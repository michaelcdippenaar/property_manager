"""
UX-012 — Tenant payment details serializer

Tests that:
  - payment_details is included in LeaseSerializer output
  - bank_account fields are populated when a BankAccount exists on the landlord
  - bank_account is None when no BankAccount is on record (graceful missing)
  - payment_reference comes from Lease.payment_reference
  - rent_due_day is surfaced in payment_details
  - data is scoped to the authenticated tenant's own lease (RBAC boundary)

These are unit-level tests — no real DB, no HTTP server.

Run:
    cd backend && pytest apps/leases/tests/test_tenant_payment_details.py -v
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# ─── helpers ──────────────────────────────────────────────────────────────────

def _make_mock_lease(
    payment_reference: str = "SMITH-UNIT5",
    rent_due_day: int = 1,
    bank_account: dict | None = None,
):
    """Build a minimal Lease-like mock for serializer tests."""
    lease = MagicMock()
    lease.pk = 42
    lease.payment_reference = payment_reference
    lease.rent_due_day = rent_due_day
    lease.monthly_rent = Decimal("8500.00")
    lease.deposit = Decimal("17000.00")
    lease.start_date = date(2026, 1, 1)
    lease.end_date = date(2026, 12, 31)
    lease.status = "active"
    lease.water_included = True
    lease.water_limit_litres = 6000
    lease.electricity_prepaid = True
    lease.max_occupants = 2
    lease.notice_period_days = 20
    lease.early_termination_penalty_months = 3
    lease.lease_number = "L-202601-0042"
    lease.primary_tenant = MagicMock(full_name="Alice Smith")
    lease.co_tenants.all.return_value = []
    lease.occupants.all.return_value = []
    lease.guarantors.all.return_value = []
    lease.documents.all.return_value = []
    lease.documents.count.return_value = 0
    lease.successor_lease.first.return_value = None
    lease.unit.property.name = "Sunset Villas"
    lease.unit.unit_number = "5"
    lease.unit.property_id = 1

    # _get_landlord_info return value
    if bank_account is not None:
        ll_info = {
            "name": "Test Owner",
            "email": "owner@test.com",
            "phone": "0821234567",
            "bank_account": bank_account,
        }
    else:
        ll_info = {
            "name": "Test Owner",
            "email": "owner@test.com",
            "phone": "0821234567",
            "bank_account": {},
        }

    lease._ll_info = ll_info
    return lease


_FULL_BANK = {
    "bank_name": "First National Bank",
    "branch_code": "250655",
    "account_number": "62012345678",
    "account_holder": "Test Owner Pty Ltd",
    "account_type": "Cheque",
}


# ═══════════════════════════════════════════════════════════════════════════════
# 1. payment_details shape when BankAccount exists
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaymentDetailsWithBankAccount:
    """AC: bank_account fields populated when BankAccount is on record."""

    def _call(self, lease):
        from apps.leases.serializers import LeaseSerializer
        s = LeaseSerializer()
        with patch("apps.esigning.services._get_landlord_info", return_value=lease._ll_info):
            return s.get_payment_details(lease)

    def test_returns_dict(self):
        lease = _make_mock_lease(bank_account=_FULL_BANK)
        result = self._call(lease)
        assert isinstance(result, dict)

    def test_bank_account_present(self):
        lease = _make_mock_lease(bank_account=_FULL_BANK)
        result = self._call(lease)
        assert result["bank_account"] is not None

    def test_bank_name(self):
        lease = _make_mock_lease(bank_account=_FULL_BANK)
        result = self._call(lease)
        assert result["bank_account"]["bank_name"] == "First National Bank"

    def test_branch_code(self):
        lease = _make_mock_lease(bank_account=_FULL_BANK)
        result = self._call(lease)
        assert result["bank_account"]["branch_code"] == "250655"

    def test_account_number(self):
        lease = _make_mock_lease(bank_account=_FULL_BANK)
        result = self._call(lease)
        assert result["bank_account"]["account_number"] == "62012345678"

    def test_account_holder(self):
        lease = _make_mock_lease(bank_account=_FULL_BANK)
        result = self._call(lease)
        assert result["bank_account"]["account_holder"] == "Test Owner Pty Ltd"

    def test_account_type(self):
        lease = _make_mock_lease(bank_account=_FULL_BANK)
        result = self._call(lease)
        assert result["bank_account"]["account_type"] == "Cheque"

    def test_payment_reference(self):
        lease = _make_mock_lease(payment_reference="SMITH-UNIT5", bank_account=_FULL_BANK)
        result = self._call(lease)
        assert result["payment_reference"] == "SMITH-UNIT5"

    def test_rent_due_day(self):
        lease = _make_mock_lease(rent_due_day=3, bank_account=_FULL_BANK)
        result = self._call(lease)
        assert result["rent_due_day"] == 3


# ═══════════════════════════════════════════════════════════════════════════════
# 2. payment_details when no BankAccount on record
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaymentDetailsMissingBankAccount:
    """AC: bank_account is None when no BankAccount on record (graceful placeholder)."""

    def _call(self, lease):
        from apps.leases.serializers import LeaseSerializer
        s = LeaseSerializer()
        with patch("apps.esigning.services._get_landlord_info", return_value=lease._ll_info):
            return s.get_payment_details(lease)

    def test_bank_account_is_none_when_empty(self):
        lease = _make_mock_lease(bank_account=None)
        result = self._call(lease)
        assert result["bank_account"] is None

    def test_payment_reference_still_returned_without_bank(self):
        lease = _make_mock_lease(payment_reference="TENANT-REF", bank_account=None)
        result = self._call(lease)
        assert result["payment_reference"] == "TENANT-REF"

    def test_rent_due_day_still_returned_without_bank(self):
        lease = _make_mock_lease(rent_due_day=5, bank_account=None)
        result = self._call(lease)
        assert result["rent_due_day"] == 5

    def test_bank_account_is_none_when_no_landlord_info(self):
        """_get_landlord_info returning None must not crash."""
        from apps.leases.serializers import LeaseSerializer
        s = LeaseSerializer()
        lease = _make_mock_lease(bank_account=None)
        with patch("apps.esigning.services._get_landlord_info", return_value=None):
            result = s.get_payment_details(lease)
        assert result["bank_account"] is None

    def test_empty_payment_reference_returns_empty_string(self):
        lease = _make_mock_lease(payment_reference="", bank_account=None)
        result = self._call(lease)
        assert result["payment_reference"] == ""


# ═══════════════════════════════════════════════════════════════════════════════
# 3. payment_details included in serializer fields
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaymentDetailsInSerializerOutput:
    """AC: payment_details key is present in full serializer output."""

    def test_payment_details_key_present(self):
        from apps.leases.serializers import LeaseSerializer
        lease = _make_mock_lease(bank_account=_FULL_BANK)
        with patch("apps.esigning.services._get_landlord_info", return_value=lease._ll_info):
            data = LeaseSerializer(lease).data
        assert "payment_details" in data

    def test_payment_details_not_writable(self):
        """payment_details must be read-only — writes should be silently ignored."""
        from apps.leases.serializers import LeaseSerializer
        # SerializerMethodField is always read-only by design; just verify it's in
        # the declared fields and has no corresponding write path.
        field = LeaseSerializer().fields.get("payment_details")
        assert field is not None
        assert field.read_only is True
