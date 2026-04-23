"""
Regression test for RNT-QUAL-039: invoice ?search= using Person.full_name.

Previously, the search filter used non-existent `first_name`/`last_name` fields
on Person (which only has `full_name`), causing silent zero results for any
tenant name search.

Run with:
    cd backend && pytest apps/payments/tests/test_invoice_search.py -v
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.test import TestCase
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


# ─────────────────────────────────────────────────────────────────────────────
# Helpers (minimal, self-contained)
# ─────────────────────────────────────────────────────────────────────────────

def _make_user(role, email):
    from apps.accounts.models import User
    return User.objects.create_user(email=email, password="testpass", role=role)


def _make_person(full_name, user=None):
    from apps.accounts.models import Person
    return Person.objects.create(full_name=full_name, linked_user=user)


def _make_property():
    from apps.properties.models import Property
    return Property.objects.create(
        name="Search Test Prop",
        address="1 Test St",
        city="Cape Town",
        province="WC",
        postal_code="8001",
        property_type="apartment",
    )


def _make_unit(prop, number="101"):
    from apps.properties.models import Unit
    return Unit.objects.create(
        property=prop,
        unit_number=number,
        bedrooms=1,
        bathrooms=1,
        rent_amount=Decimal("8000.00"),
    )


def _make_lease(unit, primary_tenant=None):
    from apps.leases.models import Lease
    return Lease.objects.create(
        unit=unit,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        monthly_rent=Decimal("8000.00"),
        status=Lease.Status.ACTIVE,
        primary_tenant=primary_tenant,
    )


def _make_invoice(lease, period_start=date(2026, 4, 1)):
    from apps.payments.models import RentInvoice
    return RentInvoice.objects.create(
        lease=lease,
        period_start=period_start,
        period_end=date(period_start.year, period_start.month, 28),
        amount_due=Decimal("8000.00"),
        due_date=period_start,
        status=RentInvoice.Status.UNPAID,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestInvoiceSearchByTenantName(TestCase):
    """
    Verifies that GET /api/v1/payments/invoices/?search=<name> correctly
    matches against Person.full_name instead of the non-existent
    first_name/last_name fields.
    """

    def setUp(self):
        self.client = APIClient()
        self.admin = _make_user("admin", "admin-search@test.com")

        prop = _make_property()
        unit_a = _make_unit(prop, "201")
        unit_b = _make_unit(prop, "202")

        self.person_sipho = _make_person("Sipho Dlamini")
        self.person_fatima = _make_person("Fatima van der Merwe")

        lease_sipho = _make_lease(unit_a, primary_tenant=self.person_sipho)
        lease_fatima = _make_lease(unit_b, primary_tenant=self.person_fatima)

        self.invoice_sipho = _make_invoice(lease_sipho)
        self.invoice_fatima = _make_invoice(lease_fatima)

        self.client.force_authenticate(user=self.admin)

    def _invoice_ids(self, response):
        data = response.data
        items = data.get("results", data)
        return [i["id"] for i in items]

    def test_search_by_full_name_exact_match(self):
        """Searching by a tenant's exact full name returns their invoice."""
        response = self.client.get("/api/v1/payments/invoices/", {"search": "Sipho Dlamini"})
        self.assertEqual(response.status_code, 200)
        ids = self._invoice_ids(response)
        self.assertIn(self.invoice_sipho.pk, ids)
        self.assertNotIn(self.invoice_fatima.pk, ids)

    def test_search_by_partial_name(self):
        """Searching by a partial name (first token) returns the matching invoice."""
        response = self.client.get("/api/v1/payments/invoices/", {"search": "Fatima"})
        self.assertEqual(response.status_code, 200)
        ids = self._invoice_ids(response)
        self.assertIn(self.invoice_fatima.pk, ids)
        self.assertNotIn(self.invoice_sipho.pk, ids)

    def test_search_by_surname(self):
        """Searching by surname portion returns the correct invoice."""
        response = self.client.get("/api/v1/payments/invoices/", {"search": "Dlamini"})
        self.assertEqual(response.status_code, 200)
        ids = self._invoice_ids(response)
        self.assertIn(self.invoice_sipho.pk, ids)
        self.assertNotIn(self.invoice_fatima.pk, ids)

    def test_search_no_match_returns_empty(self):
        """Searching by a name that doesn't exist returns an empty result set."""
        response = self.client.get("/api/v1/payments/invoices/", {"search": "Nonexistent Person"})
        self.assertEqual(response.status_code, 200)
        ids = self._invoice_ids(response)
        self.assertEqual(ids, [])

    def test_search_case_insensitive(self):
        """Full name search is case-insensitive (icontains)."""
        response = self.client.get("/api/v1/payments/invoices/", {"search": "sipho"})
        self.assertEqual(response.status_code, 200)
        ids = self._invoice_ids(response)
        self.assertIn(self.invoice_sipho.pk, ids)
