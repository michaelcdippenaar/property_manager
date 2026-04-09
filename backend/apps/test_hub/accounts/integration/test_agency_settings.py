"""
Tests for the Agency settings endpoint (singleton /api/v1/auth/agency/).

Covers:
  - GET permissions: any authenticated agent/admin may read
  - PUT permissions: admin only
  - Singleton behaviour (upsert — GET empty then PUT creates, next PUT updates)
  - PPRA compliance fields (FFC number, principal PPRA, auditor IRBA, BEE)
  - Account type enum (agency vs individual)
  - Logo upload via multipart/form-data

Source file under test: apps/accounts/admin_views.py :: AgencySettingsView
"""
import io

import pytest
from django.urls import reverse

from apps.accounts.models import Agency
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


class AgencySettingsGetPermissionTests(TremlyAPITestCase):
    """GET /auth/agency/ should be readable by any staff user (needed for isAgency check)."""

    url = reverse("agency-settings")

    def test_admin_can_get_agency(self):
        self.authenticate(self.create_admin())
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_agent_can_get_agency(self):
        self.authenticate(self.create_agent())
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_tenant_cannot_get_agency(self):
        self.authenticate(self.create_tenant())
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_supplier_cannot_get_agency(self):
        self.authenticate(self.create_supplier_user())
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_cannot_get_agency(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 401)

    def test_get_returns_empty_when_no_agency_configured(self):
        """Fresh install — no Agency row yet → returns {}."""
        self.authenticate(self.create_admin())
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, {})


class AgencySettingsPutPermissionTests(TremlyAPITestCase):
    """PUT /auth/agency/ should be admin only."""

    url = reverse("agency-settings")

    def test_admin_can_put_agency(self):
        self.authenticate(self.create_admin())
        resp = self.client.put(self.url, {"name": "Klikk Agency"}, format="json")
        self.assertEqual(resp.status_code, 200)

    def test_agent_cannot_put_agency(self):
        self.authenticate(self.create_agent())
        resp = self.client.put(self.url, {"name": "Sneaky Agency"}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_tenant_cannot_put_agency(self):
        self.authenticate(self.create_tenant())
        resp = self.client.put(self.url, {"name": "Hacker"}, format="json")
        self.assertEqual(resp.status_code, 403)


class AgencySettingsUpsertBehaviourTests(TremlyAPITestCase):
    """PUT creates the singleton if missing, updates it otherwise."""

    url = reverse("agency-settings")

    def setUp(self):
        self.admin = self.create_admin()
        self.authenticate(self.admin)

    def test_first_put_creates_agency(self):
        self.assertFalse(Agency.objects.exists())
        resp = self.client.put(
            self.url,
            {"name": "Klikk (Pty) Ltd", "contact_number": "0211234567"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Agency.objects.count(), 1)
        agency = Agency.get_solo()
        self.assertEqual(agency.name, "Klikk (Pty) Ltd")
        self.assertEqual(agency.contact_number, "0211234567")

    def test_second_put_updates_existing_agency(self):
        Agency.objects.create(name="Old Name", contact_number="0111111111")
        resp = self.client.put(
            self.url,
            {"name": "New Name", "contact_number": "0219999999"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        # Still exactly one agency, fields updated
        self.assertEqual(Agency.objects.count(), 1)
        agency = Agency.get_solo()
        self.assertEqual(agency.name, "New Name")
        self.assertEqual(agency.contact_number, "0219999999")

    def test_partial_update_preserves_unspecified_fields(self):
        Agency.objects.create(
            name="Keep Me", contact_number="0211111111", email="keep@klikk.co.za",
        )
        resp = self.client.put(self.url, {"contact_number": "0222222222"}, format="json")
        self.assertEqual(resp.status_code, 200)
        agency = Agency.get_solo()
        self.assertEqual(agency.contact_number, "0222222222")
        self.assertEqual(agency.name, "Keep Me")
        self.assertEqual(agency.email, "keep@klikk.co.za")


class AgencyComplianceFieldsTests(TremlyAPITestCase):
    """PPRA / FICA / BEE / trust-account fields must persist and return via GET."""

    url = reverse("agency-settings")

    def setUp(self):
        self.authenticate(self.create_admin())

    def test_ppra_ffc_fields_round_trip(self):
        resp = self.client.put(self.url, {
            "name": "Klikk",
            "registration_number": "2020/123456/07",
            "vat_number": "4123456789",
            "eaab_ffc_number": "PPRA-FFC-2025-01",
            "principal_name": "Jane Principal",
            "principal_ppra_number": "1234567",
        }, format="json")
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(self.url)
        self.assertEqual(resp.data["eaab_ffc_number"], "PPRA-FFC-2025-01")
        self.assertEqual(resp.data["principal_ppra_number"], "1234567")
        self.assertEqual(resp.data["registration_number"], "2020/123456/07")

    def test_auditor_and_fica_fields_round_trip(self):
        resp = self.client.put(self.url, {
            "name": "Klikk",
            "auditor_name": "PwC",
            "auditor_irba_number": "IRBA-999",
            "bee_level": "Level 4",
            "fica_registered": True,
        }, format="json")
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(self.url)
        self.assertEqual(resp.data["auditor_name"], "PwC")
        self.assertEqual(resp.data["auditor_irba_number"], "IRBA-999")
        self.assertEqual(resp.data["bee_level"], "Level 4")
        self.assertTrue(resp.data["fica_registered"])

    def test_trust_account_fields_round_trip(self):
        self.client.put(self.url, {
            "name": "Klikk",
            "trust_bank_name": "Nedbank",
            "trust_account_number": "1234567890",
            "trust_branch_code": "198765",
        }, format="json")
        resp = self.client.get(self.url)
        self.assertEqual(resp.data["trust_bank_name"], "Nedbank")
        self.assertEqual(resp.data["trust_account_number"], "1234567890")
        self.assertEqual(resp.data["trust_branch_code"], "198765")


class AgencyAccountTypeTests(TremlyAPITestCase):
    """Account type enum: 'agency' vs 'individual'."""

    url = reverse("agency-settings")

    def setUp(self):
        self.authenticate(self.create_admin())

    def test_default_account_type_is_agency(self):
        self.client.put(self.url, {"name": "Klikk"}, format="json")
        agency = Agency.get_solo()
        self.assertEqual(agency.account_type, Agency.AccountType.AGENCY)

    def test_can_set_account_type_individual(self):
        resp = self.client.put(
            self.url, {"name": "John Owner", "account_type": "individual"}, format="json",
        )
        self.assertEqual(resp.status_code, 200)
        agency = Agency.get_solo()
        self.assertEqual(agency.account_type, "individual")

    def test_get_returns_account_type(self):
        Agency.objects.create(name="Solo Owner", account_type="individual")
        resp = self.client.get(self.url)
        self.assertEqual(resp.data["account_type"], "individual")


class AgencyLogoUploadTests(TremlyAPITestCase):
    """Logo upload via multipart/form-data."""

    url = reverse("agency-settings")

    def setUp(self):
        self.authenticate(self.create_admin())

    def test_logo_upload_via_multipart(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        # Generate a valid 4×4 red PNG so Pillow's ImageField validator passes
        img = Image.new("RGB", (4, 4), color=(200, 20, 60))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()
        logo = SimpleUploadedFile("logo.png", png_bytes, content_type="image/png")

        resp = self.client.put(
            self.url,
            {"name": "Klikk", "logo": logo},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 200)
        agency = Agency.get_solo()
        self.assertTrue(agency.logo.name.startswith("agency/"))


class AgencySingletonModelTests(TremlyAPITestCase):
    """The Agency model must enforce singleton at the DB layer (save() guard)."""

    def test_cannot_create_two_agencies(self):
        Agency.objects.create(name="First")
        with self.assertRaises(ValueError):
            Agency.objects.create(name="Second")

    def test_get_solo_returns_none_when_empty(self):
        self.assertIsNone(Agency.get_solo())

    def test_get_solo_returns_instance_when_present(self):
        Agency.objects.create(name="The One")
        self.assertEqual(Agency.get_solo().name, "The One")
