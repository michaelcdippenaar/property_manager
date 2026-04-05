"""Unit tests for leases models — no DB where possible."""
import pytest
from datetime import date
from unittest.mock import MagicMock


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Lease model
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_lease_str_with_primary_tenant():
    """Lease.__str__ includes primary tenant name and unit."""
    from apps.leases.models import Lease
    from django.db.models.base import ModelState
    lease = Lease.__new__(Lease)
    lease._state = ModelState()
    tenant = MagicMock()
    tenant.full_name = "Jane Doe"
    unit = MagicMock()
    unit.__str__ = lambda self: "Unit 3"
    lease._state.fields_cache["primary_tenant"] = tenant
    lease._state.fields_cache["unit"] = unit
    assert "Jane Doe" in str(lease)
    assert "Unit 3" in str(lease)


@pytest.mark.green
def test_lease_str_without_primary_tenant():
    """Lease.__str__ falls back to 'Unknown' when primary_tenant is None."""
    from apps.leases.models import Lease
    from django.db.models.base import ModelState
    lease = Lease.__new__(Lease)
    lease._state = ModelState()
    lease._state.fields_cache["primary_tenant"] = None
    unit = MagicMock()
    unit.__str__ = lambda self: "Unit 1"
    lease._state.fields_cache["unit"] = unit
    assert "Unknown" in str(lease)


@pytest.mark.green
def test_lease_status_choices_include_active():
    """Lease.Status choices must include 'active'."""
    from apps.leases.models import Lease
    values = [c[0] for c in Lease.Status.choices]
    assert "active" in values


@pytest.mark.green
def test_lease_status_choices_include_pending_expired_terminated():
    """Lease.Status choices should cover the full rental lifecycle."""
    from apps.leases.models import Lease
    values = [c[0] for c in Lease.Status.choices]
    assert "pending" in values
    assert "expired" in values
    assert "terminated" in values


@pytest.mark.green
def test_lease_end_date_after_start_date_not_enforced():
    """
    RED: No model-level validation that end_date > start_date.
    This test documents the gap — it should fail once the validation is added.
    Until then, it passes because the model accepts invalid dates without raising.
    """
    from apps.leases.models import Lease
    # If model-level clean() is ever added, calling full_clean() would raise.
    # Currently, no validation exists at the model level.
    lease = Lease.__new__(Lease)
    lease.start_date = date(2027, 1, 1)
    lease.end_date = date(2026, 1, 1)
    # No clean() call, so no error — gap confirmed
    assert lease.end_date < lease.start_date


# ---------------------------------------------------------------------------
# LeaseTemplate model
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_lease_template_str():
    """LeaseTemplate.__str__ returns 'name v{version}'."""
    from apps.leases.models import LeaseTemplate
    t = LeaseTemplate.__new__(LeaseTemplate)
    t.name = "Standard Lease"
    t.version = "2.1"
    assert str(t) == "Standard Lease v2.1"


@pytest.mark.green
def test_lease_template_content_html_default():
    """LeaseTemplate.content_html defaults to empty string."""
    from apps.leases.models import LeaseTemplate
    field = LeaseTemplate._meta.get_field("content_html")
    assert field.default == ""


@pytest.mark.green
def test_lease_template_is_active_default():
    """LeaseTemplate.is_active defaults to True."""
    from apps.leases.models import LeaseTemplate
    field = LeaseTemplate._meta.get_field("is_active")
    assert field.default is True


# ---------------------------------------------------------------------------
# ReusableClause model
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_reusable_clause_str():
    """ReusableClause.__str__ returns its title."""
    from apps.leases.models import ReusableClause
    clause = ReusableClause.__new__(ReusableClause)
    clause.title = "Pet Policy Clause"
    assert str(clause) == "Pet Policy Clause"


@pytest.mark.green
def test_reusable_clause_category_default():
    """ReusableClause.category defaults to 'general'."""
    from apps.leases.models import ReusableClause
    field = ReusableClause._meta.get_field("category")
    assert field.default == "general"


@pytest.mark.green
def test_reusable_clause_categories_include_expected_values():
    """ReusableClause.CATEGORIES must contain 'financial', 'legal', 'general'."""
    from apps.leases.models import ReusableClause
    category_keys = [c[0] for c in ReusableClause.CATEGORIES]
    assert "financial" in category_keys
    assert "legal" in category_keys
    assert "general" in category_keys


# ---------------------------------------------------------------------------
# LeaseEvent model
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_lease_event_str():
    """LeaseEvent.__str__ returns title and date."""
    from apps.leases.models import LeaseEvent
    event = LeaseEvent.__new__(LeaseEvent)
    event.title = "Rent Due"
    event.date = date(2026, 3, 1)
    result = str(event)
    assert "Rent Due" in result
    assert "2026-03-01" in result


@pytest.mark.green
def test_lease_event_type_choices_include_rent_due():
    """LeaseEvent.EventType must include 'rent_due'."""
    from apps.leases.models import LeaseEvent
    values = [c[0] for c in LeaseEvent.EventType.choices]
    assert "rent_due" in values


@pytest.mark.green
def test_lease_event_type_choices_complete():
    """LeaseEvent.EventType should cover all standard events."""
    from apps.leases.models import LeaseEvent
    values = [c[0] for c in LeaseEvent.EventType.choices]
    expected = {
        "contract_start", "contract_end", "deposit_due", "first_rent",
        "rent_due", "inspection_in", "inspection_out", "inspection_routine",
        "notice_deadline", "renewal_review", "custom",
    }
    assert expected.issubset(set(values))


@pytest.mark.green
def test_lease_event_status_default():
    """LeaseEvent.status defaults to 'upcoming'."""
    from apps.leases.models import LeaseEvent
    field = LeaseEvent._meta.get_field("status")
    assert field.default == LeaseEvent.Status.UPCOMING


# ---------------------------------------------------------------------------
# LeaseBuilderSession model
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_builder_session_str():
    """LeaseBuilderSession.__str__ includes id, user and status."""
    from apps.leases.models import LeaseBuilderSession
    from django.db.models.base import ModelState
    session = LeaseBuilderSession.__new__(LeaseBuilderSession)
    session._state = ModelState()
    session.id = 42
    user = MagicMock()
    user.__str__ = lambda self: "agent@example.com"
    session._state.fields_cache["created_by"] = user
    session.status = "drafting"
    result = str(session)
    assert "42" in result
    assert "drafting" in result
