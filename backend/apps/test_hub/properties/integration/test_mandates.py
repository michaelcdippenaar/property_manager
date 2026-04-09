"""
Integration tests for RentalMandateViewSet.

Covers:
  - CRUD permissions (tenant/supplier forbidden, agent scoped to own properties)
  - List filtering by ?property=<id>
  - Auto-linking of landlord on create via PropertyOwnership
  - send-for-signing action: happy path, status guard, owner-email guard,
    ESigningSubmission creation, and mandate status transition

Source file under test: apps/properties/mandate_views.py
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest
from django.urls import reverse

from apps.accounts.models import Agency
from apps.esigning.models import ESigningSubmission
from apps.properties.models import RentalMandate
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


def _mandate_payload(property_id, **overrides):
    payload = {
        "property":              property_id,
        "mandate_type":          "full_management",
        "exclusivity":           "sole",
        "commission_rate":       "10.00",
        "commission_period":     "monthly",
        "start_date":            "2026-01-01",
        "end_date":              "2027-01-01",
        "notice_period_days":    60,
        "maintenance_threshold": "2500.00",
    }
    payload.update(overrides)
    return payload


class RentalMandateListPermissionTests(TremlyAPITestCase):
    """Role gates on the list endpoint."""

    url = reverse("rental-mandate-list")

    def test_unauthenticated_rejected(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 401)

    def test_tenant_forbidden(self):
        self.authenticate(self.create_tenant())
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_supplier_forbidden(self):
        self.authenticate(self.create_supplier_user())
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_admin_sees_empty_list(self):
        self.authenticate(self.create_admin())
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)


class RentalMandateListScopingTests(TremlyAPITestCase):
    """Admins see everything; agents only see mandates on their assigned properties."""

    def setUp(self):
        self.admin = self.create_admin(email="root@test.com")
        self.agent_a = self.create_agent(email="a@test.com")
        self.agent_b = self.create_agent(email="b@test.com")

        self.prop_a = self.create_property(agent=self.agent_a, name="Alpha")
        self.prop_b = self.create_property(agent=self.agent_b, name="Bravo")
        self.landlord = self.create_landlord()

        self.mandate_a = RentalMandate.objects.create(
            property=self.prop_a,
            landlord=self.landlord,
            mandate_type=RentalMandate.MandateType.FULL_MANAGEMENT,
            commission_rate=Decimal("10.00"),
            start_date=date(2026, 1, 1),
        )
        self.mandate_b = RentalMandate.objects.create(
            property=self.prop_b,
            landlord=self.landlord,
            mandate_type=RentalMandate.MandateType.LETTING_ONLY,
            commission_rate=Decimal("1.00"),
            commission_period=RentalMandate.CommissionPeriod.ONCE_OFF,
            start_date=date(2026, 1, 1),
        )

    def _list(self, user, **params):
        self.authenticate(user)
        return self.client.get(reverse("rental-mandate-list"), params)

    def test_admin_sees_all_mandates(self):
        resp = self._list(self.admin)
        self.assertEqual(resp.status_code, 200)
        ids = [m["id"] for m in resp.data["results"]]
        self.assertIn(self.mandate_a.id, ids)
        self.assertIn(self.mandate_b.id, ids)

    def test_agent_only_sees_own_property_mandates(self):
        resp = self._list(self.agent_a)
        self.assertEqual(resp.status_code, 200)
        ids = [m["id"] for m in resp.data["results"]]
        self.assertIn(self.mandate_a.id, ids)
        self.assertNotIn(self.mandate_b.id, ids)

    def test_filter_by_property_id(self):
        resp = self._list(self.admin, property=self.prop_b.id)
        ids = [m["id"] for m in resp.data["results"]]
        self.assertEqual(ids, [self.mandate_b.id])

    def test_response_includes_property_and_landlord_names(self):
        resp = self._list(self.admin, property=self.prop_a.id)
        entry = resp.data["results"][0]
        self.assertEqual(entry["property_name"], "Alpha")
        self.assertEqual(entry["landlord_name"], self.landlord.name)


class RentalMandateCreateTests(TremlyAPITestCase):
    """POST /mandates/ creates a draft mandate, auto-linking the landlord."""

    def setUp(self):
        self.admin = self.create_admin()
        self.authenticate(self.admin)
        self.prop = self.create_property()
        self.landlord = self.create_landlord()
        self.create_property_ownership(property_obj=self.prop, landlord=self.landlord)

    def test_create_mandate_with_landlord_autolink(self):
        """Omitting landlord should populate it from the current PropertyOwnership."""
        resp = self.client.post(
            reverse("rental-mandate-list"),
            _mandate_payload(self.prop.id),
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["landlord"], self.landlord.id)
        mandate = RentalMandate.objects.get(pk=resp.data["id"])
        self.assertEqual(mandate.landlord_id, self.landlord.id)
        self.assertEqual(mandate.status, RentalMandate.Status.DRAFT)

    def test_create_mandate_explicit_landlord(self):
        """Passing landlord explicitly overrides the autolink."""
        other = self.create_landlord(name="Other Landlord", id_number="9001015800088")
        resp = self.client.post(
            reverse("rental-mandate-list"),
            _mandate_payload(self.prop.id, landlord=other.id),
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["landlord"], other.id)

    def test_create_mandate_missing_required_fields(self):
        resp = self.client.post(
            reverse("rental-mandate-list"),
            {"property": self.prop.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_forbidden_for_tenant(self):
        self.authenticate(self.create_tenant())
        resp = self.client.post(
            reverse("rental-mandate-list"),
            _mandate_payload(self.prop.id),
            format="json",
        )
        self.assertEqual(resp.status_code, 403)


class RentalMandateUpdateDeleteTests(TremlyAPITestCase):

    def setUp(self):
        self.admin = self.create_admin()
        self.authenticate(self.admin)
        self.prop = self.create_property()
        self.landlord = self.create_landlord()
        self.mandate = RentalMandate.objects.create(
            property=self.prop,
            landlord=self.landlord,
            mandate_type=RentalMandate.MandateType.FULL_MANAGEMENT,
            commission_rate=Decimal("10.00"),
            start_date=date(2026, 1, 1),
            notes="Initial notes",
        )

    def test_retrieve_mandate(self):
        resp = self.client.get(reverse("rental-mandate-detail", args=[self.mandate.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["id"], self.mandate.id)
        self.assertEqual(resp.data["notes"], "Initial notes")

    def test_patch_mandate(self):
        resp = self.client.patch(
            reverse("rental-mandate-detail", args=[self.mandate.id]),
            {"notes": "Updated notes", "commission_rate": "12.50"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.mandate.refresh_from_db()
        self.assertEqual(self.mandate.notes, "Updated notes")
        self.assertEqual(self.mandate.commission_rate, Decimal("12.50"))

    def test_delete_mandate(self):
        resp = self.client.delete(reverse("rental-mandate-detail", args=[self.mandate.id]))
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(RentalMandate.objects.filter(pk=self.mandate.id).exists())


class RentalMandateSendForSigningTests(TremlyAPITestCase):
    """POST /mandates/<id>/send-for-signing/ — the document generation + e-signing flow."""

    def setUp(self):
        self.admin = self.create_admin(email="root@test.com", first_name="Root", last_name="Admin")
        self.authenticate(self.admin)

        Agency.objects.create(name="Klikk", eaab_ffc_number="PPRA-FFC-1", contact_number="0211234567")

        self.prop = self.create_property()
        self.landlord = self.create_landlord()
        self.create_property_ownership(property_obj=self.prop, landlord=self.landlord)

        self.mandate = RentalMandate.objects.create(
            property=self.prop,
            landlord=self.landlord,
            mandate_type=RentalMandate.MandateType.FULL_MANAGEMENT,
            commission_rate=Decimal("10.00"),
            start_date=date(2026, 1, 1),
            end_date=date(2027, 1, 1),
            notice_period_days=60,
            maintenance_threshold=Decimal("2000.00"),
        )
        self.url = reverse("rental-mandate-send-for-signing", args=[self.mandate.id])

    @mock.patch("apps.properties.mandate_views._auto_send_signing_links")
    def test_send_for_signing_happy_path(self, mock_send):
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 200)

        self.mandate.refresh_from_db()
        self.assertEqual(self.mandate.status, RentalMandate.Status.SENT)
        self.assertIsNotNone(self.mandate.esigning_submission)

        sub = self.mandate.esigning_submission
        self.assertEqual(sub.signing_backend, ESigningSubmission.SigningBackend.NATIVE)
        self.assertEqual(sub.signing_mode, ESigningSubmission.SigningMode.SEQUENTIAL)
        self.assertEqual(len(sub.signers), 2)
        # Signer order is owner (0) then agent (1)
        self.assertEqual(sub.signers[0]["role"], "owner")
        self.assertEqual(sub.signers[1]["role"], "agent")
        self.assertTrue(sub.document_html)
        self.assertTrue(sub.document_hash)
        self.assertEqual(sub.created_by, self.admin)
        mock_send.assert_called_once()

    @mock.patch("apps.properties.mandate_views._auto_send_signing_links")
    def test_send_for_signing_blocked_when_not_draft(self, mock_send):
        self.mandate.status = RentalMandate.Status.SENT
        self.mandate.save()
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("already", resp.data["detail"])
        mock_send.assert_not_called()

    @mock.patch("apps.properties.mandate_views._auto_send_signing_links")
    def test_send_for_signing_requires_owner_email(self, mock_send):
        self.landlord.email = ""
        self.landlord.representative_email = ""
        self.landlord.save()
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Owner email", resp.data["detail"])
        self.mandate.refresh_from_db()
        self.assertEqual(self.mandate.status, RentalMandate.Status.DRAFT)
        mock_send.assert_not_called()

    @mock.patch("apps.properties.mandate_views._auto_send_signing_links")
    def test_send_for_signing_rejected_for_tenant(self, mock_send):
        self.authenticate(self.create_tenant())
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 403)
        mock_send.assert_not_called()

    @mock.patch("apps.properties.mandate_views._auto_send_signing_links")
    @mock.patch("apps.properties.mandate_views.generate_mandate_html")
    def test_send_for_signing_document_generation_failure(self, mock_gen, mock_send):
        mock_gen.side_effect = RuntimeError("boom")
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 500)
        self.assertIn("Document generation failed", resp.data["detail"])
        self.mandate.refresh_from_db()
        self.assertEqual(self.mandate.status, RentalMandate.Status.DRAFT)
        mock_send.assert_not_called()

    @mock.patch("apps.properties.mandate_views._auto_send_signing_links",
                side_effect=RuntimeError("smtp is down"))
    def test_email_failure_is_non_fatal(self, mock_send):
        """If sending fails, the submission is still created (agent can resend)."""
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 200)
        self.mandate.refresh_from_db()
        self.assertEqual(self.mandate.status, RentalMandate.Status.SENT)
        self.assertIsNotNone(self.mandate.esigning_submission)
