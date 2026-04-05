"""Unit tests for apps/ai/tenant_context.py — build_tenant_context."""
import pytest
from unittest.mock import patch, MagicMock


pytestmark = pytest.mark.unit


def _make_mock_user(email="tenant@test.com", first_name="Jane", last_name="Doe"):
    user = MagicMock()
    user.email = email
    user.first_name = first_name
    user.last_name = last_name
    return user


def _make_mock_lease(
    start="2026-01-01",
    end="2027-01-01",
    monthly_rent=5000,
    deposit=10000,
    notice_days=20,
    tenant_name="Jane Doe",
    unit_number="3A",
    property_name="Sunset Gardens",
    property_type="apartment",
    water_included=True,
    water_limit=4000,
    electricity_prepaid=True,
    max_occupants=2,
    penalty_months=3,
):
    lease = MagicMock()
    lease.start_date = start
    lease.end_date = end
    lease.monthly_rent = monthly_rent
    lease.deposit = deposit
    lease.notice_period_days = notice_days
    lease.max_occupants = max_occupants
    lease.early_termination_penalty_months = penalty_months
    lease.water_included = water_included
    lease.water_limit_litres = water_limit
    lease.electricity_prepaid = electricity_prepaid

    tenant = MagicMock()
    tenant.full_name = tenant_name
    lease.primary_tenant = tenant

    unit = MagicMock()
    unit.unit_number = unit_number
    unit.bedrooms = 2
    unit.bathrooms = 1
    unit.pk = 1

    prop = MagicMock()
    prop.name = property_name
    prop.address = "1 Test Street"
    prop.city = "Cape Town"
    prop.province = "Western Cape"
    prop.postal_code = "8001"
    prop.get_property_type_display.return_value = "Apartment"

    unit.property = prop
    lease.unit = unit

    return lease, unit, prop


@pytest.mark.green
def test_build_tenant_context_returns_empty_when_no_lease():
    """Returns empty string when no active lease is found."""
    from apps.ai.tenant_context import build_tenant_context

    user = _make_mock_user()

    with patch("apps.ai.tenant_context.Lease.objects") as mock_mgr:
        mock_mgr.filter.return_value.select_related.return_value.order_by.return_value.first.return_value = None
        result = build_tenant_context(user)

    assert result == ""


@pytest.mark.green
def test_build_tenant_context_includes_property_name():
    """Returned context must include the property name."""
    from apps.ai.tenant_context import build_tenant_context

    user = _make_mock_user()
    lease, unit, prop = _make_mock_lease()

    with patch("apps.ai.tenant_context.Lease.objects") as mock_mgr, \
         patch("apps.ai.tenant_context.LeaseTenant.objects") as mock_lt, \
         patch("apps.ai.tenant_context.LeaseOccupant.objects") as mock_lo, \
         patch("apps.ai.tenant_context._safe_unit_info", return_value=[]), \
         patch("apps.ai.tenant_context.PropertyAgentConfig.objects") as mock_pac:

        mock_mgr.filter.return_value.select_related.return_value.order_by.return_value.first.return_value = lease
        mock_lt.filter.return_value.select_related.return_value.exists.return_value = False
        mock_lo.filter.return_value.select_related.return_value.exists.return_value = False
        mock_pac.filter.return_value.first.return_value = None

        result = build_tenant_context(user)

    assert "Sunset Gardens" in result


@pytest.mark.green
def test_build_tenant_context_includes_tenant_name():
    """Returned context must include the primary tenant's name."""
    from apps.ai.tenant_context import build_tenant_context

    user = _make_mock_user()
    lease, unit, prop = _make_mock_lease()

    with patch("apps.ai.tenant_context.Lease.objects") as mock_mgr, \
         patch("apps.ai.tenant_context.LeaseTenant.objects") as mock_lt, \
         patch("apps.ai.tenant_context.LeaseOccupant.objects") as mock_lo, \
         patch("apps.ai.tenant_context._safe_unit_info", return_value=[]), \
         patch("apps.ai.tenant_context.PropertyAgentConfig.objects") as mock_pac:

        mock_mgr.filter.return_value.select_related.return_value.order_by.return_value.first.return_value = lease
        mock_lt.filter.return_value.select_related.return_value.exists.return_value = False
        mock_lo.filter.return_value.select_related.return_value.exists.return_value = False
        mock_pac.filter.return_value.first.return_value = None

        result = build_tenant_context(user)

    assert "Jane Doe" in result


@pytest.mark.green
def test_build_tenant_context_includes_lease_dates():
    """Returned context must include lease start and end dates."""
    from apps.ai.tenant_context import build_tenant_context

    user = _make_mock_user()
    lease, unit, prop = _make_mock_lease()

    with patch("apps.ai.tenant_context.Lease.objects") as mock_mgr, \
         patch("apps.ai.tenant_context.LeaseTenant.objects") as mock_lt, \
         patch("apps.ai.tenant_context.LeaseOccupant.objects") as mock_lo, \
         patch("apps.ai.tenant_context._safe_unit_info", return_value=[]), \
         patch("apps.ai.tenant_context.PropertyAgentConfig.objects") as mock_pac:

        mock_mgr.filter.return_value.select_related.return_value.order_by.return_value.first.return_value = lease
        mock_lt.filter.return_value.select_related.return_value.exists.return_value = False
        mock_lo.filter.return_value.select_related.return_value.exists.return_value = False
        mock_pac.filter.return_value.first.return_value = None

        result = build_tenant_context(user)

    assert "2026-01-01" in result
    assert "2027-01-01" in result


@pytest.mark.green
def test_build_tenant_context_includes_header():
    """Returned context must start with the standard header line."""
    from apps.ai.tenant_context import build_tenant_context

    user = _make_mock_user()
    lease, unit, prop = _make_mock_lease()

    with patch("apps.ai.tenant_context.Lease.objects") as mock_mgr, \
         patch("apps.ai.tenant_context.LeaseTenant.objects") as mock_lt, \
         patch("apps.ai.tenant_context.LeaseOccupant.objects") as mock_lo, \
         patch("apps.ai.tenant_context._safe_unit_info", return_value=[]), \
         patch("apps.ai.tenant_context.PropertyAgentConfig.objects") as mock_pac:

        mock_mgr.filter.return_value.select_related.return_value.order_by.return_value.first.return_value = lease
        mock_lt.filter.return_value.select_related.return_value.exists.return_value = False
        mock_lo.filter.return_value.select_related.return_value.exists.return_value = False
        mock_pac.filter.return_value.first.return_value = None

        result = build_tenant_context(user)

    assert "TENANT & PROPERTY CONTEXT" in result


@pytest.mark.green
def test_build_tenant_context_includes_unit_info_when_present():
    """UnitInfo key-value pairs should appear in context when available."""
    from apps.ai.tenant_context import build_tenant_context

    user = _make_mock_user()
    lease, unit, prop = _make_mock_lease()

    with patch("apps.ai.tenant_context.Lease.objects") as mock_mgr, \
         patch("apps.ai.tenant_context.LeaseTenant.objects") as mock_lt, \
         patch("apps.ai.tenant_context.LeaseOccupant.objects") as mock_lo, \
         patch("apps.ai.tenant_context._safe_unit_info", return_value=[("WiFi password", "SuperSecret123")]), \
         patch("apps.ai.tenant_context.PropertyAgentConfig.objects") as mock_pac:

        mock_mgr.filter.return_value.select_related.return_value.order_by.return_value.first.return_value = lease
        mock_lt.filter.return_value.select_related.return_value.exists.return_value = False
        mock_lo.filter.return_value.select_related.return_value.exists.return_value = False
        mock_pac.filter.return_value.first.return_value = None

        result = build_tenant_context(user)

    assert "WiFi password" in result
    assert "SuperSecret123" in result


@pytest.mark.green
def test_build_tenant_context_uses_user_email_when_no_primary_tenant():
    """Falls back to user email in context when primary_tenant is None."""
    from apps.ai.tenant_context import build_tenant_context

    user = _make_mock_user(email="fallback@test.com", first_name="", last_name="")
    lease, unit, prop = _make_mock_lease()
    lease.primary_tenant = None

    with patch("apps.ai.tenant_context.Lease.objects") as mock_mgr, \
         patch("apps.ai.tenant_context.LeaseTenant.objects") as mock_lt, \
         patch("apps.ai.tenant_context.LeaseOccupant.objects") as mock_lo, \
         patch("apps.ai.tenant_context._safe_unit_info", return_value=[]), \
         patch("apps.ai.tenant_context.PropertyAgentConfig.objects") as mock_pac:

        mock_mgr.filter.return_value.select_related.return_value.order_by.return_value.first.return_value = lease
        mock_lt.filter.return_value.select_related.return_value.exists.return_value = False
        mock_lo.filter.return_value.select_related.return_value.exists.return_value = False
        mock_pac.filter.return_value.first.return_value = None

        result = build_tenant_context(user)

    assert "fallback@test.com" in result
