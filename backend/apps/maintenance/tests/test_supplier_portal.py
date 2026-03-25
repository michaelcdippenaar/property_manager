"""Tests for supplier portal endpoints: dashboard, jobs, quotes, decline, profile, documents, calendar."""
from datetime import date, timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from apps.maintenance.models import (
    JobDispatch, JobQuote, JobQuoteRequest, Supplier, SupplierDocument, SupplierTrade,
)
from tests.base import TremlyAPITestCase


class SupplierPortalBaseTestCase(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.supplier_user = self.create_supplier_user()
        self.supplier = self.create_supplier(
            name="Portal Supplier", phone="0820001111", linked_user=self.supplier_user,
        )
        SupplierTrade.objects.create(supplier=self.supplier, trade="plumbing")
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.mr = self.create_maintenance_request(unit=self.unit)
        self.dispatch = JobDispatch.objects.create(
            maintenance_request=self.mr, dispatched_by=self.agent, status="sent",
        )
        self.qr = JobQuoteRequest.objects.create(
            dispatch=self.dispatch, supplier=self.supplier, status="pending",
        )


class SupplierDashboardTests(SupplierPortalBaseTestCase):

    def test_dashboard(self):
        self.authenticate(self.supplier_user)
        resp = self.client.get(reverse("supplier-portal-dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("new_requests", resp.data)
        self.assertIn("company_name", resp.data)

    def test_dashboard_no_profile(self):
        user_no_profile = self.create_user(email="nosupp@test.com", role="supplier")
        self.authenticate(user_no_profile)
        resp = self.client.get(reverse("supplier-portal-dashboard"))
        self.assertEqual(resp.status_code, 403)

    def test_dashboard_unauthenticated(self):
        resp = self.client.get(reverse("supplier-portal-dashboard"))
        self.assertEqual(resp.status_code, 401)


class SupplierJobsTests(SupplierPortalBaseTestCase):

    def test_jobs_list(self):
        self.authenticate(self.supplier_user)
        resp = self.client.get(reverse("supplier-portal-jobs"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_jobs_filter_status(self):
        self.authenticate(self.supplier_user)
        resp = self.client.get(reverse("supplier-portal-jobs"), {"status": "pending"})
        self.assertEqual(resp.status_code, 200)

    def test_job_detail(self):
        self.authenticate(self.supplier_user)
        resp = self.client.get(reverse("supplier-portal-job-detail", args=[self.qr.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_job_detail_marks_viewed(self):
        self.authenticate(self.supplier_user)
        self.client.get(reverse("supplier-portal-job-detail", args=[self.qr.pk]))
        self.qr.refresh_from_db()
        self.assertIsNotNone(self.qr.viewed_at)
        self.assertEqual(self.qr.status, "viewed")

    def test_job_detail_other_supplier(self):
        other_user = self.create_user(email="other_supp@test.com", role="supplier")
        other_supplier = self.create_supplier(
            name="Other", phone="0820009999", linked_user=other_user,
        )
        self.authenticate(other_user)
        resp = self.client.get(reverse("supplier-portal-job-detail", args=[self.qr.pk]))
        self.assertEqual(resp.status_code, 404)


class SupplierQuoteTests(SupplierPortalBaseTestCase):

    def test_submit_quote(self):
        self.authenticate(self.supplier_user)
        resp = self.client.post(
            reverse("supplier-portal-quote", args=[self.qr.pk]),
            {"amount": "2500.00", "estimated_days": 3, "notes": "Can fix it"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.qr.refresh_from_db()
        self.assertEqual(self.qr.status, "quoted")

    def test_quote_already_submitted(self):
        JobQuote.objects.create(
            quote_request=self.qr, amount=Decimal("1000.00"),
        )
        self.authenticate(self.supplier_user)
        resp = self.client.post(
            reverse("supplier-portal-quote", args=[self.qr.pk]),
            {"amount": "2000.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_quote_closed_job(self):
        self.qr.status = "awarded"
        self.qr.save()
        self.authenticate(self.supplier_user)
        resp = self.client.post(
            reverse("supplier-portal-quote", args=[self.qr.pk]),
            {"amount": "1000.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)


class SupplierDeclineTests(SupplierPortalBaseTestCase):

    def test_decline_job(self):
        self.authenticate(self.supplier_user)
        resp = self.client.post(reverse("supplier-portal-decline", args=[self.qr.pk]))
        self.assertEqual(resp.status_code, 200)
        self.qr.refresh_from_db()
        self.assertEqual(self.qr.status, "declined")

    def test_decline_closed_job(self):
        self.qr.status = "awarded"
        self.qr.save()
        self.authenticate(self.supplier_user)
        resp = self.client.post(reverse("supplier-portal-decline", args=[self.qr.pk]))
        self.assertEqual(resp.status_code, 400)


class SupplierProfileTests(SupplierPortalBaseTestCase):

    def test_profile_get(self):
        self.authenticate(self.supplier_user)
        resp = self.client.get(reverse("supplier-portal-profile"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["name"], "Portal Supplier")

    def test_profile_patch(self):
        self.authenticate(self.supplier_user)
        resp = self.client.patch(
            reverse("supplier-portal-profile"),
            {"company_name": "Updated Co"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.company_name, "Updated Co")


class SupplierDocumentsPortalTests(SupplierPortalBaseTestCase):

    def test_documents_list(self):
        SupplierDocument.objects.create(
            supplier=self.supplier,
            document_type="id_copy",
            file=SimpleUploadedFile("id.pdf", b"PDF"),
        )
        self.authenticate(self.supplier_user)
        resp = self.client.get(reverse("supplier-portal-documents"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_documents_upload(self):
        self.authenticate(self.supplier_user)
        f = SimpleUploadedFile("comp.pdf", b"PDF", content_type="application/pdf")
        resp = self.client.post(
            reverse("supplier-portal-documents"),
            {"file": f, "document_type": "other"},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 201)


class SupplierCalendarTests(SupplierPortalBaseTestCase):

    def test_calendar(self):
        self.qr.status = "awarded"
        self.qr.save()
        JobQuote.objects.create(
            quote_request=self.qr,
            amount=Decimal("2000.00"),
            available_from=date.today(),
            estimated_days=2,
        )
        self.authenticate(self.supplier_user)
        resp = self.client.get(reverse("supplier-portal-calendar"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_calendar_empty(self):
        self.authenticate(self.supplier_user)
        resp = self.client.get(reverse("supplier-portal-calendar"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 0)
