"""
Integration tests for SigningDraft and SupportingDocument features.

Covers:
  - ESigningPublicDraftView (GET/POST /public-sign/<link_id>/draft/)
  - ESigningPublicDocumentsView (GET/POST /public-sign/<link_id>/documents/)
  - ESigningPublicDocumentDeleteView (DELETE /public-sign/<link_id>/documents/<doc_id>/)
  - ESigningSubmissionDocumentsView (GET /submissions/<pk>/documents/)
"""
from datetime import timedelta
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from apps.esigning.models import (
    ESigningAuditEvent,
    ESigningPublicLink,
    ESigningSubmission,
    SigningDraft,
    SupportingDocument,
)
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_pdf(name="statement.pdf"):
    """Return a minimal valid PDF as a SimpleUploadedFile."""
    content = b"%PDF-1.4 1 0 obj<</Type/Catalog>>endobj"
    return SimpleUploadedFile(name, content, content_type="application/pdf")


def _make_submission(lease, agent):
    return ESigningSubmission.objects.create(
        lease=lease,
        signing_backend="native",
        status="pending",
        signing_mode="sequential",
        created_by=agent,
        signers=[
            {
                "id": 1,
                "role": "tenant_1",
                "name": "Test Tenant",
                "email": "tenant@test.com",
                "status": "pending",
                "order": 0,
            }
        ],
        document_html="<p>Test lease</p>",
        document_hash="abc123",
    )


def _make_link(submission, days_from_now=7):
    return ESigningPublicLink.objects.create(
        submission=submission,
        signer_role="tenant_1",
        expires_at=timezone.now() + timedelta(days=days_from_now),
    )


# ── SigningDraft tests ─────────────────────────────────────────────────────────

class SigningDraftTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)
        self.submission = _make_submission(self.lease, self.agent)
        self.link = _make_link(self.submission)
        self.draft_url = reverse("esigning-public-draft", kwargs={"link_id": self.link.pk})

    # ── GET ───────────────────────────────────────────────────────────────────

    def test_get_draft_no_draft_returns_has_draft_false(self):
        resp = self.client.get(self.draft_url)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["has_draft"])

    def test_get_draft_returns_saved_state(self):
        signed = {"sig_tenant_1": {"imageData": "data:image/png;base64,abc", "signedAt": "2026-01-01T10:00:00Z"}}
        captured = {"tenant_name": "Alice"}
        self.client.post(self.draft_url, {"signed_fields": signed, "captured_fields": captured}, format="json")

        resp = self.client.get(self.draft_url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["has_draft"])
        self.assertEqual(resp.data["signed_fields"], signed)
        self.assertEqual(resp.data["captured_fields"], captured)

    # ── POST ──────────────────────────────────────────────────────────────────

    def test_post_draft_creates_draft(self):
        signed = {"sig_tenant_1": {"imageData": "data:image/png;base64,xyz", "signedAt": "2026-01-02T09:00:00Z"}}
        captured = {"tenant_id_number": "9001015001089"}

        resp = self.client.post(
            self.draft_url,
            {"signed_fields": signed, "captured_fields": captured},
            format="json",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["saved"])
        self.assertIn("saved_at", resp.data)
        self.assertEqual(SigningDraft.objects.filter(public_link=self.link).count(), 1)

    def test_post_draft_updates_existing_draft(self):
        """POSTing twice must upsert — only one SigningDraft row should exist."""
        payload = {"signed_fields": {"sig_tenant_1": {"imageData": "a", "signedAt": "2026-01-01T00:00:00Z"}}, "captured_fields": {}}
        self.client.post(self.draft_url, payload, format="json")
        payload["signed_fields"]["sig_tenant_1"]["imageData"] = "b"
        self.client.post(self.draft_url, payload, format="json")

        self.assertEqual(SigningDraft.objects.filter(public_link=self.link).count(), 1)
        draft = SigningDraft.objects.get(public_link=self.link)
        self.assertEqual(draft.signed_fields_data["sig_tenant_1"]["imageData"], "b")

    def test_draft_on_expired_link_returns_410(self):
        expired_link = _make_link(self.submission, days_from_now=-1)
        url = reverse("esigning-public-draft", kwargs={"link_id": expired_link.pk})
        resp = self.client.post(url, {"signed_fields": {}, "captured_fields": {}}, format="json")
        self.assertEqual(resp.status_code, 410)

    def test_draft_creates_audit_event(self):
        self.client.post(
            self.draft_url,
            {"signed_fields": {"s": {"imageData": "x", "signedAt": "2026-01-01T00:00:00Z"}}, "captured_fields": {}},
            format="json",
        )
        self.assertTrue(
            ESigningAuditEvent.objects.filter(
                submission=self.submission,
                event_type=ESigningAuditEvent.EventType.DRAFT_SAVED,
            ).exists()
        )


# ── SupportingDocument upload / list / delete tests ───────────────────────────

class SupportingDocumentUploadTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)
        self.submission = _make_submission(self.lease, self.agent)
        self.link = _make_link(self.submission)
        self.docs_url = reverse("esigning-public-documents", kwargs={"link_id": self.link.pk})

    # ── List ──────────────────────────────────────────────────────────────────

    def test_list_documents_empty(self):
        resp = self.client.get(self.docs_url)
        self.assertEqual(resp.status_code, 200)
        # GET now returns {documents: [...], required_documents: [...]}
        self.assertEqual(resp.data["documents"], [])
        self.assertIn("required_documents", resp.data)

    def test_list_documents_after_upload(self):
        self.client.post(self.docs_url, {"file": _make_pdf("one.pdf"), "document_type": "bank_statement"}, format="multipart")
        self.client.post(self.docs_url, {"file": _make_pdf("two.pdf"), "document_type": "id_copy"}, format="multipart")

        resp = self.client.get(self.docs_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["documents"]), 2)

    # ── Upload success ────────────────────────────────────────────────────────

    def test_upload_pdf_succeeds(self):
        resp = self.client.post(
            self.docs_url,
            {"file": _make_pdf("statement.pdf"), "document_type": "bank_statement"},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["document_type"], "bank_statement")
        self.assertEqual(resp.data["original_filename"], "statement.pdf")

    def test_upload_creates_db_record(self):
        self.client.post(
            self.docs_url,
            {"file": _make_pdf("id.pdf"), "document_type": "id_copy"},
            format="multipart",
        )
        self.assertEqual(SupportingDocument.objects.count(), 1)
        doc = SupportingDocument.objects.first()
        self.assertEqual(doc.document_type, SupportingDocument.DocumentType.ID_COPY)
        self.assertEqual(doc.uploaded_by_role, "tenant_1")

    def test_upload_logs_audit_event(self):
        self.client.post(
            self.docs_url,
            {"file": _make_pdf("proof.pdf"), "document_type": "proof_of_address"},
            format="multipart",
        )
        self.assertTrue(
            ESigningAuditEvent.objects.filter(
                submission=self.submission,
                event_type=ESigningAuditEvent.EventType.SUPPORTING_DOC_UPLOADED,
            ).exists()
        )

    # ── Upload validation ─────────────────────────────────────────────────────

    def test_upload_rejected_non_pdf_jpg_png(self):
        exe_file = SimpleUploadedFile("malware.exe", b"MZ\x90\x00", content_type="application/octet-stream")
        resp = self.client.post(
            self.docs_url,
            {"file": exe_file, "document_type": "other"},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 415)

    def test_upload_rejected_oversized_file(self):
        # 11 MB — exceeds the 10 MB limit
        big_content = b"x" * (11 * 1024 * 1024)
        big_file = SimpleUploadedFile("large.pdf", big_content, content_type="application/pdf")
        resp = self.client.post(
            self.docs_url,
            {"file": big_file, "document_type": "other"},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 413)

    def test_upload_invalid_document_type_falls_back_to_other(self):
        resp = self.client.post(
            self.docs_url,
            {"file": _make_pdf("misc.pdf"), "document_type": "invalid_type"},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 201)
        doc = SupportingDocument.objects.first()
        self.assertEqual(doc.document_type, SupportingDocument.DocumentType.OTHER)

    def test_upload_on_expired_link_returns_410(self):
        expired_link = _make_link(self.submission, days_from_now=-1)
        url = reverse("esigning-public-documents", kwargs={"link_id": expired_link.pk})
        resp = self.client.post(
            url,
            {"file": _make_pdf("late.pdf"), "document_type": "bank_statement"},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 410)

    # ── Delete ────────────────────────────────────────────────────────────────

    def test_delete_document(self):
        upload_resp = self.client.post(
            self.docs_url,
            {"file": _make_pdf("to_delete.pdf"), "document_type": "other"},
            format="multipart",
        )
        self.assertEqual(upload_resp.status_code, 201)
        doc_id = upload_resp.data["id"]

        delete_url = reverse("esigning-public-document-delete", kwargs={"link_id": self.link.pk, "doc_id": doc_id})
        del_resp = self.client.delete(delete_url)
        self.assertEqual(del_resp.status_code, 204)
        self.assertEqual(SupportingDocument.objects.filter(pk=doc_id).count(), 0)

    def test_delete_document_wrong_link_returns_404(self):
        # Upload doc via link A
        upload_resp = self.client.post(
            self.docs_url,
            {"file": _make_pdf("doc_a.pdf"), "document_type": "other"},
            format="multipart",
        )
        self.assertEqual(upload_resp.status_code, 201)
        doc_id = upload_resp.data["id"]

        # Create a second link (link B) for the same submission
        link_b = _make_link(self.submission)
        delete_url = reverse("esigning-public-document-delete", kwargs={"link_id": link_b.pk, "doc_id": doc_id})
        del_resp = self.client.delete(delete_url)
        self.assertEqual(del_resp.status_code, 404)


# ── Staff submission documents view tests ─────────────────────────────────────

class SubmissionDocumentsStaffViewTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)
        self.submission = _make_submission(self.lease, self.agent)
        self.link = _make_link(self.submission)
        self.docs_public_url = reverse("esigning-public-documents", kwargs={"link_id": self.link.pk})
        self.staff_url = reverse("esigning-submission-documents", kwargs={"pk": self.submission.pk})

    def _upload_doc(self):
        return self.client.post(
            self.docs_public_url,
            {"file": _make_pdf("bank.pdf"), "document_type": "bank_statement"},
            format="multipart",
        )

    def test_staff_can_list_submission_documents(self):
        self._upload_doc()
        self.authenticate(self.agent)
        resp = self.client.get(self.staff_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        item = resp.data[0]
        self.assertIn("file_url", item)
        self.assertEqual(item["document_type"], "bank_statement")

    def test_tenant_cannot_list_submission_documents(self):
        tenant = self.create_tenant(email="viewer_tenant@test.com")
        self.authenticate(tenant)
        resp = self.client.get(self.staff_url)
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_cannot_list_submission_documents(self):
        # No auth header
        self.client.force_authenticate(user=None)
        resp = self.client.get(self.staff_url)
        self.assertIn(resp.status_code, (401, 403))
