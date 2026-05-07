"""
Integration tests: Rental Mandate E-Signing — all 4 mandate types.

Covers:
  - Create mandate for each of the 4 types
  - send-for-signing creates ESigningSubmission and updates status to 'sent'
  - Serializer exposes submission_id, owner_email, owner_name correctly
  - send-for-signing blocked when status != draft
  - send-for-signing blocked when owner email is missing
  - ESigningDownloadSignedView resolves mandate submissions (regression: was
    filtering by lease FK, so mandate downloads always returned 404)
"""
import hashlib
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest
from django.core.files.base import ContentFile

from apps.accounts.models import Agency
from apps.esigning.models import ESigningSubmission
from apps.properties.models import RentalMandate
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_submission(mandate, agent_user):
    """Create a completed ESigningSubmission for a mandate (helper)."""
    dummy_html = "<html><body>Mandate</body></html>"
    doc_hash = hashlib.sha256(dummy_html.encode()).hexdigest()
    signer_records = [
        {"id": 1, "name": "Owner", "email": "owner@test.com", "role": "owner", "order": 0, "status": "completed"},
        {"id": 2, "name": "Agent", "email": "agent@test.com", "role": "agent", "order": 1, "status": "completed"},
    ]
    sub = ESigningSubmission.objects.create(
        agency=mandate.agency,  # Phase 2.6 — submissions inherit mandate's agency
        lease=None,
        mandate=mandate,
        signing_backend=ESigningSubmission.SigningBackend.NATIVE,
        signing_mode=ESigningSubmission.SigningMode.SEQUENTIAL,
        status=ESigningSubmission.Status.COMPLETED,
        signers=signer_records,
        document_html=dummy_html,
        document_hash=doc_hash,
        created_by=agent_user,
    )
    # Attach a dummy signed PDF
    pdf_bytes = b"%PDF-1.4 fake"
    sub.signed_pdf_file.save(f"signed_mandate_{sub.pk}.pdf", ContentFile(pdf_bytes), save=True)
    return sub


# ---------------------------------------------------------------------------
# Mandate creation — all 4 types
# ---------------------------------------------------------------------------

MANDATE_TYPES = [
    ("full_management", "monthly", Decimal("10.00")),
    ("letting_only",    "once_off", Decimal("1.00")),
    ("rent_collection", "monthly", Decimal("5.00")),
    ("finders_fee",     "once_off", Decimal("1.00")),
]


class MandateCreateAllTypesTest(TremlyAPITestCase):
    """All 4 mandate types can be created via POST /api/v1/properties/mandates/."""

    def setUp(self):
        self.agency = Agency.objects.create(name="Klikk Properties", eaab_ffc_number="FFC-001")
        self.agent = self.create_agent(email="agent@klikk.co.za", first_name="Mary", last_name="Manager")
        self.agent.agency = self.agency
        self.agent.save(update_fields=["agency"])
        self.landlord = self.create_landlord(agency=self.agency)
        self.prop = self.create_property(agent=self.agent, agency=self.agency)
        self.create_property_ownership(property_obj=self.prop, landlord=self.landlord, agency=self.agency)
        self.authenticate(self.agent)

    def _create_mandate_payload(self, mandate_type, commission_period, commission_rate):
        return {
            "property": self.prop.pk,
            "mandate_type": mandate_type,
            "exclusivity": "sole",
            "commission_rate": str(commission_rate),
            "commission_period": commission_period,
            "start_date": "2026-01-01",
            "notice_period_days": 60,
            "maintenance_threshold": "2000.00",
        }

    def test_full_management_mandate_created(self):
        payload = self._create_mandate_payload("full_management", "monthly", Decimal("10.00"))
        resp = self.client.post("/api/v1/properties/mandates/", payload, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["mandate_type"], "full_management")
        self.assertEqual(resp.data["status"], "draft")

    def test_letting_only_mandate_created(self):
        payload = self._create_mandate_payload("letting_only", "once_off", Decimal("1.00"))
        resp = self.client.post("/api/v1/properties/mandates/", payload, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["mandate_type"], "letting_only")

    def test_rent_collection_mandate_created(self):
        payload = self._create_mandate_payload("rent_collection", "monthly", Decimal("5.00"))
        resp = self.client.post("/api/v1/properties/mandates/", payload, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["mandate_type"], "rent_collection")

    def test_finders_fee_mandate_created(self):
        payload = self._create_mandate_payload("finders_fee", "once_off", Decimal("1.00"))
        resp = self.client.post("/api/v1/properties/mandates/", payload, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["mandate_type"], "finders_fee")


# ---------------------------------------------------------------------------
# send-for-signing
# ---------------------------------------------------------------------------

class MandateSendForSigningTest(TremlyAPITestCase):
    """send-for-signing creates ESigningSubmission and transitions mandate to 'sent'."""

    def setUp(self):
        self.agency = Agency.objects.create(name="Klikk Properties", eaab_ffc_number="FFC-001")
        self.agent = self.create_agent(email="agent@klikk.co.za", first_name="Mary", last_name="Manager")
        self.agent.agency = self.agency
        self.agent.save(update_fields=["agency"])
        self.landlord = self.create_landlord(agency=self.agency)
        self.prop = self.create_property(agent=self.agent, agency=self.agency)
        self.create_property_ownership(property_obj=self.prop, landlord=self.landlord, agency=self.agency)
        self.authenticate(self.agent)

    def _create_mandate(self, mandate_type="full_management"):
        return RentalMandate.objects.create(
            agency=self.agency,
            property=self.prop,
            landlord=self.landlord,
            mandate_type=mandate_type,
            exclusivity="sole",
            commission_rate=Decimal("10.00"),
            commission_period="monthly",
            start_date=date(2026, 1, 1),
            notice_period_days=60,
            maintenance_threshold=Decimal("2000.00"),
            created_by=self.agent,
        )

    @mock.patch("apps.esigning.views._auto_send_signing_links")
    @mock.patch("apps.properties.mandate_services.generate_mandate_html")
    def test_send_for_signing_transitions_to_sent(self, mock_html, mock_send):
        mock_html.return_value = "<html>Mandate content</html>"
        mandate = self._create_mandate()
        resp = self.client.post(f"/api/v1/properties/mandates/{mandate.pk}/send-for-signing/")
        self.assertEqual(resp.status_code, 200, resp.data)
        mandate.refresh_from_db()
        self.assertEqual(mandate.status, RentalMandate.Status.SENT)

    @mock.patch("apps.esigning.views._auto_send_signing_links")
    @mock.patch("apps.properties.mandate_services.generate_mandate_html")
    def test_send_for_signing_creates_esigning_submission(self, mock_html, mock_send):
        mock_html.return_value = "<html>Mandate content</html>"
        mandate = self._create_mandate()
        resp = self.client.post(f"/api/v1/properties/mandates/{mandate.pk}/send-for-signing/")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIsNotNone(resp.data.get("submission_id"))
        sub = ESigningSubmission.objects.get(pk=resp.data["submission_id"])
        self.assertIsNone(sub.lease_id)
        self.assertEqual(sub.mandate_id, mandate.pk)

    @mock.patch("apps.esigning.views._auto_send_signing_links")
    @mock.patch("apps.properties.mandate_services.generate_mandate_html")
    def test_send_for_signing_rejected_when_already_sent(self, mock_html, mock_send):
        mock_html.return_value = "<html>Mandate content</html>"
        mandate = self._create_mandate()
        # Send first time
        self.client.post(f"/api/v1/properties/mandates/{mandate.pk}/send-for-signing/")
        # Send second time — should fail
        resp = self.client.post(f"/api/v1/properties/mandates/{mandate.pk}/send-for-signing/")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("sent", resp.data["detail"].lower())

    def test_send_for_signing_rejected_when_no_owner_email(self):
        # Strip all email from landlord
        self.landlord.email = ""
        self.landlord.representative_email = ""
        self.landlord.save()
        mandate = self._create_mandate()
        resp = self.client.post(f"/api/v1/properties/mandates/{mandate.pk}/send-for-signing/")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("email", resp.data["detail"].lower())

    @mock.patch("apps.esigning.views._auto_send_signing_links")
    @mock.patch("apps.properties.mandate_services.generate_mandate_html")
    def test_send_for_signing_all_four_types(self, mock_html, mock_send):
        """All 4 mandate types reach 'sent' status without error."""
        mock_html.return_value = "<html>Mandate</html>"
        for mt in ("full_management", "letting_only", "rent_collection", "finders_fee"):
            mandate = self._create_mandate(mandate_type=mt)
            resp = self.client.post(f"/api/v1/properties/mandates/{mandate.pk}/send-for-signing/")
            self.assertEqual(resp.status_code, 200, f"Failed for mandate type {mt}: {resp.data}")
            mandate.refresh_from_db()
            self.assertEqual(mandate.status, RentalMandate.Status.SENT, f"Status wrong for {mt}")


# ---------------------------------------------------------------------------
# Download signed mandate (regression: was broken for mandate submissions)
# ---------------------------------------------------------------------------

class MandateDownloadSignedRegressionTest(TremlyAPITestCase):
    """
    Regression: ESigningDownloadSignedView previously filtered by
    lease FK only, so mandate submissions always returned 404.
    """

    def setUp(self):
        self.agency = Agency.objects.create(name="Klikk Properties", eaab_ffc_number="FFC-001")
        self.agent = self.create_agent(email="agent@klikk.co.za", first_name="Mary", last_name="Manager")
        self.agent.agency = self.agency
        self.agent.save(update_fields=["agency"])
        self.landlord = self.create_landlord(agency=self.agency)
        self.prop = self.create_property(agent=self.agent, agency=self.agency)
        self.create_property_ownership(property_obj=self.prop, landlord=self.landlord, agency=self.agency)
        self.mandate = RentalMandate.objects.create(
            agency=self.agency,
            property=self.prop,
            landlord=self.landlord,
            mandate_type="full_management",
            commission_rate=Decimal("10.00"),
            start_date=date(2026, 1, 1),
            notice_period_days=60,
            maintenance_threshold=Decimal("2000.00"),
            status=RentalMandate.Status.ACTIVE,
            created_by=self.agent,
        )
        self.authenticate(self.agent)

    def test_download_returns_url_not_404(self):
        sub = _make_submission(self.mandate, self.agent)
        resp = self.client.get(f"/api/v1/esigning/submissions/{sub.pk}/download/")
        # Should be 200 (url returned) not 404
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIn("url", resp.data)

    def test_download_blocked_when_submission_not_completed(self):
        """Incomplete submission should return 400, not 404."""
        dummy_html = "<html><body>Mandate</body></html>"
        doc_hash = hashlib.sha256(dummy_html.encode()).hexdigest()
        sub = ESigningSubmission.objects.create(
            agency=self.mandate.agency,  # Phase 2.6 — inherit mandate's agency
            lease=None,
            mandate=self.mandate,
            signing_backend=ESigningSubmission.SigningBackend.NATIVE,
            signing_mode=ESigningSubmission.SigningMode.SEQUENTIAL,
            status=ESigningSubmission.Status.PENDING,
            signers=[],
            document_html=dummy_html,
            document_hash=doc_hash,
            created_by=self.agent,
        )
        resp = self.client.get(f"/api/v1/esigning/submissions/{sub.pk}/download/")
        self.assertEqual(resp.status_code, 400)


# ---------------------------------------------------------------------------
# Serializer — submission_id and owner fields
# ---------------------------------------------------------------------------

class MandateSerializerFieldsTest(TremlyAPITestCase):
    """Serializer exposes submission_id, owner_email, owner_name from landlord."""

    def setUp(self):
        self.agency = Agency.objects.create(name="Klikk Properties", eaab_ffc_number="FFC-001")
        self.agent = self.create_agent(email="agent@klikk.co.za")
        self.agent.agency = self.agency
        self.agent.save(update_fields=["agency"])
        self.landlord = self.create_landlord(agency=self.agency)
        self.prop = self.create_property(agent=self.agent, agency=self.agency)
        self.create_property_ownership(property_obj=self.prop, landlord=self.landlord, agency=self.agency)
        self.mandate = RentalMandate.objects.create(
            agency=self.agency,
            property=self.prop,
            landlord=self.landlord,
            mandate_type="full_management",
            commission_rate=Decimal("10.00"),
            start_date=date(2026, 1, 1),
            notice_period_days=60,
            maintenance_threshold=Decimal("2000.00"),
            created_by=self.agent,
        )
        self.authenticate(self.agent)

    def test_submission_id_null_before_sending(self):
        resp = self.client.get(f"/api/v1/properties/mandates/{self.mandate.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.data["submission_id"])

    def test_owner_email_and_name_populated(self):
        resp = self.client.get(f"/api/v1/properties/mandates/{self.mandate.pk}/")
        self.assertEqual(resp.status_code, 200)
        # Landlord representative_email and representative_name set in create_landlord fixture
        self.assertEqual(resp.data["owner_email"], "john@landlord.co.za")
        self.assertEqual(resp.data["owner_name"], "John Landlord")

    @mock.patch("apps.esigning.views._auto_send_signing_links")
    @mock.patch("apps.properties.mandate_services.generate_mandate_html")
    def test_submission_id_populated_after_sending(self, mock_html, mock_send):
        mock_html.return_value = "<html>Mandate</html>"
        self.client.post(f"/api/v1/properties/mandates/{self.mandate.pk}/send-for-signing/")
        resp = self.client.get(f"/api/v1/properties/mandates/{self.mandate.pk}/")
        self.assertIsNotNone(resp.data["submission_id"])
