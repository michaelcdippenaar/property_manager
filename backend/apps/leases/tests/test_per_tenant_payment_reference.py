"""
Tests for per-lessee payment_reference (Lease.payment_reference for primary,
LeaseTenant.payment_reference for co-tenants), and the merge fields:
  - primary_tenant_payment_reference (alias of legacy payment_reference)
  - cotenant_1_payment_reference / cotenant_2_payment_reference / cotenant_3_payment_reference
  - payment_reference (legacy alias) still works
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock


def _make_mock_co(payment_reference: str, person_name: str, ct_id: int) -> MagicMock:
    p = MagicMock()
    p.full_name = person_name
    p.id_number = ""
    p.phone = ""
    p.email = ""
    p.address = ""
    p.employer = ""
    p.occupation = ""
    p.date_of_birth = None
    p.emergency_contact_name = ""
    p.emergency_contact_phone = ""

    ct = MagicMock()
    ct.id = ct_id
    ct.person = p
    ct.payment_reference = payment_reference
    return ct


def _make_orm_lease(co_tenants: list, primary_payment_ref: str = "PRIMARY-REF"):
    prop = MagicMock()
    prop.name = "Sunset"
    prop.address = "12 Sunset Drive"
    prop.city = "Stellenbosch"
    prop.province = "Western Cape"
    prop.description = ""
    ownership_qs = MagicMock()
    ownership_qs.filter.return_value.select_related.return_value.first.return_value = None
    prop.ownerships = ownership_qs

    unit = MagicMock()
    unit.unit_number = "5B"
    unit.property = prop

    tenant = MagicMock()
    tenant.full_name = "Jane Smith"
    tenant.id_number = ""
    tenant.phone = ""
    tenant.email = ""
    tenant.address = ""
    tenant.employer = ""
    tenant.occupation = ""
    tenant.date_of_birth = None
    tenant.emergency_contact_name = ""
    tenant.emergency_contact_phone = ""

    co_qs = MagicMock()
    co_qs.select_related.return_value.all.return_value = co_tenants

    occ_qs = MagicMock()
    occ_qs.select_related.return_value.all.return_value = []

    lease = MagicMock()
    lease.pk = 1
    lease.unit = unit
    lease.primary_tenant = tenant
    lease.monthly_rent = Decimal("9500.00")
    lease.deposit = Decimal("19000.00")
    lease.start_date = date(2026, 3, 1)
    lease.end_date = date(2027, 2, 28)
    lease.notice_period_days = 30
    lease.water_included = True
    lease.electricity_prepaid = False
    lease.max_occupants = 2
    lease.payment_reference = primary_payment_ref
    lease.lease_number = "L-1"
    lease.co_tenants = co_qs
    lease.occupants = occ_qs
    return lease


class TestPerTenantPaymentReference:
    def test_primary_tenant_payment_reference_resolves_from_lease(self):
        from apps.esigning.services import build_lease_context
        lease = _make_orm_lease(co_tenants=[], primary_payment_ref="UNIT5B-SMITH")
        ctx = build_lease_context(lease)
        assert ctx["primary_tenant_payment_reference"] == "UNIT5B-SMITH"

    def test_legacy_payment_reference_still_populated(self):
        from apps.esigning.services import build_lease_context
        lease = _make_orm_lease(co_tenants=[], primary_payment_ref="UNIT5B-SMITH")
        ctx = build_lease_context(lease)
        assert ctx["payment_reference"] == "UNIT5B-SMITH"

    def test_cotenant_1_payment_reference_resolves_from_first_co_tenant(self):
        from apps.esigning.services import build_lease_context
        co1 = _make_mock_co("CO1-REF", "Alex Co", ct_id=10)
        co2 = _make_mock_co("CO2-REF", "Beth Co", ct_id=20)
        lease = _make_orm_lease(co_tenants=[co1, co2])
        ctx = build_lease_context(lease)
        assert ctx["cotenant_1_payment_reference"] == "CO1-REF"
        assert ctx["cotenant_2_payment_reference"] == "CO2-REF"
        assert ctx["cotenant_3_payment_reference"] == "—"

    def test_cotenant_payment_reference_empty_when_no_co_tenants(self):
        from apps.esigning.services import build_lease_context
        lease = _make_orm_lease(co_tenants=[])
        ctx = build_lease_context(lease)
        # No co-tenants — all 3 slots fall back to em-dash placeholder
        assert ctx["cotenant_1_payment_reference"] == "—"
        assert ctx["cotenant_2_payment_reference"] == "—"
        assert ctx["cotenant_3_payment_reference"] == "—"

    def test_cotenants_ordered_by_id_for_stability(self):
        from apps.esigning.services import build_lease_context
        # Insert in reverse order — sort by id should still place co1 first
        co1 = _make_mock_co("LOW-ID-REF", "Alex Co", ct_id=5)
        co2 = _make_mock_co("HIGH-ID-REF", "Beth Co", ct_id=99)
        lease = _make_orm_lease(co_tenants=[co2, co1])
        ctx = build_lease_context(lease)
        assert ctx["cotenant_1_payment_reference"] == "LOW-ID-REF"
        assert ctx["cotenant_2_payment_reference"] == "HIGH-ID-REF"


class TestMergeFieldRegistry:
    def test_new_fields_in_canonical_registry(self):
        from apps.leases.merge_fields import CANONICAL_FIELD_NAMES
        assert "primary_tenant_payment_reference" in CANONICAL_FIELD_NAMES
        assert "cotenant_1_payment_reference" in CANONICAL_FIELD_NAMES
        assert "cotenant_2_payment_reference" in CANONICAL_FIELD_NAMES
        assert "cotenant_3_payment_reference" in CANONICAL_FIELD_NAMES
        # Legacy alias retained
        assert "payment_reference" in CANONICAL_FIELD_NAMES


# ---------------------------------------------------------------------------
# Post-review regression — Bug 6: tenant_N_name and cotenant_N_payment_reference
# must use the SAME ordering (id ascending) so the right reference is rendered
# next to the right tenant.
# ---------------------------------------------------------------------------

class TestNameAndPaymentReferenceAlignment:
    def test_tenant_n_name_and_cotenant_n_reference_align_after_reordering(self):
        from apps.esigning.services import build_lease_context

        # Insert co-tenants in reverse-id order in the iterable returned by
        # the queryset mock — services must still align name(slot N) with
        # payment_reference(slot N) by sorting on id.
        co_low = _make_mock_co("REF-LOW", "Alex Lowid", ct_id=2)
        co_high = _make_mock_co("REF-HIGH", "Beth Highid", ct_id=200)
        lease = _make_orm_lease(co_tenants=[co_high, co_low])

        ctx = build_lease_context(lease)
        # Slot 2 should be the lower-id co-tenant; slot 3 the higher-id.
        assert ctx["tenant_2_name"] == "Alex Lowid"
        assert ctx["tenant_3_name"] == "Beth Highid"
        assert ctx["cotenant_1_payment_reference"] == "REF-LOW"
        assert ctx["cotenant_2_payment_reference"] == "REF-HIGH"
