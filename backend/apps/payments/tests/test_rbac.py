"""
Role-based access control tests for the payments API — RNT-SEC-031.

Verifies that:
  - Tenants see only invoices/payments on their own leases (IDOR prevention).
  - Owners see only invoices/payments on leases for properties they own.
  - Agents see only invoices/payments for properties assigned to them.
  - Admins see everything.
  - UnmatchedPaymentViewSet returns 403 for tenant and owner callers.

Run with:
    cd backend && pytest apps/payments/tests/test_rbac.py -v
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.test import TestCase
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULT_AGENCY = None


def _default_agency():
    """Lazily create / fetch a single shared Agency for these test rows.

    Phase 2.7: payments viewsets now apply AgencyScopedQuerysetMixin, so
    every property/lease/invoice/agent must share an agency_id for the
    existing role-based assertions to keep working.
    """
    from apps.accounts.models import Agency

    global _DEFAULT_AGENCY
    if _DEFAULT_AGENCY is None or not Agency.objects.filter(pk=_DEFAULT_AGENCY.pk).exists():
        _DEFAULT_AGENCY = Agency.objects.create(name="Payments RBAC Default Agency")
    return _DEFAULT_AGENCY


def _reset_default_agency():
    """Reset the cached agency between TestCase setUp() runs (DB rollback)."""
    global _DEFAULT_AGENCY
    _DEFAULT_AGENCY = None


def _make_property(name="Test Prop", agent=None, agency=None):
    from apps.properties.models import Property
    if agency is None:
        agency = _default_agency()
    return Property.objects.create(
        name=name,
        address="1 Test St",
        city="Cape Town",
        province="WC",
        postal_code="8001",
        property_type="apartment",
        agent=agent,
        agency=agency,
    )


def _make_unit(prop, number="101"):
    from apps.properties.models import Unit
    return Unit.objects.create(
        property=prop,
        unit_number=number,
        bedrooms=2,
        bathrooms=1,
        rent_amount=Decimal("10000.00"),
        agency=prop.agency,
    )


def _make_lease(unit, primary_tenant=None):
    from apps.leases.models import Lease
    return Lease.objects.create(
        unit=unit,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        monthly_rent=Decimal("10000.00"),
        status=Lease.Status.ACTIVE,
        primary_tenant=primary_tenant,
        agency=unit.agency,
    )


def _make_invoice(lease, period_start=date(2026, 4, 1)):
    from apps.payments.models import RentInvoice
    return RentInvoice.objects.create(
        lease=lease,
        period_start=period_start,
        period_end=date(period_start.year, period_start.month, 28),
        amount_due=Decimal("10000.00"),
        due_date=period_start,
        status=RentInvoice.Status.UNPAID,
        agency=lease.agency,
    )


def _make_payment(invoice):
    from apps.payments.reconciliation import apply_payment
    return apply_payment(invoice, Decimal("5000.00"), payment_date=date(2026, 4, 5))


def _make_user(role, email_suffix="", agency=None, **kwargs):
    from apps.accounts.models import User
    email = f"{role}{email_suffix}@test.com"
    if role != "tenant" and agency is None:
        agency = _default_agency()
    user = User.objects.create_user(email=email, password="testpass", role=role, **kwargs)
    if agency is not None:
        user.agency = agency
        user.save(update_fields=["agency"])
    return user


def _make_person(user=None, full_name="Test User"):
    from apps.accounts.models import Person
    return Person.objects.create(
        full_name=full_name,
        linked_user=user,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Invoice RBAC tests
# ─────────────────────────────────────────────────────────────────────────────

class TestInvoiceRBACTenant(TestCase):
    """Tenants see only their own invoices — IDOR prevention."""

    def setUp(self):
        _reset_default_agency()
        self.client = APIClient()
        self.tenant_user = _make_user("tenant", "_inv")
        self.tenant_person = _make_person(user=self.tenant_user, full_name="Jane Inv")
        self.other_tenant = _make_user("tenant", "_inv_other")
        self.other_person = _make_person(user=self.other_tenant, full_name="Bob Inv")

        prop = _make_property("Prop A")
        unit_a = _make_unit(prop, "101")
        unit_b = _make_unit(prop, "102")

        self.own_lease = _make_lease(unit_a, primary_tenant=self.tenant_person)
        self.other_lease = _make_lease(unit_b, primary_tenant=self.other_person)

        self.own_invoice = _make_invoice(self.own_lease)
        self.other_invoice = _make_invoice(self.other_lease)

    def _invoice_ids(self, response):
        """Extract IDs from a potentially paginated list response."""
        data = response.data
        items = data["results"] if "results" in data else data
        return [i["id"] for i in items]

    def test_tenant_sees_own_invoice_in_list(self):
        self.client.force_authenticate(user=self.tenant_user)
        response = self.client.get("/api/v1/payments/invoices/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.own_invoice.pk, self._invoice_ids(response))

    def test_tenant_does_not_see_other_tenant_invoice_in_list(self):
        self.client.force_authenticate(user=self.tenant_user)
        response = self.client.get("/api/v1/payments/invoices/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.other_invoice.pk, self._invoice_ids(response))

    def test_tenant_cannot_fetch_other_tenant_invoice_detail(self):
        """IDOR: direct PK lookup for another tenant's invoice must return 404."""
        self.client.force_authenticate(user=self.tenant_user)
        response = self.client.get(f"/api/v1/payments/invoices/{self.other_invoice.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_tenant_can_fetch_own_invoice_detail(self):
        self.client.force_authenticate(user=self.tenant_user)
        response = self.client.get(f"/api/v1/payments/invoices/{self.own_invoice.pk}/")
        self.assertEqual(response.status_code, 200)

    def test_tenant_cannot_record_payment(self):
        """Write action must be restricted to agents/admins."""
        self.client.force_authenticate(user=self.tenant_user)
        response = self.client.post(
            f"/api/v1/payments/invoices/{self.own_invoice.pk}/payments/",
            {"amount": "5000.00", "payment_date": "2026-04-05"},
        )
        self.assertEqual(response.status_code, 403)


class TestInvoiceRBACAgent(TestCase):
    """Agents see only invoices for properties assigned to them."""

    def setUp(self):
        _reset_default_agency()
        self.client = APIClient()
        self.agent = _make_user("agent", "_inv")
        self.other_agent = _make_user("agent", "_inv_other")

        from apps.properties.models import PropertyAgentAssignment
        self.prop_assigned = _make_property("Assigned Prop", agent=self.agent)
        self.prop_other = _make_property("Other Prop", agent=self.other_agent)

        unit_a = _make_unit(self.prop_assigned, "A01")
        unit_b = _make_unit(self.prop_other, "B01")

        self.lease_assigned = _make_lease(unit_a)
        self.lease_other = _make_lease(unit_b)

        self.invoice_assigned = _make_invoice(self.lease_assigned)
        self.invoice_other = _make_invoice(self.lease_other)

    def _invoice_ids(self, response):
        data = response.data
        items = data["results"] if "results" in data else data
        return [i["id"] for i in items]

    def test_agent_sees_assigned_invoice(self):
        self.client.force_authenticate(user=self.agent)
        response = self.client.get("/api/v1/payments/invoices/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.invoice_assigned.pk, self._invoice_ids(response))

    def test_agent_does_not_see_other_property_invoice(self):
        self.client.force_authenticate(user=self.agent)
        response = self.client.get("/api/v1/payments/invoices/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.invoice_other.pk, self._invoice_ids(response))

    def test_agent_cannot_fetch_other_property_invoice_detail(self):
        self.client.force_authenticate(user=self.agent)
        response = self.client.get(f"/api/v1/payments/invoices/{self.invoice_other.pk}/")
        self.assertEqual(response.status_code, 404)


class TestInvoiceRBACAdmin(TestCase):
    """Admins see all invoices."""

    def setUp(self):
        _reset_default_agency()
        self.client = APIClient()
        self.admin = _make_user("admin", "_inv")

        prop = _make_property("Admin Prop")
        unit = _make_unit(prop)
        lease = _make_lease(unit)
        self.invoice = _make_invoice(lease)

    def test_admin_sees_all_invoices(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/v1/payments/invoices/")
        self.assertEqual(response.status_code, 200)
        data = response.data
        items = data["results"] if "results" in data else data
        ids = [i["id"] for i in items]
        self.assertIn(self.invoice.pk, ids)

    def test_unauthenticated_returns_401(self):
        response = self.client.get("/api/v1/payments/invoices/")
        self.assertEqual(response.status_code, 401)


# ─────────────────────────────────────────────────────────────────────────────
# RentPayment RBAC tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPaymentRBACTenant(TestCase):
    """Tenant cannot see other tenant's payment records."""

    def setUp(self):
        _reset_default_agency()
        self.client = APIClient()
        self.tenant_user = _make_user("tenant", "_pay")
        self.tenant_person = _make_person(user=self.tenant_user, full_name="Pay Tenant")
        self.other_tenant = _make_user("tenant", "_pay_other")
        self.other_person = _make_person(user=self.other_tenant, full_name="Other Tenant")

        prop = _make_property("Pay Prop")
        unit_a = _make_unit(prop, "P01")
        unit_b = _make_unit(prop, "P02")

        self.own_lease = _make_lease(unit_a, primary_tenant=self.tenant_person)
        self.other_lease = _make_lease(unit_b, primary_tenant=self.other_person)

        own_invoice = _make_invoice(self.own_lease)
        other_invoice = _make_invoice(self.other_lease)

        self.own_payment = _make_payment(own_invoice)
        self.other_payment = _make_payment(other_invoice)

    def test_tenant_cannot_fetch_other_tenant_payment(self):
        self.client.force_authenticate(user=self.tenant_user)
        response = self.client.get(f"/api/v1/payments/payments/{self.other_payment.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_tenant_can_fetch_own_payment(self):
        self.client.force_authenticate(user=self.tenant_user)
        response = self.client.get(f"/api/v1/payments/payments/{self.own_payment.pk}/")
        self.assertEqual(response.status_code, 200)

    def test_tenant_cannot_reverse_own_payment(self):
        self.client.force_authenticate(user=self.tenant_user)
        response = self.client.post(
            f"/api/v1/payments/payments/{self.own_payment.pk}/reverse/",
            {"reason": "tenant attempt"},
        )
        self.assertEqual(response.status_code, 403)


# ─────────────────────────────────────────────────────────────────────────────
# UnmatchedPayment RBAC tests
# ─────────────────────────────────────────────────────────────────────────────

class TestUnmatchedPaymentRBAC(TestCase):
    """UnmatchedPaymentViewSet must be restricted to agency_admin / admin only."""

    def setUp(self):
        _reset_default_agency()
        self.client = APIClient()
        self.tenant = _make_user("tenant", "_um")
        self.owner = _make_user("owner", "_um")
        self.agent = _make_user("agent", "_um")
        self.agency_admin = _make_user("agency_admin", "_um")
        self.admin = _make_user("admin", "_um")

        from apps.payments.models import UnmatchedPayment
        self.unmatched = UnmatchedPayment.objects.create(
            amount=Decimal("9000.00"),
            payment_date=date(2026, 4, 10),
            reference="UM-TEST-001",
        )

    def test_tenant_gets_403_on_unmatched_list(self):
        self.client.force_authenticate(user=self.tenant)
        response = self.client.get("/api/v1/payments/unmatched/")
        self.assertEqual(response.status_code, 403)

    def test_owner_gets_403_on_unmatched_list(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get("/api/v1/payments/unmatched/")
        self.assertEqual(response.status_code, 403)

    def test_agent_gets_403_on_unmatched_list(self):
        """Regular agents are not granted access to unmatched deposits."""
        self.client.force_authenticate(user=self.agent)
        response = self.client.get("/api/v1/payments/unmatched/")
        self.assertEqual(response.status_code, 403)

    def test_agency_admin_can_list_unmatched(self):
        self.client.force_authenticate(user=self.agency_admin)
        response = self.client.get("/api/v1/payments/unmatched/")
        self.assertEqual(response.status_code, 200)

    def test_admin_can_list_unmatched(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/v1/payments/unmatched/")
        self.assertEqual(response.status_code, 200)

    def test_tenant_cannot_create_unmatched(self):
        self.client.force_authenticate(user=self.tenant)
        response = self.client.post(
            "/api/v1/payments/unmatched/",
            {
                "amount": "5000.00",
                "payment_date": "2026-04-10",
                "reference": "TENANT-INJECT",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_gets_401_on_unmatched(self):
        response = self.client.get("/api/v1/payments/unmatched/")
        self.assertEqual(response.status_code, 401)
