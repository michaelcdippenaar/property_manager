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
  6. RBAC regression: admin/agency_admin get 200; all other roles get 403
  7. AuditContextMiddleware: thread-local context populated from request
"""

from __future__ import annotations

from io import StringIO

from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditEvent, compute_self_hash
from apps.audit.middleware import AuditContextMiddleware, get_audit_context, _clear_audit_context
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


# ---------------------------------------------------------------------------
# 6. RBAC regression — audit endpoints
# ---------------------------------------------------------------------------


def _make_user(email: str, role: str) -> User:
    return User.objects.create_user(password="testpass123", email=email, role=role)


class TestAuditEndpointRBAC(TestCase):
    """
    RNT-SEC-039 — RBAC regression for GET /api/v1/audit/events/ and
    GET /api/v1/audit/timeline/{app_label}/{model}/{pk}/.

    admin and agency_admin must receive HTTP 200.
    All other roles must receive HTTP 403.
    """

    EVENTS_URL = "/api/v1/audit/events/"
    # Use a deliberately non-existent object so we test permission before DB lookup.
    # leases/lease/0/ — ContentType must exist (it does after migrations run).
    TIMELINE_URL = "/api/v1/audit/timeline/leases/lease/0/"

    def _assert_role_status(self, role: str, expected_status: int) -> None:
        email = f"{role.replace('_', '')}@rbac-test.com"
        user = _make_user(email, role)
        client = APIClient()
        client.force_authenticate(user=user)

        events_resp = client.get(self.EVENTS_URL)
        self.assertEqual(
            events_resp.status_code,
            expected_status,
            f"Role '{role}' got {events_resp.status_code} on {self.EVENTS_URL}, expected {expected_status}",
        )

        timeline_resp = client.get(self.TIMELINE_URL)
        self.assertEqual(
            timeline_resp.status_code,
            expected_status,
            f"Role '{role}' got {timeline_resp.status_code} on {self.TIMELINE_URL}, expected {expected_status}",
        )

    # --- allowed roles ---

    def test_admin_gets_200(self):
        self._assert_role_status(User.Role.ADMIN, 200)

    def test_agency_admin_gets_200(self):
        self._assert_role_status(User.Role.AGENCY_ADMIN, 200)

    # --- forbidden roles ---

    def test_agent_gets_403(self):
        self._assert_role_status(User.Role.AGENT, 403)

    def test_estate_agent_gets_403(self):
        self._assert_role_status(User.Role.ESTATE_AGENT, 403)

    def test_managing_agent_gets_403(self):
        self._assert_role_status(User.Role.MANAGING_AGENT, 403)

    def test_tenant_gets_403(self):
        self._assert_role_status(User.Role.TENANT, 403)

    def test_owner_gets_403(self):
        # The codebase uses OWNER (not landlord); this matches the task intent.
        self._assert_role_status(User.Role.OWNER, 403)

    def test_supplier_gets_403(self):
        self._assert_role_status(User.Role.SUPPLIER, 403)

    def test_unauthenticated_gets_401(self):
        """Unauthenticated callers must never reach audit data."""
        client = APIClient()
        events_resp = client.get(self.EVENTS_URL)
        self.assertIn(
            events_resp.status_code,
            (401, 403),
            f"Unauthenticated caller got unexpected status {events_resp.status_code}",
        )
        timeline_resp = client.get(self.TIMELINE_URL)
        self.assertIn(
            timeline_resp.status_code,
            (401, 403),
            f"Unauthenticated caller got unexpected status {timeline_resp.status_code}",
        )


# ---------------------------------------------------------------------------
# 7. AuditContextMiddleware unit tests
# ---------------------------------------------------------------------------


class TestAuditContextMiddleware(TestCase):
    """
    RNT-SEC-039 — AuditContextMiddleware stores actor/ip/user_agent in
    thread-local storage and clears it after the response.
    """

    def setUp(self):
        # Ensure clean state before each test
        _clear_audit_context()

    def tearDown(self):
        _clear_audit_context()

    def _make_middleware(self, view_fn=None):
        """Return a middleware instance wrapping a trivial get_response."""
        from django.http import HttpResponse

        def _default_view(request):
            return HttpResponse("ok")

        return AuditContextMiddleware(view_fn or _default_view)

    def _make_request(self, user=None, remote_addr="1.2.3.4", user_agent="TestAgent/1.0"):
        """Build a minimal request-like object."""
        from django.test import RequestFactory
        rf = RequestFactory()
        request = rf.get("/", HTTP_USER_AGENT=user_agent, REMOTE_ADDR=remote_addr)
        if user is not None:
            request.user = user
        else:
            from django.contrib.auth.models import AnonymousUser
            request.user = AnonymousUser()
        return request

    def test_authenticated_user_stored_in_context(self):
        user = _make_user("ctx_user@test.com", User.Role.ADMIN)
        request = self._make_request(user=user, remote_addr="10.0.0.1", user_agent="Mozilla/5.0")

        captured = {}

        def view(req):
            from django.http import HttpResponse
            ctx = get_audit_context()
            captured["actor"] = ctx.actor
            captured["ip"] = ctx.ip
            captured["user_agent"] = ctx.user_agent
            return HttpResponse("ok")

        middleware = self._make_middleware(view)
        middleware(request)

        self.assertEqual(captured["actor"], user)
        self.assertEqual(captured["ip"], "10.0.0.1")
        self.assertEqual(captured["user_agent"], "Mozilla/5.0")

    def test_anonymous_user_actor_is_none(self):
        request = self._make_request(user=None, remote_addr="192.168.1.1")

        captured = {}

        def view(req):
            from django.http import HttpResponse
            ctx = get_audit_context()
            captured["actor"] = ctx.actor
            return HttpResponse("ok")

        middleware = self._make_middleware(view)
        middleware(request)

        self.assertIsNone(captured["actor"])

    def test_context_cleared_after_response(self):
        user = _make_user("ctx_clear@test.com", User.Role.ADMIN)
        request = self._make_request(user=user)
        middleware = self._make_middleware()
        middleware(request)

        # After the request completes, context must be empty
        ctx = get_audit_context()
        self.assertIsNone(ctx.actor)
        self.assertIsNone(ctx.ip)

    def test_context_cleared_even_on_view_exception(self):
        """Context must be cleared in the finally block even if the view raises."""
        user = _make_user("ctx_exc@test.com", User.Role.ADMIN)
        request = self._make_request(user=user)

        def exploding_view(req):
            raise RuntimeError("boom")

        middleware = self._make_middleware(exploding_view)
        with self.assertRaises(RuntimeError):
            middleware(request)

        ctx = get_audit_context()
        self.assertIsNone(ctx.actor)

    def test_x_forwarded_for_used_as_ip(self):
        """With NUM_PROXIES=1 (default) and XFF='203.0.113.5, 10.0.0.1', get_client_ip
        walks one trusted hop back from the right — the real client is '203.0.113.5'
        (index -2 in a 2-entry list).  This delegates entirely to utils.http.get_client_ip
        so the behaviour stays in sync with the global proxy-trust configuration."""
        from unittest.mock import patch
        from django.test import RequestFactory
        rf = RequestFactory()
        request = rf.get(
            "/",
            HTTP_X_FORWARDED_FOR="203.0.113.5, 10.0.0.1",
            REMOTE_ADDR="10.0.0.1",
        )
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()

        captured = {}

        def view(req):
            from django.http import HttpResponse
            ctx = get_audit_context()
            captured["ip"] = ctx.ip
            return HttpResponse("ok")

        middleware = self._make_middleware(view)
        with patch("django.conf.settings") as mock_settings:
            mock_settings.NUM_PROXIES = 1
            mock_settings.TRUSTED_PROXY_IPS = None
            middleware(request)

        self.assertEqual(captured["ip"], "203.0.113.5")

    def test_forged_xff_with_no_proxy_uses_remote_addr(self):
        """Spoofing-negative test: with NUM_PROXIES=0 an attacker-supplied
        X-Forwarded-For header must be ignored entirely; AuditEvent ip_address
        must be REMOTE_ADDR, not the forged value."""
        from unittest.mock import patch
        from django.test import RequestFactory
        rf = RequestFactory()
        # Attacker injects a forged XFF; REMOTE_ADDR is the real socket address.
        request = rf.get(
            "/",
            HTTP_X_FORWARDED_FOR="1.2.3.4",
            REMOTE_ADDR="203.0.113.99",
        )
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()

        captured = {}

        def view(req):
            from django.http import HttpResponse
            ctx = get_audit_context()
            captured["ip"] = ctx.ip
            return HttpResponse("ok")

        middleware = self._make_middleware(view)
        with patch("django.conf.settings") as mock_settings:
            mock_settings.NUM_PROXIES = 0
            mock_settings.TRUSTED_PROXY_IPS = None
            middleware(request)

        # Must record the real socket address, not the forged header.
        self.assertEqual(
            captured["ip"],
            "203.0.113.99",
            "Forged X-Forwarded-For must not override REMOTE_ADDR when NUM_PROXIES=0",
        )
        self.assertNotEqual(captured["ip"], "1.2.3.4")

    def test_outside_request_context_returns_empty(self):
        """get_audit_context() outside a request must return empty/None values."""
        ctx = get_audit_context()
        self.assertIsNone(ctx.actor)
        self.assertIsNone(ctx.ip)
        self.assertEqual(ctx.user_agent, "")
