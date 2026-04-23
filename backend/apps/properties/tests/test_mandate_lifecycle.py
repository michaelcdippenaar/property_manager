"""
Mandate lifecycle tests — one case per mandate type × state transition.

Covers:
  - All 4 mandate types (full_management, letting_only, rent_collection, finders_fee)
  - All 4 exclusivity / duration configurations:
      sole            → exclusivity=sole
      multiple-agent  → exclusivity=open
      limited-duration → end_date enforced (expire_mandates command + active check)
      (shared is modelled through sole+open — the serializer exposes the exclusivity field)
  - Multi-owner scenarios: owner email missing blocks send-for-signing
  - Termination: active-lease guard, override flag, reason required
  - Renewal: clone + previous_mandate chain preserved
  - Expiry: expire_mandates command transitions active+end_date < today → expired
  - Reminder dry-run: expire_mandates --dry-run emits correct messages
"""
import hashlib
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from unittest import mock

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import Agency
from apps.esigning.models import ESigningSubmission
from apps.properties.models import RentalMandate
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _active_mandate(test_case, mandate_type="full_management", exclusivity="sole",
                    end_date=None) -> RentalMandate:
    """Create and return an active RentalMandate for the test's property."""
    return RentalMandate.objects.create(
        property=test_case.prop,
        landlord=test_case.landlord,
        mandate_type=mandate_type,
        exclusivity=exclusivity,
        commission_rate=Decimal("10.00"),
        commission_period="monthly",
        start_date=date(2025, 1, 1),
        end_date=end_date,
        notice_period_days=60,
        maintenance_threshold=Decimal("2000.00"),
        status=RentalMandate.Status.ACTIVE,
        created_by=test_case.agent,
    )


class MandateLifecycleBase(TremlyAPITestCase):
    """Base setUp shared by all lifecycle test classes."""

    def setUp(self):
        Agency.objects.create(name="Klikk Properties", eaab_ffc_number="FFC-001")
        self.agent = self.create_agent(email="agent@klikk.co.za", first_name="Mary", last_name="Manager")
        self.landlord = self.create_landlord()
        self.prop = self.create_property(agent=self.agent)
        self.create_property_ownership(property_obj=self.prop, landlord=self.landlord)
        self.authenticate(self.agent)


# ---------------------------------------------------------------------------
# 1. All 4 mandate types reach 'active' status
# ---------------------------------------------------------------------------

class MandateTypesCoverageTest(MandateLifecycleBase):
    """Each of the 4 mandate types can be created and activated."""

    TYPES = [
        ("full_management", "monthly",  Decimal("10.00")),
        ("letting_only",    "once_off", Decimal("1.00")),
        ("rent_collection", "monthly",  Decimal("5.00")),
        ("finders_fee",     "once_off", Decimal("1.00")),
    ]

    def test_all_mandate_types_can_be_created_and_activated(self):
        for mandate_type, period, rate in self.TYPES:
            m = _active_mandate(self, mandate_type=mandate_type)
            m.refresh_from_db()
            self.assertEqual(m.mandate_type, mandate_type,
                             f"{mandate_type}: mandate_type wrong")
            self.assertEqual(m.status, RentalMandate.Status.ACTIVE,
                             f"{mandate_type}: status should be active")


# ---------------------------------------------------------------------------
# 2. Exclusivity — sole vs open (multiple-agent)
# ---------------------------------------------------------------------------

class MandateExclusivityTest(MandateLifecycleBase):
    """Sole and open (multiple-agent/non-exclusive) mandates are stored correctly."""

    def test_sole_mandate_exclusivity(self):
        m = _active_mandate(self, exclusivity="sole")
        self.assertEqual(m.exclusivity, "sole")

    def test_open_mandate_exclusivity(self):
        m = _active_mandate(self, exclusivity="open")
        self.assertEqual(m.exclusivity, "open")

    def test_exclusivity_exposed_by_api(self):
        _active_mandate(self, exclusivity="open")
        resp = self.client.get(f"/api/v1/properties/mandates/?property={self.prop.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["results"][0]["exclusivity"], "open")


# ---------------------------------------------------------------------------
# 3. Limited-duration — end_date enforced by expire_mandates command
# ---------------------------------------------------------------------------

class LimitedDurationMandateTest(MandateLifecycleBase):
    """Mandates with an end_date in the past are expired by the management command."""

    def test_expired_by_command_when_end_date_passed(self):
        yesterday = date.today() - timedelta(days=1)
        m = _active_mandate(self, end_date=yesterday)
        call_command("expire_mandates", verbosity=0)
        m.refresh_from_db()
        self.assertEqual(m.status, RentalMandate.Status.EXPIRED)

    def test_not_expired_when_end_date_in_future(self):
        future = date.today() + timedelta(days=60)
        m = _active_mandate(self, end_date=future)
        call_command("expire_mandates", verbosity=0)
        m.refresh_from_db()
        self.assertEqual(m.status, RentalMandate.Status.ACTIVE)

    def test_dry_run_does_not_change_status(self):
        yesterday = date.today() - timedelta(days=1)
        m = _active_mandate(self, end_date=yesterday)
        out = StringIO()
        call_command("expire_mandates", "--dry-run", stdout=out, verbosity=0)
        m.refresh_from_db()
        self.assertEqual(m.status, RentalMandate.Status.ACTIVE)
        self.assertIn("dry-run", out.getvalue())

    def test_reminder_logged_at_30_14_7_days(self):
        """expire_mandates queues reminders for mandates expiring in 30, 14, and 7 days."""
        for days in [30, 14, 7]:
            target = date.today() + timedelta(days=days)
            m = _active_mandate(self, end_date=target)
            with mock.patch(
                "apps.properties.management.commands.expire_mandates._send_expiry_reminder"
            ) as mock_remind:
                call_command("expire_mandates", verbosity=0)
                mock_remind.assert_called_once_with(m, days_remaining=days)
            m.delete()  # clean up so next iteration starts fresh


# ---------------------------------------------------------------------------
# 4. Multi-owner signature — owner email guard
# ---------------------------------------------------------------------------

class MandateMultiOwnerSigningTest(MandateLifecycleBase):
    """send-for-signing is blocked when the owner has no email address."""

    def test_blocked_when_owner_email_missing(self):
        self.landlord.email = ""
        self.landlord.representative_email = ""
        self.landlord.save()
        m = RentalMandate.objects.create(
            property=self.prop,
            landlord=self.landlord,
            mandate_type="full_management",
            exclusivity="sole",
            commission_rate=Decimal("10.00"),
            commission_period="monthly",
            start_date=date(2026, 1, 1),
            notice_period_days=60,
            maintenance_threshold=Decimal("2000.00"),
            created_by=self.agent,
        )
        resp = self.client.post(f"/api/v1/properties/mandates/{m.pk}/send-for-signing/")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("email", resp.data["detail"].lower())

    @mock.patch("apps.esigning.views._auto_send_signing_links")
    @mock.patch("apps.properties.mandate_services.generate_mandate_html")
    def test_send_for_signing_creates_owner_signer_record(self, mock_html, mock_send):
        mock_html.return_value = "<html>Mandate</html>"
        m = RentalMandate.objects.create(
            property=self.prop,
            landlord=self.landlord,
            mandate_type="full_management",
            exclusivity="sole",
            commission_rate=Decimal("10.00"),
            commission_period="monthly",
            start_date=date(2026, 1, 1),
            notice_period_days=60,
            maintenance_threshold=Decimal("2000.00"),
            created_by=self.agent,
        )
        resp = self.client.post(f"/api/v1/properties/mandates/{m.pk}/send-for-signing/")
        self.assertEqual(resp.status_code, 200)
        sub = ESigningSubmission.objects.get(pk=resp.data["submission_id"])
        owner_signers = [s for s in sub.signers if s["role"] == "owner"]
        self.assertEqual(len(owner_signers), 1)
        self.assertEqual(owner_signers[0]["email"], "john@landlord.co.za")


# ---------------------------------------------------------------------------
# 5. Termination
# ---------------------------------------------------------------------------

class MandateTerminationTest(MandateLifecycleBase):
    """Termination state transitions, notice enforcement, and active-lease guard."""

    def test_terminate_active_mandate(self):
        m = _active_mandate(self)
        resp = self.client.post(
            f"/api/v1/properties/mandates/{m.pk}/terminate/",
            {"reason": "Owner sold the property."},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        m.refresh_from_db()
        self.assertEqual(m.status, RentalMandate.Status.TERMINATED)
        self.assertIsNotNone(m.terminated_at)
        self.assertEqual(m.terminated_reason, "Owner sold the property.")

    def test_terminate_requires_reason(self):
        m = _active_mandate(self)
        resp = self.client.post(
            f"/api/v1/properties/mandates/{m.pk}/terminate/",
            {"reason": ""},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("reason", resp.data["detail"].lower())

    def test_terminate_blocked_on_non_active_mandate(self):
        m = RentalMandate.objects.create(
            property=self.prop,
            landlord=self.landlord,
            mandate_type="full_management",
            exclusivity="sole",
            commission_rate=Decimal("10.00"),
            commission_period="monthly",
            start_date=date(2026, 1, 1),
            notice_period_days=60,
            maintenance_threshold=Decimal("2000.00"),
            status=RentalMandate.Status.DRAFT,
            created_by=self.agent,
        )
        resp = self.client.post(
            f"/api/v1/properties/mandates/{m.pk}/terminate/",
            {"reason": "Testing."},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_terminate_blocked_when_active_lease(self):
        unit = self.create_unit(property_obj=self.prop)
        self.create_lease(unit=unit, status="active")
        m = _active_mandate(self)
        resp = self.client.post(
            f"/api/v1/properties/mandates/{m.pk}/terminate/",
            {"reason": "Testing active lease block."},
            format="json",
        )
        self.assertEqual(resp.status_code, 409)
        self.assertIn("active lease", resp.data["detail"].lower())

    def test_terminate_override_active_lease(self):
        unit = self.create_unit(property_obj=self.prop)
        self.create_lease(unit=unit, status="active")
        m = _active_mandate(self)
        resp = self.client.post(
            f"/api/v1/properties/mandates/{m.pk}/terminate/",
            {"reason": "Emergency override.", "override_active_lease": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        m.refresh_from_db()
        self.assertEqual(m.status, RentalMandate.Status.TERMINATED)

    def test_all_4_types_can_be_terminated(self):
        for mandate_type, _, _ in [
            ("full_management", "monthly",  Decimal("10.00")),
            ("letting_only",    "once_off", Decimal("1.00")),
            ("rent_collection", "monthly",  Decimal("5.00")),
            ("finders_fee",     "once_off", Decimal("1.00")),
        ]:
            m = _active_mandate(self, mandate_type=mandate_type)
            resp = self.client.post(
                f"/api/v1/properties/mandates/{m.pk}/terminate/",
                {"reason": f"Terminating {mandate_type}."},
                format="json",
            )
            self.assertEqual(resp.status_code, 200, f"{mandate_type}: {resp.data}")
            m.refresh_from_db()
            self.assertEqual(m.status, RentalMandate.Status.TERMINATED)


# ---------------------------------------------------------------------------
# 6. Renewal flow
# ---------------------------------------------------------------------------

class MandateRenewalTest(MandateLifecycleBase):
    """Renewal clones the mandate, links previous_mandate, and starts in draft."""

    def test_renew_active_mandate(self):
        m = _active_mandate(self)
        resp = self.client.post(f"/api/v1/properties/mandates/{m.pk}/renew/", format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["status"], "draft")
        self.assertEqual(resp.data["previous_mandate"], m.pk)

    def test_renew_expired_mandate(self):
        m = _active_mandate(self, end_date=date.today() - timedelta(days=1))
        call_command("expire_mandates", verbosity=0)
        m.refresh_from_db()
        self.assertEqual(m.status, RentalMandate.Status.EXPIRED)
        resp = self.client.post(f"/api/v1/properties/mandates/{m.pk}/renew/", format="json")
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_renew_terminated_mandate(self):
        m = _active_mandate(self)
        self.client.post(
            f"/api/v1/properties/mandates/{m.pk}/terminate/",
            {"reason": "Owner request."},
            format="json",
        )
        resp = self.client.post(f"/api/v1/properties/mandates/{m.pk}/renew/", format="json")
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_renewal_chain_preserved(self):
        """A chain of 3 renewals links each to its predecessor."""
        m1 = _active_mandate(self)
        resp1 = self.client.post(f"/api/v1/properties/mandates/{m1.pk}/renew/", format="json")
        m2_id = resp1.data["id"]

        # Activate m2 manually for the test
        m2 = RentalMandate.objects.get(pk=m2_id)
        m2.status = RentalMandate.Status.ACTIVE
        m2.save(update_fields=["status"])

        resp2 = self.client.post(f"/api/v1/properties/mandates/{m2_id}/renew/", format="json")
        m3_id = resp2.data["id"]

        self.assertEqual(resp2.data["previous_mandate"], m2_id)
        m3 = RentalMandate.objects.get(pk=m3_id)
        self.assertEqual(m3.previous_mandate_id, m2_id)
        self.assertEqual(m3.previous_mandate.previous_mandate_id, m1.pk)

    def test_renew_blocked_for_draft(self):
        m = RentalMandate.objects.create(
            property=self.prop,
            landlord=self.landlord,
            mandate_type="full_management",
            exclusivity="sole",
            commission_rate=Decimal("10.00"),
            commission_period="monthly",
            start_date=date(2026, 1, 1),
            notice_period_days=60,
            maintenance_threshold=Decimal("2000.00"),
            status=RentalMandate.Status.DRAFT,
            created_by=self.agent,
        )
        resp = self.client.post(f"/api/v1/properties/mandates/{m.pk}/renew/", format="json")
        self.assertEqual(resp.status_code, 400)

    def test_renewal_inherits_mandate_type(self):
        m = _active_mandate(self, mandate_type="rent_collection")
        resp = self.client.post(f"/api/v1/properties/mandates/{m.pk}/renew/", format="json")
        self.assertEqual(resp.data["mandate_type"], "rent_collection")

    def test_renewal_overrides_start_date(self):
        m = _active_mandate(self)
        new_start = "2027-01-01"
        resp = self.client.post(
            f"/api/v1/properties/mandates/{m.pk}/renew/",
            {"start_date": new_start},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["start_date"], new_start)

    def test_all_4_types_can_be_renewed(self):
        for mandate_type in ("full_management", "letting_only", "rent_collection", "finders_fee"):
            m = _active_mandate(self, mandate_type=mandate_type)
            resp = self.client.post(f"/api/v1/properties/mandates/{m.pk}/renew/", format="json")
            self.assertEqual(resp.status_code, 201, f"{mandate_type}: {resp.data}")
            self.assertEqual(resp.data["mandate_type"], mandate_type)

    def test_renewal_inherits_notes_when_omitted(self):
        """Renewing without supplying notes should preserve the source mandate's notes."""
        m = _active_mandate(self)
        m.notes = "Special commission arrangement agreed with owner."
        m.save(update_fields=["notes"])

        resp = self.client.post(f"/api/v1/properties/mandates/{m.pk}/renew/", format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["notes"], "Special commission arrangement agreed with owner.")

    def test_renewal_notes_can_be_overridden(self):
        """Supplying notes in the renew POST body should use the provided value, not the source."""
        m = _active_mandate(self)
        m.notes = "Original notes."
        m.save(update_fields=["notes"])

        resp = self.client.post(
            f"/api/v1/properties/mandates/{m.pk}/renew/",
            {"notes": "Updated notes for renewal."},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["notes"], "Updated notes for renewal.")
