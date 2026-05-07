"""
Phase 2.5 — two-agency isolation tests for the maintenance app viewsets.

Confirms that the AgencyScopedQuerysetMixin + AgencyStampedCreateMixin (now
applied to the maintenance viewsets) prevent cross-tenant data leakage in
production code paths for MaintenanceRequest, Supplier, AgentQuestion, and
the dispatch / invoice APIViews.

Setup: two agencies, each with one AGENCY_ADMIN + one Property + Unit +
MaintenanceRequest + Supplier + AgentQuestion. We exercise list / retrieve
/ create from each tenant's perspective and from an ADMIN perspective.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Agency, User
from apps.maintenance.models import (
    AgentQuestion,
    JobDispatch,
    JobQuoteRequest,
    MaintenanceRequest,
    Supplier,
    SupplierInvoice,
)
from apps.properties.models import Property, Unit


@pytest.mark.django_db
class TwoAgencyMaintenanceIsolationTestBase(TestCase):
    """Two agencies, two agency-admins, two property/unit/MR/supplier sets."""

    def setUp(self):
        self.agency_a = Agency.objects.create(name="Agency MA")
        self.agency_b = Agency.objects.create(name="Agency MB")

        self.user_a = User.objects.create_user(
            email="mstaff_a@x.com", password="pass", role=User.Role.AGENCY_ADMIN,
        )
        self.user_a.agency = self.agency_a
        self.user_a.save(update_fields=["agency"])

        self.user_b = User.objects.create_user(
            email="mstaff_b@x.com", password="pass", role=User.Role.AGENCY_ADMIN,
        )
        self.user_b.agency = self.agency_b
        self.user_b.save(update_fields=["agency"])

        self.admin = User.objects.create_user(
            email="madmin@x.com", password="pass", role=User.Role.ADMIN,
        )

        # Tenants — used to verify the tenant-bypass branch on the MR viewset.
        self.tenant_a = User.objects.create_user(
            email="mtenant_a@x.com", password="pass", role=User.Role.TENANT,
        )

        # Agency A — property + unit + MR + supplier + question
        self.prop_a = Property.objects.create(
            agency=self.agency_a, agent=self.user_a, name="MA House",
            property_type="house", address="1 MA St", city="C", province="WC",
            postal_code="0001",
        )
        self.unit_a = Unit.objects.create(
            agency=self.agency_a, property=self.prop_a, unit_number="1",
            rent_amount=Decimal("5000"),
        )
        self.mr_a = MaintenanceRequest.objects.create(
            agency=self.agency_a, unit=self.unit_a, tenant=self.tenant_a,
            title="A leak", description="Leaking tap", status="open",
            priority="medium",
        )
        self.supplier_a = Supplier.objects.create(
            agency=self.agency_a, name="Plumber A", phone="0820000000",
        )
        self.question_a = AgentQuestion.objects.create(
            agency=self.agency_a, question="A question?", property=self.prop_a,
            status=AgentQuestion.Status.PENDING,
        )

        # Agency B
        self.prop_b = Property.objects.create(
            agency=self.agency_b, agent=self.user_b, name="MB House",
            property_type="house", address="1 MB St", city="C", province="WC",
            postal_code="0002",
        )
        self.unit_b = Unit.objects.create(
            agency=self.agency_b, property=self.prop_b, unit_number="1",
            rent_amount=Decimal("6000"),
        )
        self.mr_b = MaintenanceRequest.objects.create(
            agency=self.agency_b, unit=self.unit_b,
            title="B leak", description="Leaking tap", status="open",
            priority="medium",
        )
        self.supplier_b = Supplier.objects.create(
            agency=self.agency_b, name="Plumber B", phone="0830000000",
        )
        self.question_b = AgentQuestion.objects.create(
            agency=self.agency_b, question="B question?", property=self.prop_b,
            status=AgentQuestion.Status.PENDING,
        )

        self.client = APIClient(HTTP_ACCEPT="application/json")


def _ids(resp):
    body = resp.json()
    if isinstance(body, dict) and "results" in body:
        body = body["results"]
    return [row["id"] for row in body]


class MaintenanceRequestViewSetIsolationTest(TwoAgencyMaintenanceIsolationTestBase):
    URL = "/api/v1/maintenance/"

    def test_user_a_lists_only_a_requests(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(_ids(resp), [self.mr_a.id])

    def test_user_a_cannot_retrieve_b_request(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(f"{self.URL}{self.mr_b.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_sees_all_requests(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(self.URL)
        self.assertEqual(
            sorted(_ids(resp)), sorted([self.mr_a.id, self.mr_b.id])
        )


class SupplierViewSetIsolationTest(TwoAgencyMaintenanceIsolationTestBase):
    URL = "/api/v1/maintenance/suppliers/"

    def test_user_a_lists_only_a_suppliers(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(_ids(resp), [self.supplier_a.id])

    def test_user_a_cannot_retrieve_b_supplier(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(f"{self.URL}{self.supplier_b.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_stamps_users_agency_ignoring_payload(self):
        """User A POSTs supplier with agency=B in payload — server forces agency=A."""
        self.client.force_authenticate(self.user_a)
        resp = self.client.post(self.URL, {
            "name": "Forced supplier",
            "phone": "0820001111",
            "agency": self.agency_b.id,  # malicious override
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        new_sup = Supplier.objects.get(name="Forced supplier")
        self.assertEqual(new_sup.agency_id, self.agency_a.id)

    def test_admin_sees_all_suppliers(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(self.URL)
        ids = _ids(resp)
        self.assertIn(self.supplier_a.id, ids)
        self.assertIn(self.supplier_b.id, ids)


class AgentQuestionViewSetIsolationTest(TwoAgencyMaintenanceIsolationTestBase):
    URL = "/api/v1/maintenance/agent-questions/"

    def test_user_a_lists_only_a_questions(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(_ids(resp), [self.question_a.id])

    def test_user_a_cannot_retrieve_b_question(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(f"{self.URL}{self.question_b.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class AgentInvoiceApprovalIsolationTest(TwoAgencyMaintenanceIsolationTestBase):
    """The agent-side invoice approval APIView must not leak across agencies."""

    def setUp(self):
        super().setUp()
        # Build a SupplierInvoice on agency B's chain.
        self.dispatch_b = JobDispatch.objects.create(
            agency=self.agency_b, maintenance_request=self.mr_b,
            dispatched_by=self.user_b, status="awarded",
        )
        self.qr_b = JobQuoteRequest.objects.create(
            agency=self.agency_b, dispatch=self.dispatch_b,
            supplier=self.supplier_b, status="awarded",
        )
        self.invoice_b = SupplierInvoice.objects.create(
            agency=self.agency_b, quote_request=self.qr_b,
            total_amount=Decimal("2500.00"),
            status=SupplierInvoice.Status.PENDING,
        )

    def test_user_a_cannot_read_b_invoice(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(f"/api/v1/maintenance/{self.mr_b.id}/invoice/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_a_cannot_approve_b_invoice(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.post(
            f"/api/v1/maintenance/{self.mr_b.id}/invoice/",
            {"action": "approve"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        # Invoice unchanged.
        self.invoice_b.refresh_from_db()
        self.assertEqual(self.invoice_b.status, SupplierInvoice.Status.PENDING)

    def test_admin_sees_b_invoice(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(f"/api/v1/maintenance/{self.mr_b.id}/invoice/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
