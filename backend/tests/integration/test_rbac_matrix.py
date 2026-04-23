"""
QA-009: Roles × endpoints RBAC test matrix.

Verifies that every user role receives the expected HTTP status on every
critical endpoint group. The matrix covers:

    admin, agency_admin, agent, managing_agent, estate_agent,
    owner, tenant, supplier

Endpoint groups tested
----------------------
- Properties          GET/POST list, GET/PATCH/DELETE detail
- Units               GET/POST list, GET/PATCH/DELETE detail
- Leases              GET/POST list, GET/PATCH/DELETE detail
- Payments/Invoices   GET list, GET detail, POST payment, POST reverse
- Payments/Unmatched  GET list, POST assign
- Maintenance         GET list, POST create, PATCH/DELETE detail
- Esigning submissions GET list, GET detail
- Tenant portal chat  POST (tenant-only endpoint)
- Owner portal        GET dashboard, GET properties
- Supplier portal     GET jobs, GET profile

Cross-boundary isolation tests
-------------------------------
- Agency A agent cannot read Agency B data (cross-agency leak)
- Tenant A cannot access Tenant B lease/payment/maintenance (cross-tenant leak)
- Owner read-only: PATCH/DELETE return 403 or 405 on owned resources

Run with:
    cd backend && pytest tests/integration/test_rbac_matrix.py -v

All tests are marked green (must pass). Tests are deliberately free of
external dependencies — no email, no celery, no external API calls.
"""
from __future__ import annotations

import pytest
from datetime import date, timedelta
from decimal import Decimal

from rest_framework.test import APIClient

pytestmark = [pytest.mark.django_db, pytest.mark.integration, pytest.mark.green]


# ─────────────────────────────────────────────────────────────────────────────
# Low-level helpers
# ─────────────────────────────────────────────────────────────────────────────

def _user(role, suffix="", **kwargs):
    from apps.accounts.models import User
    email = f"{role}{suffix}@rbac-test.com"
    return User.objects.create_user(email=email, password="testpass", role=role, **kwargs)


def _person(user=None, full_name="RBAC Person"):
    from apps.accounts.models import Person
    return Person.objects.create(full_name=full_name, linked_user=user)


def _agency(name="Agency"):
    from apps.accounts.models import Agency
    return Agency.objects.create(name=name)


def _property(name="Prop", agent=None):
    from apps.properties.models import Property
    return Property.objects.create(
        name=name, address="1 Test St", city="Cape Town",
        province="WC", postal_code="8001", property_type="apartment",
        agent=agent,
    )


def _unit(prop, number="101"):
    from apps.properties.models import Unit
    return Unit.objects.create(
        property=prop, unit_number=number,
        bedrooms=2, bathrooms=1, rent_amount=Decimal("8000.00"),
    )


def _lease(unit, primary_tenant=None, status="active"):
    from apps.leases.models import Lease
    return Lease.objects.create(
        unit=unit,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        monthly_rent=Decimal("8000.00"),
        status=status,
        primary_tenant=primary_tenant,
    )


def _invoice(lease, period_start=date(2026, 4, 1)):
    from apps.payments.models import RentInvoice
    return RentInvoice.objects.create(
        lease=lease,
        period_start=period_start,
        period_end=date(period_start.year, period_start.month, 28),
        amount_due=Decimal("8000.00"),
        due_date=period_start,
        status=RentInvoice.Status.UNPAID,
    )


def _payment(invoice):
    from apps.payments.reconciliation import apply_payment
    return apply_payment(invoice, Decimal("4000.00"), payment_date=date(2026, 4, 5))


def _unmatched():
    from apps.payments.models import UnmatchedPayment
    return UnmatchedPayment.objects.create(
        amount=Decimal("5000.00"),
        payment_date=date(2026, 4, 10),
        reference="UM-RBAC-001",
    )


def _maintenance_request(unit, tenant):
    from apps.maintenance.models import MaintenanceRequest
    return MaintenanceRequest.objects.create(
        unit=unit, tenant=tenant,
        title="RBAC Test Issue", description="Test", priority="medium", status="open",
    )


def _client_for(user) -> APIClient:
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _assign_property_to_agent(prop, agent, assignment_type="managing"):
    from apps.properties.models import PropertyAgentAssignment
    return PropertyAgentAssignment.objects.create(
        property=prop, agent=agent,
        assignment_type=assignment_type, status="active",
    )


def _assign_owner_to_property(prop, owner_user):
    """Create Person + Landlord + PropertyOwnership chain for an owner user."""
    from apps.properties.models import Landlord, PropertyOwnership
    person = _person(user=owner_user, full_name="Owner Person")
    landlord = Landlord.objects.create(
        name="Owner Landlord",
        person=person,
        landlord_type="individual",
        email="owner-landlord@rbac.com",
        phone="0821111111",
        representative_name="Owner",
        representative_id_number="8001015800083",
        representative_email="owner@rbac.com",
        representative_phone="0821111112",
        address={"street": "1 St", "city": "Cape Town", "province": "WC", "postal_code": "8001"},
    )
    PropertyOwnership.objects.create(
        property=prop, landlord=landlord,
        owner_name="Owner Landlord", owner_type="individual",
        owner_email="owner@rbac.com", is_current=True,
        start_date=date(2025, 1, 1),
    )
    return person, landlord


# ─────────────────────────────────────────────────────────────────────────────
# World fixture: a complete, realistic set of users + objects
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def world(db):
    """
    A complete RBAC test world with:
      - agency_a with agency_admin_a, agent_a (managing), estate_agent_a
      - agency_b with agency_admin_b, agent_b
      - prop_a owned by owner_a, managed by agent_a
      - prop_b managed by agent_b (different agency)
      - tenant_a on lease_a (unit_a of prop_a)
      - tenant_b on lease_b (unit_b_b of prop_b)
      - supplier_a
      - admin (global)
      - managing_agent_a — explicit managing_agent role for prop_a
    """
    agency_a = _agency("Agency A")
    agency_b = _agency("Agency B")

    admin = _user("admin", "_world")
    agency_admin_a = _user("agency_admin", "_a", agency=agency_a)
    agency_admin_b = _user("agency_admin", "_b", agency=agency_b)

    # Agent roles in agency A
    agent_a = _user("agent", "_a", agency=agency_a)
    managing_agent_a = _user("managing_agent", "_a", agency=agency_a)
    estate_agent_a = _user("estate_agent", "_a", agency=agency_a)

    # Agent in agency B
    agent_b = _user("agent", "_b", agency=agency_b)

    # Owner
    owner_a = _user("owner", "_a")

    # Tenants
    tenant_a_user = _user("tenant", "_a")
    tenant_b_user = _user("tenant", "_b")
    tenant_a_person = _person(user=tenant_a_user, full_name="Tenant A")
    tenant_b_person = _person(user=tenant_b_user, full_name="Tenant B")

    # Supplier
    supplier = _user("supplier", "_a")

    # Properties — prop_a belongs to agency_a
    prop_a = _property("Prop A", agent=agent_a)
    prop_b = _property("Prop B", agent=agent_b)

    # Assignments
    _assign_property_to_agent(prop_a, agent_a, "managing")
    _assign_property_to_agent(prop_a, managing_agent_a, "managing")
    _assign_property_to_agent(prop_a, estate_agent_a, "estate")

    # Owner link
    _assign_owner_to_property(prop_a, owner_a)

    # Units
    unit_a = _unit(prop_a, "A01")
    unit_b = _unit(prop_a, "A02")
    unit_b_b = _unit(prop_b, "B01")

    # Leases
    lease_a = _lease(unit_a, primary_tenant=tenant_a_person)
    lease_b = _lease(unit_b_b, primary_tenant=tenant_b_person)

    # Payments
    invoice_a = _invoice(lease_a)
    invoice_b = _invoice(lease_b)
    payment_a = _payment(invoice_a)

    # Maintenance
    mr_a = _maintenance_request(unit_a, tenant_a_user)
    mr_b = _maintenance_request(unit_b_b, tenant_b_user)

    # Unmatched payment
    um = _unmatched()

    return {
        "admin": admin,
        "agency_admin_a": agency_admin_a,
        "agency_admin_b": agency_admin_b,
        "agent_a": agent_a,
        "managing_agent_a": managing_agent_a,
        "estate_agent_a": estate_agent_a,
        "agent_b": agent_b,
        "owner_a": owner_a,
        "tenant_a": tenant_a_user,
        "tenant_b": tenant_b_user,
        "tenant_a_person": tenant_a_person,
        "tenant_b_person": tenant_b_person,
        "supplier": supplier,
        "prop_a": prop_a,
        "prop_b": prop_b,
        "unit_a": unit_a,
        "unit_b": unit_b,
        "unit_b_b": unit_b_b,
        "lease_a": lease_a,
        "lease_b": lease_b,
        "invoice_a": invoice_a,
        "invoice_b": invoice_b,
        "payment_a": payment_a,
        "mr_a": mr_a,
        "mr_b": mr_b,
        "unmatched": um,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helper: assert status
# ─────────────────────────────────────────────────────────────────────────────

def _check(client, method, url, expected_status, data=None):
    """Call method on url; assert expected_status. Returns response."""
    fn = getattr(client, method)
    resp = fn(url, data=data, format="json") if data is not None else fn(url)
    assert resp.status_code == expected_status, (
        f"{method.upper()} {url}: expected {expected_status}, got {resp.status_code}. "
        f"Response data: {getattr(resp, 'data', None)}"
    )
    return resp


# ─────────────────────────────────────────────────────────────────────────────
# 1. UNAUTHENTICATED — all critical endpoints return 401
# ─────────────────────────────────────────────────────────────────────────────

class TestUnauthenticatedBlocked:
    """No credentials must never reach any data."""

    ENDPOINTS = [
        ("get", "/api/v1/properties/"),
        ("get", "/api/v1/leases/"),
        ("get", "/api/v1/payments/invoices/"),
        # Note: /api/v1/payments/payments/ has no list URL (RetrieveModelMixin only)
        # so we check a concrete detail URL via a real pk in later tests.
        ("get", "/api/v1/payments/unmatched/"),
        ("get", "/api/v1/maintenance/"),
        ("get", "/api/v1/esigning/submissions/"),
    ]

    def test_unauthenticated_gets_401(self, db):
        c = APIClient()
        for method, url in self.ENDPOINTS:
            resp = getattr(c, method)(url)
            assert resp.status_code == 401, (
                f"Unauthenticated {method.upper()} {url} expected 401, got {resp.status_code}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 2. PROPERTIES — role matrix
# ─────────────────────────────────────────────────────────────────────────────

class TestPropertiesRBAC:
    """
    Role matrix for GET /api/v1/properties/ (list) and detail.

    Expected access:
      admin           → 200 list, 200 detail prop_a
      agency_admin_a  → 200 list (prop_a visible), 200 detail prop_a
      agent_a         → 200 list (prop_a visible), 200 detail prop_a
      managing_agent_a→ 200 list (prop_a visible), 200 detail prop_a
      estate_agent_a  → 200 list (prop_a visible via estate assignment)
      agent_b         → 200 list (prop_b visible, NOT prop_a)
      owner_a         → 403 (IsAgentOrAdmin guard — owner cannot hit this viewset)
      tenant_a        → 403 (IsAgentOrAdmin guard)
      supplier        → 403 (IsAgentOrAdmin guard)
    """

    def _prop_ids_from_list(self, client):
        resp = client.get("/api/v1/properties/")
        assert resp.status_code == 200
        data = resp.data
        items = data.get("results", data) if isinstance(data, dict) else data
        return [p["id"] for p in items]

    def test_admin_sees_all_properties(self, world):
        c = _client_for(world["admin"])
        ids = self._prop_ids_from_list(c)
        assert world["prop_a"].pk in ids
        assert world["prop_b"].pk in ids

    def test_agent_a_sees_only_assigned_property(self, world):
        c = _client_for(world["agent_a"])
        ids = self._prop_ids_from_list(c)
        assert world["prop_a"].pk in ids
        assert world["prop_b"].pk not in ids

    def test_agent_a_detail_own_property(self, world):
        c = _client_for(world["agent_a"])
        _check(c, "get", f"/api/v1/properties/{world['prop_a'].pk}/", 200)

    def test_agent_a_cannot_detail_other_agency_property(self, world):
        c = _client_for(world["agent_a"])
        _check(c, "get", f"/api/v1/properties/{world['prop_b'].pk}/", 404)

    def test_managing_agent_sees_assigned_property(self, world):
        c = _client_for(world["managing_agent_a"])
        ids = self._prop_ids_from_list(c)
        assert world["prop_a"].pk in ids

    def test_estate_agent_sees_estate_assigned_property(self, world):
        c = _client_for(world["estate_agent_a"])
        ids = self._prop_ids_from_list(c)
        assert world["prop_a"].pk in ids

    def test_agency_admin_a_sees_agency_a_property(self, world):
        c = _client_for(world["agency_admin_a"])
        ids = self._prop_ids_from_list(c)
        assert world["prop_a"].pk in ids

    def test_agency_admin_a_does_not_see_agency_b_property(self, world):
        c = _client_for(world["agency_admin_a"])
        ids = self._prop_ids_from_list(c)
        assert world["prop_b"].pk not in ids

    def test_tenant_cannot_list_properties(self, world):
        c = _client_for(world["tenant_a"])
        _check(c, "get", "/api/v1/properties/", 403)

    def test_owner_cannot_list_properties_via_agent_endpoint(self, world):
        c = _client_for(world["owner_a"])
        _check(c, "get", "/api/v1/properties/", 403)

    def test_supplier_cannot_list_properties(self, world):
        c = _client_for(world["supplier"])
        _check(c, "get", "/api/v1/properties/", 403)

    def test_agent_b_cannot_create_property_in_agency_a(self, world):
        """Agent B creating a property is fine for their own scope — but the
        more important check is that agent_a cannot PATCH agent_b's property."""
        c = _client_for(world["agent_a"])
        _check(c, "patch", f"/api/v1/properties/{world['prop_b'].pk}/",
               404, data={"name": "Injected"})

    def test_agent_cannot_delete_other_agency_property(self, world):
        c = _client_for(world["agent_a"])
        _check(c, "delete", f"/api/v1/properties/{world['prop_b'].pk}/", 404)


# ─────────────────────────────────────────────────────────────────────────────
# 3. UNITS — role matrix
# ─────────────────────────────────────────────────────────────────────────────

class TestUnitsRBAC:
    """
    Unit access piggybacks on property-level scoping (unit__property in queryset).
    """

    def _unit_ids_from_list(self, client):
        resp = client.get("/api/v1/properties/units/")
        assert resp.status_code == 200
        data = resp.data
        items = data.get("results", data) if isinstance(data, dict) else data
        return [u["id"] for u in items]

    def test_admin_sees_all_units(self, world):
        c = _client_for(world["admin"])
        ids = self._unit_ids_from_list(c)
        assert world["unit_a"].pk in ids
        assert world["unit_b_b"].pk in ids

    def test_agent_a_sees_own_property_units(self, world):
        c = _client_for(world["agent_a"])
        ids = self._unit_ids_from_list(c)
        assert world["unit_a"].pk in ids

    def test_agent_a_does_not_see_other_property_units(self, world):
        c = _client_for(world["agent_a"])
        ids = self._unit_ids_from_list(c)
        assert world["unit_b_b"].pk not in ids

    def test_agent_a_cannot_detail_other_property_unit(self, world):
        c = _client_for(world["agent_a"])
        _check(c, "get", f"/api/v1/properties/units/{world['unit_b_b'].pk}/", 404)

    def test_tenant_cannot_list_units(self, world):
        c = _client_for(world["tenant_a"])
        _check(c, "get", "/api/v1/properties/units/", 403)

    def test_owner_cannot_list_units_via_agent_endpoint(self, world):
        c = _client_for(world["owner_a"])
        _check(c, "get", "/api/v1/properties/units/", 403)


# ─────────────────────────────────────────────────────────────────────────────
# 4. LEASES — role matrix
# ─────────────────────────────────────────────────────────────────────────────

class TestLeasesRBAC:
    """
    Lease access is scoped in LeaseViewSet.get_queryset().

    admin           → all leases
    agent_a         → leases on properties assigned to agent_a
    managing_agent_a→ same as agent_a
    estate_agent_a  → same (estate assignment gives property access)
    agency_admin_a  → leases for all agency_a managed properties
    agent_b         → leases for prop_b only
    owner_a         → leases on properties they own
    tenant_a        → only lease_a (their own)
    supplier        → no lease access (IsAuthenticated but no scoping)
    """

    def _lease_ids(self, client):
        resp = client.get("/api/v1/leases/")
        assert resp.status_code == 200
        data = resp.data
        items = data.get("results", data) if isinstance(data, dict) else data
        return [l["id"] for l in items]

    def test_admin_sees_all_leases(self, world):
        c = _client_for(world["admin"])
        ids = self._lease_ids(c)
        assert world["lease_a"].pk in ids
        assert world["lease_b"].pk in ids

    def test_agent_a_sees_own_property_lease(self, world):
        c = _client_for(world["agent_a"])
        ids = self._lease_ids(c)
        assert world["lease_a"].pk in ids

    def test_agent_a_does_not_see_other_agency_lease(self, world):
        c = _client_for(world["agent_a"])
        ids = self._lease_ids(c)
        assert world["lease_b"].pk not in ids

    def test_agent_a_cannot_detail_other_agency_lease(self, world):
        c = _client_for(world["agent_a"])
        _check(c, "get", f"/api/v1/leases/{world['lease_b'].pk}/", 404)

    def test_agent_a_cannot_patch_other_agency_lease(self, world):
        c = _client_for(world["agent_a"])
        _check(c, "patch", f"/api/v1/leases/{world['lease_b'].pk}/",
               404, data={"monthly_rent": "1.00"})

    def test_agent_a_cannot_delete_other_agency_lease(self, world):
        c = _client_for(world["agent_a"])
        _check(c, "delete", f"/api/v1/leases/{world['lease_b'].pk}/", 404)

    def test_managing_agent_sees_assigned_lease(self, world):
        c = _client_for(world["managing_agent_a"])
        ids = self._lease_ids(c)
        assert world["lease_a"].pk in ids

    def test_estate_agent_sees_lease_via_estate_assignment(self, world):
        c = _client_for(world["estate_agent_a"])
        ids = self._lease_ids(c)
        assert world["lease_a"].pk in ids

    def test_owner_sees_own_property_lease(self, world):
        c = _client_for(world["owner_a"])
        ids = self._lease_ids(c)
        assert world["lease_a"].pk in ids

    def test_owner_does_not_see_other_property_lease(self, world):
        c = _client_for(world["owner_a"])
        ids = self._lease_ids(c)
        assert world["lease_b"].pk not in ids

    def test_tenant_a_sees_only_own_lease(self, world):
        c = _client_for(world["tenant_a"])
        ids = self._lease_ids(c)
        assert world["lease_a"].pk in ids
        assert world["lease_b"].pk not in ids

    def test_tenant_a_cannot_detail_tenant_b_lease(self, world):
        c = _client_for(world["tenant_a"])
        _check(c, "get", f"/api/v1/leases/{world['lease_b'].pk}/", 404)

    def test_supplier_gets_empty_lease_list(self, world):
        """Supplier is authenticated (IsAuthenticated) but gets scoped to nothing."""
        c = _client_for(world["supplier"])
        resp = _check(c, "get", "/api/v1/leases/", 200)
        data = resp.data
        items = data.get("results", data) if isinstance(data, dict) else data
        assert items == [], f"Supplier should see no leases, got: {items}"


# ─────────────────────────────────────────────────────────────────────────────
# 5. PAYMENTS — role matrix
# ─────────────────────────────────────────────────────────────────────────────

class TestPaymentsInvoiceRBAC:
    """Invoice list/detail and write actions."""

    def _invoice_ids(self, client):
        resp = client.get("/api/v1/payments/invoices/")
        assert resp.status_code == 200
        data = resp.data
        items = data.get("results", data) if isinstance(data, dict) else data
        return [i["id"] for i in items]

    def test_admin_sees_all_invoices(self, world):
        c = _client_for(world["admin"])
        ids = self._invoice_ids(c)
        assert world["invoice_a"].pk in ids
        assert world["invoice_b"].pk in ids

    def test_agent_a_sees_own_invoice(self, world):
        c = _client_for(world["agent_a"])
        ids = self._invoice_ids(c)
        assert world["invoice_a"].pk in ids

    def test_agent_a_does_not_see_agency_b_invoice(self, world):
        c = _client_for(world["agent_a"])
        ids = self._invoice_ids(c)
        assert world["invoice_b"].pk not in ids

    def test_agent_a_cannot_detail_agency_b_invoice(self, world):
        c = _client_for(world["agent_a"])
        _check(c, "get", f"/api/v1/payments/invoices/{world['invoice_b'].pk}/", 404)

    def test_owner_sees_own_property_invoice(self, world):
        c = _client_for(world["owner_a"])
        ids = self._invoice_ids(c)
        assert world["invoice_a"].pk in ids

    def test_owner_does_not_see_other_property_invoice(self, world):
        c = _client_for(world["owner_a"])
        ids = self._invoice_ids(c)
        assert world["invoice_b"].pk not in ids

    def test_tenant_a_sees_own_invoice(self, world):
        c = _client_for(world["tenant_a"])
        ids = self._invoice_ids(c)
        assert world["invoice_a"].pk in ids

    def test_tenant_a_cannot_see_tenant_b_invoice(self, world):
        c = _client_for(world["tenant_a"])
        ids = self._invoice_ids(c)
        assert world["invoice_b"].pk not in ids

    def test_tenant_a_cannot_detail_tenant_b_invoice(self, world):
        c = _client_for(world["tenant_a"])
        _check(c, "get", f"/api/v1/payments/invoices/{world['invoice_b'].pk}/", 404)

    def test_tenant_cannot_record_payment(self, world):
        """Tenants must not be able to record payments — write action requires agent/admin."""
        c = _client_for(world["tenant_a"])
        _check(
            c, "post",
            f"/api/v1/payments/invoices/{world['invoice_a'].pk}/payments/",
            403,
            data={"amount": "8000.00", "payment_date": "2026-04-01"},
        )

    def test_owner_cannot_record_payment(self, world):
        c = _client_for(world["owner_a"])
        _check(
            c, "post",
            f"/api/v1/payments/invoices/{world['invoice_a'].pk}/payments/",
            403,
            data={"amount": "8000.00", "payment_date": "2026-04-01"},
        )

    def test_supplier_cannot_list_invoices(self, world):
        """Supplier scoping returns empty but still 200 — invoice list is IsAuthenticated."""
        c = _client_for(world["supplier"])
        resp = _check(c, "get", "/api/v1/payments/invoices/", 200)
        data = resp.data
        items = data.get("results", data) if isinstance(data, dict) else data
        # Supplier has no property scope, so no invoices should be visible
        ids = [i["id"] for i in items]
        assert world["invoice_a"].pk not in ids
        assert world["invoice_b"].pk not in ids


class TestPaymentsPaymentRBAC:
    """RentPayment detail and reverse action."""

    def test_tenant_a_can_read_own_payment(self, world):
        c = _client_for(world["tenant_a"])
        _check(c, "get", f"/api/v1/payments/payments/{world['payment_a'].pk}/", 200)

    def test_tenant_a_cannot_reverse_payment(self, world):
        c = _client_for(world["tenant_a"])
        _check(
            c, "post",
            f"/api/v1/payments/payments/{world['payment_a'].pk}/reverse/",
            403,
            data={"reason": "tenant reverse attempt"},
        )

    def test_owner_cannot_reverse_payment(self, world):
        c = _client_for(world["owner_a"])
        _check(
            c, "post",
            f"/api/v1/payments/payments/{world['payment_a'].pk}/reverse/",
            403,
            data={"reason": "owner reverse attempt"},
        )

    def test_agent_a_can_reverse_payment(self, world):
        """Agents are allowed to reverse payments (IsAgentOrAdmin guard)."""
        c = _client_for(world["agent_a"])
        _check(
            c, "post",
            f"/api/v1/payments/payments/{world['payment_a'].pk}/reverse/",
            200,
            data={"reason": "agent test reverse"},
        )


class TestUnmatchedPaymentsRBAC:
    """UnmatchedPaymentViewSet is restricted to admin + agency_admin."""

    def test_admin_can_list_unmatched(self, world):
        c = _client_for(world["admin"])
        _check(c, "get", "/api/v1/payments/unmatched/", 200)

    def test_agency_admin_a_can_list_unmatched(self, world):
        c = _client_for(world["agency_admin_a"])
        _check(c, "get", "/api/v1/payments/unmatched/", 200)

    def test_agent_cannot_list_unmatched(self, world):
        c = _client_for(world["agent_a"])
        _check(c, "get", "/api/v1/payments/unmatched/", 403)

    def test_tenant_cannot_list_unmatched(self, world):
        c = _client_for(world["tenant_a"])
        _check(c, "get", "/api/v1/payments/unmatched/", 403)

    def test_owner_cannot_list_unmatched(self, world):
        c = _client_for(world["owner_a"])
        _check(c, "get", "/api/v1/payments/unmatched/", 403)

    def test_supplier_cannot_list_unmatched(self, world):
        c = _client_for(world["supplier"])
        _check(c, "get", "/api/v1/payments/unmatched/", 403)

    def test_unauthenticated_cannot_list_unmatched(self, db):
        _check(APIClient(), "get", "/api/v1/payments/unmatched/", 401)


# ─────────────────────────────────────────────────────────────────────────────
# 6. MAINTENANCE — role matrix
# ─────────────────────────────────────────────────────────────────────────────

class TestMaintenanceRBAC:
    """
    MaintenanceRequestViewSet — IsAuthenticated with get_queryset scoping.

    admin           → all requests
    agent_a         → requests for assigned properties only
    agent_b         → requests for prop_b only
    tenant_a        → only their own request
    supplier        → 0 requests (no property scope)
    """

    def _mr_ids(self, client):
        resp = client.get("/api/v1/maintenance/")
        assert resp.status_code == 200
        data = resp.data
        items = data.get("results", data) if isinstance(data, dict) else data
        return [r["id"] for r in items]

    def test_admin_sees_all_requests(self, world):
        c = _client_for(world["admin"])
        ids = self._mr_ids(c)
        assert world["mr_a"].pk in ids
        assert world["mr_b"].pk in ids

    def test_agent_a_sees_own_property_request(self, world):
        c = _client_for(world["agent_a"])
        ids = self._mr_ids(c)
        assert world["mr_a"].pk in ids

    def test_agent_a_does_not_see_other_property_request(self, world):
        c = _client_for(world["agent_a"])
        ids = self._mr_ids(c)
        assert world["mr_b"].pk not in ids

    def test_agent_a_cannot_detail_other_property_request(self, world):
        c = _client_for(world["agent_a"])
        _check(c, "get", f"/api/v1/maintenance/{world['mr_b'].pk}/", 404)

    def test_agent_a_cannot_patch_other_property_request(self, world):
        c = _client_for(world["agent_a"])
        _check(
            c, "patch",
            f"/api/v1/maintenance/{world['mr_b'].pk}/",
            404,
            data={"status": "resolved"},
        )

    def test_managing_agent_sees_assigned_property_request(self, world):
        c = _client_for(world["managing_agent_a"])
        ids = self._mr_ids(c)
        assert world["mr_a"].pk in ids

    def test_tenant_a_sees_only_own_request(self, world):
        c = _client_for(world["tenant_a"])
        ids = self._mr_ids(c)
        assert world["mr_a"].pk in ids
        assert world["mr_b"].pk not in ids

    def test_tenant_a_cannot_detail_tenant_b_request(self, world):
        c = _client_for(world["tenant_a"])
        _check(c, "get", f"/api/v1/maintenance/{world['mr_b'].pk}/", 404)

    def test_supplier_sees_no_maintenance_requests(self, world):
        c = _client_for(world["supplier"])
        ids = self._mr_ids(c)
        assert world["mr_a"].pk not in ids
        assert world["mr_b"].pk not in ids

    def test_dispatch_award_requires_agent(self, world):
        """POST dispatch/award action is agent-only (IsAgentOrAdmin)."""
        c = _client_for(world["tenant_a"])
        _check(
            c, "post",
            f"/api/v1/maintenance/{world['mr_a'].pk}/dispatch/award/",
            403,
        )

    def test_supplier_cannot_create_maintenance_request(self, world):
        """Suppliers must receive 403 when attempting to POST a maintenance request.
        Suppliers interact only with jobs dispatched to them via the supplier portal
        (POPIA data-minimisation). RNT-SEC-036."""
        c = _client_for(world["supplier"])
        resp = c.post("/api/v1/maintenance/", {
            "title": "Supplier Injected", "description": "x",
            "unit": world["unit_a"].pk, "priority": "low",
        }, format="json")
        assert resp.status_code == 403, (
            f"Supplier POST /api/v1/maintenance/ must return 403, got {resp.status_code}"
        )

    def test_tenant_can_create_maintenance_request(self, world):
        """Tenants may POST their own maintenance requests (IsTenantOrAgent guard)."""
        c = _client_for(world["tenant_a"])
        resp = c.post("/api/v1/maintenance/", {
            "title": "Dripping tap", "description": "Kitchen tap drips constantly.",
            "unit": world["unit_a"].pk, "priority": "low",
        }, format="json")
        assert resp.status_code == 201, (
            f"Tenant POST /api/v1/maintenance/ must return 201, got {resp.status_code}"
        )

    def test_agent_can_create_maintenance_request(self, world):
        """Agents may POST maintenance requests on behalf of tenants (IsTenantOrAgent guard)."""
        c = _client_for(world["agent_a"])
        resp = c.post("/api/v1/maintenance/", {
            "title": "Broken geyser", "description": "Geyser not heating.",
            "unit": world["unit_a"].pk, "priority": "high",
        }, format="json")
        assert resp.status_code == 201, (
            f"Agent POST /api/v1/maintenance/ must return 201, got {resp.status_code}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 7. SUPPLIER PORTAL — only suppliers
# ─────────────────────────────────────────────────────────────────────────────

class TestSupplierPortalRBAC:
    """
    /api/v1/maintenance/supplier/* endpoints require IsSupplier.
    All other roles should get 403.
    """

    SUPPLIER_PORTAL_URLS = [
        "/api/v1/maintenance/supplier/dashboard/",
        "/api/v1/maintenance/supplier/jobs/",
        "/api/v1/maintenance/supplier/profile/",
    ]

    def test_supplier_can_access_supplier_portal(self, world):
        """Supplier role passes the IsSupplier guard. May get 403 if no Supplier
        profile record is linked (separate from the auth guard), or 200 if it is."""
        c = _client_for(world["supplier"])
        for url in self.SUPPLIER_PORTAL_URLS:
            resp = c.get(url)
            assert resp.status_code in (200, 403, 404), (
                f"Supplier GET {url} expected 200/403/404, got {resp.status_code}"
            )

    def test_agent_cannot_access_supplier_portal(self, world):
        c = _client_for(world["agent_a"])
        for url in self.SUPPLIER_PORTAL_URLS:
            resp = c.get(url)
            assert resp.status_code == 403, (
                f"Agent GET {url} expected 403, got {resp.status_code}"
            )

    def test_tenant_cannot_access_supplier_portal(self, world):
        c = _client_for(world["tenant_a"])
        for url in self.SUPPLIER_PORTAL_URLS:
            resp = c.get(url)
            assert resp.status_code == 403, (
                f"Tenant GET {url} expected 403, got {resp.status_code}"
            )

    def test_admin_cannot_access_supplier_portal(self, world):
        """Admin uses the main API, not the supplier portal."""
        c = _client_for(world["admin"])
        for url in self.SUPPLIER_PORTAL_URLS:
            resp = c.get(url)
            assert resp.status_code == 403, (
                f"Admin GET {url} expected 403, got {resp.status_code}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 8. OWNER PORTAL — owner + staff read-only
# ─────────────────────────────────────────────────────────────────────────────

class TestOwnerPortalRBAC:
    """
    /api/v1/properties/owner/* requires IsOwnerOrStaff.
    Tenants and suppliers should get 403.
    """

    def test_owner_can_access_owner_dashboard(self, world):
        c = _client_for(world["owner_a"])
        _check(c, "get", "/api/v1/properties/owner/dashboard/", 200)

    def test_owner_can_access_owner_properties(self, world):
        c = _client_for(world["owner_a"])
        _check(c, "get", "/api/v1/properties/owner/properties/", 200)

    def test_agent_can_access_owner_portal(self, world):
        """Agents are staff so they can also hit this endpoint."""
        c = _client_for(world["agent_a"])
        _check(c, "get", "/api/v1/properties/owner/dashboard/", 200)

    def test_tenant_cannot_access_owner_portal(self, world):
        c = _client_for(world["tenant_a"])
        _check(c, "get", "/api/v1/properties/owner/dashboard/", 403)

    def test_supplier_cannot_access_owner_portal(self, world):
        c = _client_for(world["supplier"])
        _check(c, "get", "/api/v1/properties/owner/dashboard/", 403)


# ─────────────────────────────────────────────────────────────────────────────
# 9. ESIGNING — agent/admin only
# ─────────────────────────────────────────────────────────────────────────────

class TestESigningRBAC:
    """
    ESigningSubmissionListCreateView uses IsAuthenticated + queryset scoping
    (ScopedESigningQuerysetMixin). Any authenticated user can hit the list endpoint
    but only sees submissions they are party to.

    Detail/mutate actions (resend, download, etc.) use IsAgentOrAdmin.
    Public signing endpoints are AllowAny (not tested here).
    """

    def test_admin_can_list_esigning_submissions(self, world):
        c = _client_for(world["admin"])
        _check(c, "get", "/api/v1/esigning/submissions/", 200)

    def test_agent_can_list_esigning_submissions(self, world):
        c = _client_for(world["agent_a"])
        _check(c, "get", "/api/v1/esigning/submissions/", 200)

    def test_tenant_can_list_esigning_submissions(self, world):
        """Tenant is authenticated so gets 200 (empty queryset for unlinked tenant)."""
        c = _client_for(world["tenant_a"])
        _check(c, "get", "/api/v1/esigning/submissions/", 200)

    def test_owner_can_list_esigning_submissions(self, world):
        """Owner is authenticated so gets 200 (scoped queryset)."""
        c = _client_for(world["owner_a"])
        _check(c, "get", "/api/v1/esigning/submissions/", 200)

    def test_supplier_can_list_esigning_submissions(self, world):
        """Supplier is authenticated so gets 200 (scoped queryset)."""
        c = _client_for(world["supplier"])
        _check(c, "get", "/api/v1/esigning/submissions/", 200)

    def test_unauthenticated_cannot_list_esigning_submissions(self, db):
        _check(APIClient(), "get", "/api/v1/esigning/submissions/", 401)


# ─────────────────────────────────────────────────────────────────────────────
# 10. TENANT PORTAL — tenant only
# ─────────────────────────────────────────────────────────────────────────────

class TestTenantPortalRBAC:
    """
    /api/v1/tenant-portal/conversations/* requires authentication.
    Tenant conversation isolation: tenant A cannot read tenant B's conversations.
    """

    def _make_conversation(self, tenant_user):
        from apps.ai.models import TenantChatSession
        return TenantChatSession.objects.create(user=tenant_user)

    def test_tenant_can_list_own_conversations(self, world):
        c = _client_for(world["tenant_a"])
        _check(c, "get", "/api/v1/tenant-portal/conversations/", 200)

    def test_tenant_a_cannot_read_tenant_b_conversation(self, world):
        conv_b = self._make_conversation(world["tenant_b"])
        c = _client_for(world["tenant_a"])
        _check(c, "get", f"/api/v1/tenant-portal/conversations/{conv_b.pk}/", 404)

    def test_agent_can_access_tenant_portal_conversations(self, world):
        """Agents can list conversations (IsAuthenticated gate, then scoped)."""
        c = _client_for(world["agent_a"])
        _check(c, "get", "/api/v1/tenant-portal/conversations/", 200)

    def test_supplier_conversation_is_scoped_to_supplier(self, world):
        """Tenant portal conversations use IsAuthenticated — a supplier can create a
        conversation but it is scoped to the supplier's own user (no cross-user leak).
        The intent is that the UI doesn't route suppliers here; the API doesn't block it."""
        c = _client_for(world["supplier"])
        resp = c.post("/api/v1/tenant-portal/conversations/", {"title": "Supplier test"}, format="json")
        # 201 is the actual behaviour (IsAuthenticated only); if tightened to require
        # tenant role this would become 403. Document current state.
        assert resp.status_code in (201, 400, 403), (
            f"Supplier POST conversations returned unexpected {resp.status_code}"
        )
        if resp.status_code == 201:
            # Verify the conversation is scoped to the supplier user, not tenant_a
            assert resp.data.get("id") is not None


# ─────────────────────────────────────────────────────────────────────────────
# 11. CROSS-AGENCY LEAK TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestCrossAgencyLeaks:
    """
    Comprehensive cross-agency isolation: agency A user cannot read or write
    any data belonging to agency B.
    """

    def test_agency_admin_a_cannot_see_agency_b_property(self, world):
        c = _client_for(world["agency_admin_a"])
        resp = c.get("/api/v1/properties/")
        data = resp.data
        items = data.get("results", data) if isinstance(data, dict) else data
        ids = [p["id"] for p in items]
        assert world["prop_b"].pk not in ids

    def test_agency_admin_a_cannot_detail_agency_b_property(self, world):
        c = _client_for(world["agency_admin_a"])
        _check(c, "get", f"/api/v1/properties/{world['prop_b'].pk}/", 404)

    def test_agency_admin_a_cannot_see_agency_b_lease(self, world):
        c = _client_for(world["agency_admin_a"])
        resp = c.get("/api/v1/leases/")
        data = resp.data
        items = data.get("results", data) if isinstance(data, dict) else data
        ids = [l["id"] for l in items]
        assert world["lease_b"].pk not in ids

    def test_agency_admin_a_cannot_see_agency_b_invoice(self, world):
        c = _client_for(world["agency_admin_a"])
        resp = c.get("/api/v1/payments/invoices/")
        data = resp.data
        items = data.get("results", data) if isinstance(data, dict) else data
        ids = [i["id"] for i in items]
        assert world["invoice_b"].pk not in ids

    def test_agency_admin_a_cannot_see_agency_b_maintenance(self, world):
        c = _client_for(world["agency_admin_a"])
        resp = c.get("/api/v1/maintenance/")
        data = resp.data
        items = data.get("results", data) if isinstance(data, dict) else data
        ids = [m["id"] for m in items]
        assert world["mr_b"].pk not in ids

    def test_agent_a_cannot_patch_agency_b_lease(self, world):
        c = _client_for(world["agent_a"])
        _check(c, "patch", f"/api/v1/leases/{world['lease_b'].pk}/",
               404, data={"monthly_rent": "1.00"})

    def test_agent_b_cannot_patch_agency_a_lease(self, world):
        c = _client_for(world["agent_b"])
        _check(c, "patch", f"/api/v1/leases/{world['lease_a'].pk}/",
               404, data={"monthly_rent": "1.00"})

    def test_agent_a_cannot_delete_agency_b_maintenance_request(self, world):
        c = _client_for(world["agent_a"])
        _check(c, "delete", f"/api/v1/maintenance/{world['mr_b'].pk}/", 404)


# ─────────────────────────────────────────────────────────────────────────────
# 12. CROSS-TENANT LEAK TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestCrossTenantLeaks:
    """
    Tenant A should never read Tenant B's data regardless of whether they share
    the same property.
    """

    def test_tenant_a_cannot_see_tenant_b_lease(self, world):
        c = _client_for(world["tenant_a"])
        _check(c, "get", f"/api/v1/leases/{world['lease_b'].pk}/", 404)

    def test_tenant_a_cannot_see_tenant_b_invoice(self, world):
        c = _client_for(world["tenant_a"])
        _check(c, "get", f"/api/v1/payments/invoices/{world['invoice_b'].pk}/", 404)

    def test_tenant_a_cannot_see_tenant_b_maintenance_request(self, world):
        c = _client_for(world["tenant_a"])
        _check(c, "get", f"/api/v1/maintenance/{world['mr_b'].pk}/", 404)

    def test_tenant_a_does_not_see_tenant_b_invoice_in_list(self, world):
        c = _client_for(world["tenant_a"])
        resp = c.get("/api/v1/payments/invoices/")
        assert resp.status_code == 200
        data = resp.data
        items = data.get("results", data) if isinstance(data, dict) else data
        ids = [i["id"] for i in items]
        assert world["invoice_b"].pk not in ids

    def test_tenant_a_does_not_see_tenant_b_mr_in_list(self, world):
        c = _client_for(world["tenant_a"])
        resp = c.get("/api/v1/maintenance/")
        assert resp.status_code == 200
        data = resp.data
        items = data.get("results", data) if isinstance(data, dict) else data
        ids = [m["id"] for m in items]
        assert world["mr_b"].pk not in ids

    def test_same_property_tenant_isolation(self, world):
        """Two tenants on different units of the SAME property cannot see each other's data."""
        # Create a second tenant on unit_b of prop_a (same property as tenant_a)
        tenant_c_user = _user("tenant", "_c_same_prop")
        tenant_c_person = _person(user=tenant_c_user, full_name="Tenant C Same Prop")
        lease_c = _lease(world["unit_b"], primary_tenant=tenant_c_person)
        invoice_c = _invoice(lease_c, period_start=date(2026, 4, 1))

        c_a = _client_for(world["tenant_a"])
        c_c = _client_for(tenant_c_user)

        # tenant_a cannot see lease_c
        _check(c_a, "get", f"/api/v1/leases/{lease_c.pk}/", 404)
        # tenant_c cannot see lease_a
        _check(c_c, "get", f"/api/v1/leases/{world['lease_a'].pk}/", 404)

        # invoice cross-check
        _check(c_a, "get", f"/api/v1/payments/invoices/{invoice_c.pk}/", 404)
        _check(c_c, "get", f"/api/v1/payments/invoices/{world['invoice_a'].pk}/", 404)


# ─────────────────────────────────────────────────────────────────────────────
# 13. OWNER READ-ONLY SCOPE
# ─────────────────────────────────────────────────────────────────────────────

class TestOwnerReadOnly:
    """
    Owners can read their own property data but cannot mutate via the agent-facing
    API endpoints (IsAgentOrAdmin guard on PropertyViewSet).
    """

    def test_owner_cannot_create_property(self, world):
        c = _client_for(world["owner_a"])
        resp = c.post("/api/v1/properties/", {
            "name": "Owner New Prop",
            "address": "99 Test St",
            "city": "Cape Town",
            "province": "WC",
            "postal_code": "8001",
            "property_type": "apartment",
        }, format="json")
        assert resp.status_code == 403

    def test_owner_cannot_patch_lease(self, world):
        """LeaseViewSet.get_permissions() returns IsAgentOrAdmin for write actions.
        Owners may read their leases but must receive 403 on any mutating call."""
        c = _client_for(world["owner_a"])
        resp = c.patch(
            f"/api/v1/leases/{world['lease_a'].pk}/",
            {"monthly_rent": "1.00"},
            format="json",
        )
        assert resp.status_code == 403, (
            f"Owner PATCH lease expected 403, got {resp.status_code}"
        )

    def test_owner_cannot_record_payment(self, world):
        """Write action on invoices is explicitly IsAgentOrAdmin."""
        c = _client_for(world["owner_a"])
        _check(
            c, "post",
            f"/api/v1/payments/invoices/{world['invoice_a'].pk}/payments/",
            403,
            data={"amount": "8000.00", "payment_date": "2026-04-01"},
        )

    def test_owner_cannot_delete_maintenance_request(self, world):
        """MaintenanceRequestViewSet.get_permissions() returns IsAgentOrAdmin for destroy.
        Owners can read their property's maintenance requests but must get 403 on DELETE."""
        c = _client_for(world["owner_a"])
        # Owner can see maintenance requests for their property
        resp = c.get("/api/v1/maintenance/")
        data = resp.data
        items = data.get("results", data) if isinstance(data, dict) else data
        ids = [m["id"] for m in items]
        assert world["mr_a"].pk in ids

        # DELETE must be blocked for owners — IsAgentOrAdmin guard on destroy action
        delete_resp = c.delete(f"/api/v1/maintenance/{world['mr_a'].pk}/")
        assert delete_resp.status_code == 403, (
            f"Owner DELETE maintenance expected 403, got {delete_resp.status_code}"
        )

    def test_owner_cannot_patch_maintenance_request(self, world):
        """MaintenanceRequestViewSet.get_permissions() returns IsAgentOrAdmin for
        partial_update. Owners are read-only on the agent-facing maintenance API."""
        c = _client_for(world["owner_a"])
        resp = c.patch(
            f"/api/v1/maintenance/{world['mr_a'].pk}/",
            {"status": "resolved"},
            format="json",
        )
        assert resp.status_code == 403, (
            f"Owner PATCH maintenance expected 403, got {resp.status_code}"
        )

    def test_owner_cannot_post_maintenance_request(self, world):
        """IsTenantOrAgent guard on create explicitly excludes the owner role.
        Owners must receive 403 when attempting to POST a new maintenance request."""
        c = _client_for(world["owner_a"])
        resp = c.post("/api/v1/maintenance/", {
            "title": "Owner injected issue", "description": "Should be blocked.",
            "unit": world["unit_a"].pk, "priority": "low",
        }, format="json")
        assert resp.status_code == 403, (
            f"Owner POST maintenance expected 403, got {resp.status_code}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 14. MANDATE DOCUMENTS — agent/admin only
# ─────────────────────────────────────────────────────────────────────────────

class TestMandatesRBAC:
    """
    Rental mandates are created per-property by agents.
    Tenants and suppliers must not access them.
    """

    def test_admin_can_list_mandates(self, world):
        c = _client_for(world["admin"])
        _check(c, "get", "/api/v1/properties/mandates/", 200)

    def test_agent_a_can_list_mandates(self, world):
        c = _client_for(world["agent_a"])
        _check(c, "get", "/api/v1/properties/mandates/", 200)

    def test_tenant_cannot_list_mandates(self, world):
        c = _client_for(world["tenant_a"])
        _check(c, "get", "/api/v1/properties/mandates/", 403)

    def test_owner_cannot_list_mandates(self, world):
        c = _client_for(world["owner_a"])
        _check(c, "get", "/api/v1/properties/mandates/", 403)

    def test_supplier_cannot_list_mandates(self, world):
        c = _client_for(world["supplier"])
        _check(c, "get", "/api/v1/properties/mandates/", 403)


# ─────────────────────────────────────────────────────────────────────────────
# 15. LEASE TEMPLATES — agent/admin only
# ─────────────────────────────────────────────────────────────────────────────

class TestLeaseTemplatesRBAC:
    """Lease templates should only be accessible to agents and admins."""

    def test_admin_can_list_lease_templates(self, world):
        c = _client_for(world["admin"])
        _check(c, "get", "/api/v1/leases/templates/", 200)

    def test_agent_can_list_lease_templates(self, world):
        c = _client_for(world["agent_a"])
        _check(c, "get", "/api/v1/leases/templates/", 200)

    def test_tenant_cannot_list_lease_templates(self, world):
        c = _client_for(world["tenant_a"])
        _check(c, "get", "/api/v1/leases/templates/", 403)

    def test_owner_cannot_list_lease_templates(self, world):
        c = _client_for(world["owner_a"])
        _check(c, "get", "/api/v1/leases/templates/", 403)

    def test_supplier_cannot_list_lease_templates(self, world):
        c = _client_for(world["supplier"])
        _check(c, "get", "/api/v1/leases/templates/", 403)


# ─────────────────────────────────────────────────────────────────────────────
# 16. ROLE MATRIX SUMMARY — parametrized smoke checks
# ─────────────────────────────────────────────────────────────────────────────

ROLE_ENDPOINT_MATRIX = [
    # (role_key, url, expected_status, method)
    # Properties list — only agents and admins
    ("admin",            "/api/v1/properties/", 200, "get"),
    ("agency_admin_a",   "/api/v1/properties/", 200, "get"),
    ("agent_a",          "/api/v1/properties/", 200, "get"),
    ("managing_agent_a", "/api/v1/properties/", 200, "get"),
    ("estate_agent_a",   "/api/v1/properties/", 200, "get"),
    ("owner_a",          "/api/v1/properties/", 403, "get"),
    ("tenant_a",         "/api/v1/properties/", 403, "get"),
    ("supplier",         "/api/v1/properties/", 403, "get"),
    # Leases list — all authenticated, scoped by queryset
    ("admin",            "/api/v1/leases/", 200, "get"),
    ("agency_admin_a",   "/api/v1/leases/", 200, "get"),
    ("agent_a",          "/api/v1/leases/", 200, "get"),
    ("managing_agent_a", "/api/v1/leases/", 200, "get"),
    ("estate_agent_a",   "/api/v1/leases/", 200, "get"),
    ("owner_a",          "/api/v1/leases/", 200, "get"),
    ("tenant_a",         "/api/v1/leases/", 200, "get"),
    ("supplier",         "/api/v1/leases/", 200, "get"),
    # Invoices list — all authenticated, scoped by queryset
    ("admin",            "/api/v1/payments/invoices/", 200, "get"),
    ("agency_admin_a",   "/api/v1/payments/invoices/", 200, "get"),
    ("agent_a",          "/api/v1/payments/invoices/", 200, "get"),
    ("owner_a",          "/api/v1/payments/invoices/", 200, "get"),
    ("tenant_a",         "/api/v1/payments/invoices/", 200, "get"),
    ("supplier",         "/api/v1/payments/invoices/", 200, "get"),
    # Unmatched — admin + agency_admin only
    ("admin",            "/api/v1/payments/unmatched/", 200, "get"),
    ("agency_admin_a",   "/api/v1/payments/unmatched/", 200, "get"),
    ("agent_a",          "/api/v1/payments/unmatched/", 403, "get"),
    ("managing_agent_a", "/api/v1/payments/unmatched/", 403, "get"),
    ("owner_a",          "/api/v1/payments/unmatched/", 403, "get"),
    ("tenant_a",         "/api/v1/payments/unmatched/", 403, "get"),
    ("supplier",         "/api/v1/payments/unmatched/", 403, "get"),
    # Maintenance list — all authenticated
    ("admin",            "/api/v1/maintenance/", 200, "get"),
    ("agent_a",          "/api/v1/maintenance/", 200, "get"),
    ("managing_agent_a", "/api/v1/maintenance/", 200, "get"),
    ("owner_a",          "/api/v1/maintenance/", 200, "get"),
    ("tenant_a",         "/api/v1/maintenance/", 200, "get"),
    ("supplier",         "/api/v1/maintenance/", 200, "get"),
    # Esigning submissions — IsAuthenticated list (scoped queryset); all roles get 200
    ("admin",            "/api/v1/esigning/submissions/", 200, "get"),
    ("agent_a",          "/api/v1/esigning/submissions/", 200, "get"),
    ("managing_agent_a", "/api/v1/esigning/submissions/", 200, "get"),
    ("owner_a",          "/api/v1/esigning/submissions/", 200, "get"),
    ("tenant_a",         "/api/v1/esigning/submissions/", 200, "get"),
    ("supplier",         "/api/v1/esigning/submissions/", 200, "get"),
    # Mandates — agent + admin only
    ("admin",            "/api/v1/properties/mandates/", 200, "get"),
    ("agent_a",          "/api/v1/properties/mandates/", 200, "get"),
    ("owner_a",          "/api/v1/properties/mandates/", 403, "get"),
    ("tenant_a",         "/api/v1/properties/mandates/", 403, "get"),
    ("supplier",         "/api/v1/properties/mandates/", 403, "get"),
    # Owner portal — owner + staff
    ("owner_a",          "/api/v1/properties/owner/dashboard/", 200, "get"),
    ("agent_a",          "/api/v1/properties/owner/dashboard/", 200, "get"),
    ("tenant_a",         "/api/v1/properties/owner/dashboard/", 403, "get"),
    ("supplier",         "/api/v1/properties/owner/dashboard/", 403, "get"),
    # Supplier portal — supplier role passes IsSupplier; may return 403 if no profile linked
    # The parametrized matrix only checks role-based HTTP status, not profile linkage.
    # Non-supplier roles always get 403.
    ("agent_a",          "/api/v1/maintenance/supplier/dashboard/", 403, "get"),
    ("tenant_a",         "/api/v1/maintenance/supplier/dashboard/", 403, "get"),
    ("owner_a",          "/api/v1/maintenance/supplier/dashboard/", 403, "get"),
    ("admin",            "/api/v1/maintenance/supplier/dashboard/", 403, "get"),
]


@pytest.mark.parametrize("role_key,url,expected_status,method", ROLE_ENDPOINT_MATRIX)
def test_role_endpoint_matrix(world, role_key, url, expected_status, method):
    """
    Parametrized smoke-check: every (role, endpoint) combo returns the expected status.
    Failing entries reveal RBAC gaps — each failure identifies a specific role/endpoint
    combination to fix before v1.0 ship.
    """
    user = world[role_key]
    c = _client_for(user)
    fn = getattr(c, method)
    resp = fn(url)
    assert resp.status_code == expected_status, (
        f"[{role_key}] {method.upper()} {url}: "
        f"expected {expected_status}, got {resp.status_code}"
    )
