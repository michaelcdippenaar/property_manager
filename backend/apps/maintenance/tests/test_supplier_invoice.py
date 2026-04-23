"""
Minimal tests for the SupplierInvoice state machine + file upload validation.

Covers:
  - approve: pending → approved
  - approve: non-pending rejected with 400
  - reject: pending → rejected (with reason)
  - reject: non-pending (approved/paid) rejected with 400  [Fix 2 guard]
  - paid: approved → paid
  - paid: non-approved rejected with 400
  - invoice_file validation: PDF accepted
  - invoice_file validation: image accepted
  - invoice_file validation: wrong MIME type rejected
  - invoice_file validation: oversized file rejected
  - status-update photo validation: non-image MIME type rejected
"""
from __future__ import annotations

import io
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.maintenance.models import (
    JobDispatch,
    JobQuoteRequest,
    Supplier,
    SupplierInvoice,
)
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

INVOICE_URL_TPL = "/api/v1/maintenance/{request_pk}/invoice/"
SUPPLIER_STATUS_URL_TPL = "/api/v1/maintenance/supplier/jobs/{pk}/status/"
SUPPLIER_INVOICE_URL_TPL = "/api/v1/maintenance/supplier/jobs/{pk}/invoice/"


class InvoiceTestBase(TremlyAPITestCase):
    """Sets up: agent, supplier user+profile, property, unit, MR, dispatch, awarded QR, invoice."""

    def setUp(self):
        self.agent = self.create_agent(email="inv-agent@test.com")
        self.supplier_user = self.create_supplier_user(email="inv-supplier@test.com")
        self.supplier = self.create_supplier(
            name="Invoice Supplier",
            phone="0820002222",
            linked_user=self.supplier_user,
        )
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.mr = self.create_maintenance_request(unit=self.unit, status="in_progress")
        self.dispatch = JobDispatch.objects.create(
            maintenance_request=self.mr,
            dispatched_by=self.agent,
            status="awarded",
        )
        self.qr = JobQuoteRequest.objects.create(
            dispatch=self.dispatch,
            supplier=self.supplier,
            status="awarded",
        )
        self.invoice = SupplierInvoice.objects.create(
            quote_request=self.qr,
            total_amount=Decimal("2500.00"),
            status=SupplierInvoice.Status.PENDING,
        )

    def _agent_client(self):
        c = APIClient()
        c.force_authenticate(user=self.agent)
        return c

    def _supplier_client(self):
        c = APIClient()
        c.force_authenticate(user=self.supplier_user)
        return c

    def _invoice_url(self):
        return INVOICE_URL_TPL.format(request_pk=self.mr.pk)

    def _status_url(self):
        return SUPPLIER_STATUS_URL_TPL.format(pk=self.qr.pk)

    def _supplier_invoice_url(self):
        return SUPPLIER_INVOICE_URL_TPL.format(pk=self.qr.pk)


# ---------------------------------------------------------------------------
# State machine — approve
# ---------------------------------------------------------------------------

class TestApproveAction(InvoiceTestBase):

    def test_approve_pending_invoice(self):
        resp = self._agent_client().post(self._invoice_url(), {"action": "approve"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, SupplierInvoice.Status.APPROVED)
        self.assertEqual(self.invoice.reviewed_by, self.agent)

    def test_approve_non_pending_returns_400(self):
        self.invoice.status = SupplierInvoice.Status.APPROVED
        self.invoice.save()
        resp = self._agent_client().post(self._invoice_url(), {"action": "approve"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("pending", resp.data["detail"].lower())


# ---------------------------------------------------------------------------
# State machine — reject
# ---------------------------------------------------------------------------

class TestRejectAction(InvoiceTestBase):

    def test_reject_pending_invoice(self):
        resp = self._agent_client().post(
            self._invoice_url(),
            {"action": "reject", "reason": "Amount is incorrect"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, SupplierInvoice.Status.REJECTED)
        self.assertEqual(self.invoice.rejection_reason, "Amount is incorrect")

    def test_reject_approved_invoice_returns_400(self):
        """Fix 2: reject on an already-approved invoice must return 400."""
        self.invoice.status = SupplierInvoice.Status.APPROVED
        self.invoice.save()
        resp = self._agent_client().post(
            self._invoice_url(),
            {"action": "reject", "reason": "Changed my mind"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("pending", resp.data["detail"].lower())

    def test_reject_paid_invoice_returns_400(self):
        """Fix 2: reject on a paid invoice must return 400."""
        self.invoice.status = SupplierInvoice.Status.PAID
        self.invoice.save()
        resp = self._agent_client().post(
            self._invoice_url(),
            {"action": "reject", "reason": "Oops"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_reject_without_reason_returns_400(self):
        resp = self._agent_client().post(
            self._invoice_url(), {"action": "reject"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)


# ---------------------------------------------------------------------------
# State machine — paid
# ---------------------------------------------------------------------------

class TestPaidAction(InvoiceTestBase):

    def test_mark_paid_when_approved(self):
        self.invoice.status = SupplierInvoice.Status.APPROVED
        self.invoice.save()
        resp = self._agent_client().post(
            self._invoice_url(),
            {"action": "paid", "reference": "EFT-20260423"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, SupplierInvoice.Status.PAID)
        self.assertEqual(self.invoice.paid_reference, "EFT-20260423")

    def test_mark_paid_when_not_approved_returns_400(self):
        # invoice is still PENDING
        resp = self._agent_client().post(
            self._invoice_url(), {"action": "paid"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("approved", resp.data["detail"].lower())


# ---------------------------------------------------------------------------
# File upload validation — invoice_file (Fix 1)
# ---------------------------------------------------------------------------

class TestInvoiceFileValidation(InvoiceTestBase):

    def _delete_existing_invoice(self):
        """Remove the pre-created invoice so the POST creates a fresh one."""
        self.invoice.delete()

    def _make_file(self, content: bytes, content_type: str, name: str = "test.bin") -> SimpleUploadedFile:
        return SimpleUploadedFile(name, content, content_type=content_type)

    def test_pdf_invoice_accepted(self):
        self._delete_existing_invoice()
        pdf_bytes = b"%PDF-1.4 minimal"
        f = self._make_file(pdf_bytes, "application/pdf", "invoice.pdf")
        resp = self._supplier_client().post(
            self._supplier_invoice_url(),
            {"invoice_file": f, "total_amount": "1000.00"},
            format="multipart",
        )
        self.assertIn(resp.status_code, [200, 201], resp.data)

    def test_image_invoice_accepted(self):
        self._delete_existing_invoice()
        # Minimal valid 1x1 PNG bytes
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        f = self._make_file(png_bytes, "image/png", "photo.png")
        resp = self._supplier_client().post(
            self._supplier_invoice_url(),
            {"invoice_file": f, "total_amount": "1000.00"},
            format="multipart",
        )
        self.assertIn(resp.status_code, [200, 201], resp.data)

    def test_non_pdf_image_rejected(self):
        self._delete_existing_invoice()
        f = self._make_file(b"EXE content", "application/octet-stream", "malware.exe")
        resp = self._supplier_client().post(
            self._supplier_invoice_url(),
            {"invoice_file": f, "total_amount": "1000.00"},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 400)

    def test_oversized_invoice_rejected(self):
        self._delete_existing_invoice()
        # 11 MB > 10 MB cap
        big_bytes = b"x" * (11 * 1024 * 1024)
        f = self._make_file(big_bytes, "application/pdf", "big.pdf")
        resp = self._supplier_client().post(
            self._supplier_invoice_url(),
            {"invoice_file": f, "total_amount": "1000.00"},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 400)


# ---------------------------------------------------------------------------
# File upload validation — status update photo (Fix 1)
# ---------------------------------------------------------------------------

class TestStatusPhotoValidation(InvoiceTestBase):

    def _make_file(self, content: bytes, content_type: str, name: str = "test.bin") -> SimpleUploadedFile:
        return SimpleUploadedFile(name, content, content_type=content_type)

    def test_non_image_photo_rejected(self):
        f = self._make_file(b"%PDF-1.4", "application/pdf", "doc.pdf")
        resp = self._supplier_client().post(
            self._status_url(),
            {"status": "in_progress", "photo": f},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 400)

    def test_image_photo_accepted(self):
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        f = self._make_file(png_bytes, "image/png", "progress.png")
        resp = self._supplier_client().post(
            self._status_url(),
            {"status": "in_progress", "photo": f},
            format="multipart",
        )
        self.assertIn(resp.status_code, [200, 201], resp.data)
