"""
Phase 2.7 — two-agency isolation tests for the payments app viewsets.

Confirms that AgencyScopedQuerysetMixin (now applied to RentInvoiceViewSet,
RentPaymentViewSet, UnmatchedPaymentViewSet) prevents cross-tenant
data leakage on top of the pre-existing role-based scoping.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Agency, User
from apps.leases.models import Lease
from apps.payments.models import RentInvoice, UnmatchedPayment
from apps.properties.models import Property, Unit


@pytest.mark.django_db
class _TwoAgencyBase(TestCase):
    def setUp(self):
        self.agency_a = Agency.objects.create(name="Agency A (payments)")
        self.agency_b = Agency.objects.create(name="Agency B (payments)")

        self.staff_a = User.objects.create_user(
            email="pay_a@x.com", password="pass", role=User.Role.AGENCY_ADMIN,
        )
        self.staff_a.agency = self.agency_a
        self.staff_a.save(update_fields=["agency"])

        self.staff_b = User.objects.create_user(
            email="pay_b@x.com", password="pass", role=User.Role.AGENCY_ADMIN,
        )
        self.staff_b.agency = self.agency_b
        self.staff_b.save(update_fields=["agency"])

        self.admin = User.objects.create_user(
            email="pay_admin@x.com", password="pass", role=User.Role.ADMIN,
        )

        # Property/Unit/Lease/Invoice for each agency
        self.prop_a = Property.objects.create(
            agency=self.agency_a, agent=self.staff_a, name="A", property_type="house",
            address="1 A St", city="C", province="WC", postal_code="0001",
        )
        self.unit_a = Unit.objects.create(
            agency=self.agency_a, property=self.prop_a, unit_number="1",
            rent_amount=Decimal("1000"),
        )
        self.lease_a = Lease.objects.create(
            agency=self.agency_a, unit=self.unit_a, start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31), monthly_rent=Decimal("1000"),
            status=Lease.Status.ACTIVE,
        )
        self.invoice_a = RentInvoice.objects.create(
            agency=self.agency_a, lease=self.lease_a, period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30), amount_due=Decimal("1000"),
            due_date=date(2026, 4, 1), status=RentInvoice.Status.UNPAID,
        )
        self.unmatched_a = UnmatchedPayment.objects.create(
            agency=self.agency_a, amount=Decimal("250"), payment_date=date(2026, 4, 5),
            reference="A-REF-1",
        )

        self.prop_b = Property.objects.create(
            agency=self.agency_b, agent=self.staff_b, name="B", property_type="house",
            address="1 B St", city="C", province="WC", postal_code="0002",
        )
        self.unit_b = Unit.objects.create(
            agency=self.agency_b, property=self.prop_b, unit_number="1",
            rent_amount=Decimal("2000"),
        )
        self.lease_b = Lease.objects.create(
            agency=self.agency_b, unit=self.unit_b, start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31), monthly_rent=Decimal("2000"),
            status=Lease.Status.ACTIVE,
        )
        self.invoice_b = RentInvoice.objects.create(
            agency=self.agency_b, lease=self.lease_b, period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30), amount_due=Decimal("2000"),
            due_date=date(2026, 4, 1), status=RentInvoice.Status.UNPAID,
        )
        self.unmatched_b = UnmatchedPayment.objects.create(
            agency=self.agency_b, amount=Decimal("500"), payment_date=date(2026, 4, 5),
            reference="B-REF-1",
        )

        self.client = APIClient(HTTP_ACCEPT="application/json")


def _ids(resp):
    body = resp.json()
    if isinstance(body, dict) and "results" in body:
        body = body["results"]
    return [row["id"] for row in body]


class RentInvoiceIsolationTest(_TwoAgencyBase):
    URL = "/api/v1/payments/invoices/"

    def test_staff_a_lists_only_a_invoices(self):
        self.client.force_authenticate(self.staff_a)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = _ids(resp)
        self.assertIn(self.invoice_a.id, ids)
        self.assertNotIn(self.invoice_b.id, ids)

    def test_staff_a_cannot_retrieve_b_invoice(self):
        self.client.force_authenticate(self.staff_a)
        resp = self.client.get(f"{self.URL}{self.invoice_b.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_sees_all_invoices(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(self.URL)
        ids = _ids(resp)
        self.assertIn(self.invoice_a.id, ids)
        self.assertIn(self.invoice_b.id, ids)


class UnmatchedPaymentIsolationTest(_TwoAgencyBase):
    URL = "/api/v1/payments/unmatched/"

    def test_staff_a_lists_only_a_unmatched(self):
        self.client.force_authenticate(self.staff_a)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = _ids(resp)
        self.assertIn(self.unmatched_a.id, ids)
        self.assertNotIn(self.unmatched_b.id, ids)

    def test_staff_a_cannot_retrieve_b_unmatched(self):
        self.client.force_authenticate(self.staff_a)
        resp = self.client.get(f"{self.URL}{self.unmatched_b.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_unmatched_stamps_users_agency(self):
        """Staff A POSTs with agency=B — server forces agency=A."""
        self.client.force_authenticate(self.staff_a)
        resp = self.client.post(
            self.URL,
            {
                "amount": "999.00",
                "payment_date": "2026-04-09",
                "reference": "FORCED-REF",
                "agency": self.agency_b.id,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        new = UnmatchedPayment.objects.get(reference="FORCED-REF")
        self.assertEqual(new.agency_id, self.agency_a.id)
