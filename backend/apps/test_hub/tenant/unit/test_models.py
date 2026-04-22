"""
Unit tests for apps.tenant models (Tenant, TenantUnitAssignment).

Run without DB where possible.
"""
import pytest
from datetime import date
from unittest.mock import MagicMock, patch
from django.db.models.base import ModelState

pytestmark = [pytest.mark.unit, pytest.mark.green]


class TestTenantStr:
    def test_str_format(self):
        """Tenant.__str__ produces 'Tenant: <full_name>'."""
        from apps.tenant.models import Tenant
        # Call the __str__ method logic directly (avoids DB/descriptor issues)
        person = MagicMock()
        person.full_name = "Alice Renter"
        obj = MagicMock(spec=Tenant)
        obj.person = person
        # Use the actual __str__ implementation
        result = Tenant.__str__(obj)
        assert "Alice Renter" in result


class TestTenantAssignUnitValidation:
    def test_end_date_before_start_date_raises_value_error(self):
        from apps.tenant.models import Tenant
        obj = Tenant.__new__(Tenant)
        obj._state = ModelState()
        obj.pk = 1

        unit = MagicMock()
        with pytest.raises(ValueError, match="end_date"):
            # Patch the DB query to return empty (no overlap), but this raises before it
            obj.assign_unit(
                unit=unit,
                start_date=date(2026, 5, 1),
                end_date=date(2026, 4, 1),
            )


class TestTenantAssignFromLeaseValidation:
    def test_raise_when_lease_has_no_unit(self):
        from apps.tenant.models import Tenant
        obj = Tenant.__new__(Tenant)
        obj._state = ModelState()

        lease = MagicMock()
        lease.pk = 99
        lease.unit = None

        with pytest.raises(ValueError, match="no unit"):
            obj.assign_from_lease(lease)

    def test_raise_when_lease_primary_tenant_mismatch(self):
        from apps.tenant.models import Tenant
        obj = Tenant.__new__(Tenant)
        obj._state = ModelState()
        obj.person_id = 10

        lease = MagicMock()
        lease.pk = 99
        lease.unit = MagicMock()
        lease.primary_tenant_id = 999  # different from person_id=10

        with pytest.raises(ValueError, match="does not match"):
            obj.assign_from_lease(lease)


class TestTenantUnitAssignmentStr:
    def test_str_open_ended(self):
        """TenantUnitAssignment.__str__ shows 'present' when end_date is None."""
        from apps.tenant.models import TenantUnitAssignment
        tenant = MagicMock()
        tenant.__str__ = MagicMock(return_value="Tenant: Alice Renter")
        unit = MagicMock()
        unit.__str__ = MagicMock(return_value="Unit 4A")
        obj = MagicMock(spec=TenantUnitAssignment)
        obj.tenant = tenant
        obj.unit = unit
        obj.start_date = date(2026, 1, 1)
        obj.end_date = None
        result = TenantUnitAssignment.__str__(obj)
        assert "present" in result

    def test_str_with_end_date(self):
        """TenantUnitAssignment.__str__ shows end_date when set."""
        from apps.tenant.models import TenantUnitAssignment
        tenant = MagicMock()
        unit = MagicMock()
        obj = MagicMock(spec=TenantUnitAssignment)
        obj.tenant = tenant
        obj.unit = unit
        obj.start_date = date(2026, 1, 1)
        obj.end_date = date(2026, 12, 31)
        result = TenantUnitAssignment.__str__(obj)
        assert "2026-12-31" in result


class TestTenantSourceChoices:
    def test_manual_and_lease_sources_exist(self):
        from apps.tenant.models import TenantUnitAssignment
        values = [c[0] for c in TenantUnitAssignment.Source.choices]
        assert "manual" in values
        assert "lease" in values
