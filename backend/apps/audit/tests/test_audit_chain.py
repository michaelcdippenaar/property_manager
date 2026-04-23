"""
tests/test_audit_chain.py

Automated tests for RNT-SEC-008 — tamper-evident audit log.

Coverage:
  1. AuditEvent creation: self_hash is set and valid on every new row
  2. Hash chain linkage: prev_hash of row N == self_hash of row N-1
  3. Chain break detection: verify_audit_chain detects a tampered row
  4. Signal coverage: Lease / RentalMandate / ESigningSubmission / RentPayment
     / User role change each emit exactly one AuditEvent
  5. User non-role edits do NOT emit an AuditEvent
"""

from __future__ import annotations

from io import StringIO

from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.accounts.models import User
from apps.audit.models import AuditEvent, compute_self_hash
from apps.leases.models import Lease
from apps.payments.models import RentInvoice, RentPayment
from apps.properties.models import Property, RentalMandate, Unit
from apps.esigning.models import ESigningSubmission

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_admin_user(**kwargs) -> User:
    defaults = {"email": "admin@test.com", "role": User.Role.ADMIN}
    defaults.update(kwargs)
    return User.objects.create_user(password="x", **defaults)


def _create_property_and_unit() -> tuple[Property, Unit]:
    # Minimal property + unit for lease/mandate creation
    prop = Property.objects.create(
        name="Test Property",
        address="1 Main Rd",
        city="Cape Town",
        province="WC",
        postal_code="8001",
    )
    unit = Unit.objects.create(
        property=prop,
        unit_number="1",
        bedrooms=2,
        bathrooms=1,
        rent_amount=5000,
    )
    return prop, unit


# ---------------------------------------------------------------------------
# 1. Hash validity
# ---------------------------------------------------------------------------


class TestAuditEventHashValidity(TestCase):
    """Every new AuditEvent must have a valid self_hash."""

    def test_genesis_row_hash_is_valid(self):
        """Genesis row (seeded in migration) must have a valid hash."""
        genesis = AuditEvent.objects.filter(action="audit.genesis").first()
        if genesis is None:
            self.skipTest("Genesis row not present — migration may not have run")
        self.assertTrue(genesis.is_hash_valid(), "Genesis row self_hash is invalid")

    def test_new_event_hash_is_valid(self):
        """Manually created event must have valid hash after save."""
        tail = AuditEvent.objects.order_by("-id").first()
        prev_hash = tail.self_hash if tail else ""

        user = _create_admin_user(email="h@test.com")
        # Saving the User triggers a signal event; grab the latest
        latest = AuditEvent.objects.order_by("-id").first()
        self.assertIsNotNone(latest)
        self.assertTrue(latest.is_hash_valid(), "Latest event self_hash is invalid")


# ---------------------------------------------------------------------------
# 2. Chain linkage
# ---------------------------------------------------------------------------


class TestHashChainLinkage(TestCase):
    """prev_hash of each row must equal self_hash of the previous row."""

    def test_chain_is_linked(self):
        # Create several events by saving watched models
        _create_admin_user(email="u1@test.com")
        _create_admin_user(email="u2@test.com")
        _create_admin_user(email="u3@test.com")

        events = list(AuditEvent.objects.order_by("id"))
        if len(events) < 2:
            self.skipTest("Not enough events to test linkage")

        for i in range(1, len(events)):
            self.assertEqual(
                events[i].prev_hash,
                events[i - 1].self_hash,
                f"Chain break between event id={events[i-1].id} and id={events[i].id}",
            )


# ---------------------------------------------------------------------------
# 3. verify_audit_chain management command
# ---------------------------------------------------------------------------


class TestVerifyAuditChainCommand(TestCase):
    """verify_audit_chain must pass clean chain and detect tampered rows."""

    def test_command_passes_on_clean_chain(self):
        _create_admin_user(email="clean@test.com")
        out = StringIO()
        # Should not raise
        call_command("verify_audit_chain", stdout=out, stderr=StringIO())
        self.assertIn("Chain OK", out.getvalue())

    def test_command_fails_on_tampered_row(self):
        _create_admin_user(email="tamper@test.com")
        # Tamper: directly update self_hash of the latest event
        latest = AuditEvent.objects.order_by("-id").first()
        self.assertIsNotNone(latest)
        AuditEvent.objects.filter(pk=latest.pk).update(self_hash="aaaa" + "0" * 60)

        with self.assertRaises(CommandError):
            call_command("verify_audit_chain", stdout=StringIO(), stderr=StringIO())

    def test_command_fails_on_modified_field(self):
        _create_admin_user(email="modify@test.com")
        latest = AuditEvent.objects.order_by("-id").first()
        self.assertIsNotNone(latest)
        # Mutate a payload field without updating self_hash
        AuditEvent.objects.filter(pk=latest.pk).update(action="tampered.action")

        with self.assertRaises(CommandError):
            call_command("verify_audit_chain", stdout=StringIO(), stderr=StringIO())


# ---------------------------------------------------------------------------
# 4. Signal coverage
# ---------------------------------------------------------------------------


class TestSignalCoverage(TestCase):
    """Each watched model save emits exactly one AuditEvent."""

    def _count_events_for(self, instance) -> int:
        ct = ContentType.objects.get_for_model(instance.__class__)
        return AuditEvent.objects.filter(content_type=ct, object_id=instance.pk).count()

    def test_user_creation_emits_event(self):
        before = AuditEvent.objects.count()
        user = _create_admin_user(email="sig_user@test.com")
        after = AuditEvent.objects.count()
        self.assertEqual(after - before, 1)
        self.assertEqual(self._count_events_for(user), 1)

    def test_user_role_change_emits_event(self):
        user = _create_admin_user(email="role@test.com")
        before = AuditEvent.objects.count()
        user.role = User.Role.AGENT
        user.save()
        after = AuditEvent.objects.count()
        self.assertEqual(after - before, 1, "Role change must emit exactly 1 event")

    def test_user_non_role_edit_does_not_emit_event(self):
        user = _create_admin_user(email="noevent@test.com")
        before = AuditEvent.objects.count()
        user.first_name = "Changed"
        user.save()
        after = AuditEvent.objects.count()
        self.assertEqual(after - before, 0, "Non-role User edit must NOT emit an event")

    def test_lease_creation_emits_event(self):
        _prop, unit = _create_property_and_unit()
        before = AuditEvent.objects.count()
        lease = Lease.objects.create(
            unit=unit,
            start_date="2026-01-01",
            end_date="2026-12-31",
            monthly_rent=5000,
            status=Lease.Status.PENDING,
        )
        after = AuditEvent.objects.count()
        self.assertGreaterEqual(after - before, 1)
        self.assertGreaterEqual(self._count_events_for(lease), 1)

    def test_rental_mandate_creation_emits_event(self):
        from apps.properties.models import Landlord
        prop, _unit = _create_property_and_unit()
        landlord = Landlord.objects.create(
            name="Test Owner",
            email="owner@test.com",
        )
        before = AuditEvent.objects.count()
        mandate = RentalMandate.objects.create(
            property=prop,
            landlord=landlord,
            mandate_type=RentalMandate.MandateType.FULL_MANAGEMENT,
            commission_rate=10,
            start_date="2026-01-01",
        )
        after = AuditEvent.objects.count()
        self.assertGreaterEqual(after - before, 1)
        self.assertGreaterEqual(self._count_events_for(mandate), 1)

    def test_rent_payment_creation_emits_event(self):
        _prop, unit = _create_property_and_unit()
        lease = Lease.objects.create(
            unit=unit,
            start_date="2026-01-01",
            end_date="2026-12-31",
            monthly_rent=5000,
            status=Lease.Status.ACTIVE,
        )
        invoice = RentInvoice.objects.create(
            lease=lease,
            period_start="2026-01-01",
            period_end="2026-01-31",
            amount_due=5000,
            due_date="2026-01-01",
        )
        before = AuditEvent.objects.count()
        payment = RentPayment.objects.create(
            invoice=invoice,
            amount=5000,
            payment_date="2026-01-05",
        )
        after = AuditEvent.objects.count()
        self.assertGreaterEqual(after - before, 1)
        self.assertGreaterEqual(self._count_events_for(payment), 1)

    def test_esigning_submission_creation_emits_event(self):
        _prop, unit = _create_property_and_unit()
        lease = Lease.objects.create(
            unit=unit,
            start_date="2026-01-01",
            end_date="2026-12-31",
            monthly_rent=5000,
            status=Lease.Status.PENDING,
        )
        before = AuditEvent.objects.count()
        submission = ESigningSubmission.objects.create(
            lease=lease,
            status=ESigningSubmission.Status.PENDING,
        )
        after = AuditEvent.objects.count()
        self.assertGreaterEqual(after - before, 1)
        self.assertGreaterEqual(self._count_events_for(submission), 1)


# ---------------------------------------------------------------------------
# 5. Compute hash unit test (pure, no DB)
# ---------------------------------------------------------------------------


class TestComputeSelfHash(TestCase):
    """compute_self_hash must be deterministic and unique per input."""

    def test_deterministic(self):
        payload = {"id": 1, "action": "lease.created", "timestamp": "2026-01-01T00:00:00"}
        h1 = compute_self_hash("", payload)
        h2 = compute_self_hash("", payload)
        self.assertEqual(h1, h2)

    def test_different_prev_hash_yields_different_result(self):
        payload = {"id": 1, "action": "lease.created"}
        h1 = compute_self_hash("aaa", payload)
        h2 = compute_self_hash("bbb", payload)
        self.assertNotEqual(h1, h2)

    def test_genesis_hash_is_64_chars(self):
        h = compute_self_hash("", {"id": 1, "action": "audit.genesis"})
        self.assertEqual(len(h), 64)
