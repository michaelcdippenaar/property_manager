"""Unit tests for apps/leases/events.py — lease event and onboarding step generation.

Patching strategy: events.py creates LeaseEvent(...) and OnboardingStep(...) instances
directly, so we patch the classes at their import location in apps.leases.events to
prevent Django FK descriptor validation on the mock lease object.
"""
import pytest
from datetime import date
from unittest.mock import MagicMock, patch


pytestmark = pytest.mark.unit


def _make_lease(start, end, deposit=10000, monthly_rent=5000, notice_days=20, primary_name="Jane Doe"):
    """Build a minimal mock Lease for unit tests (no DB)."""
    lease = MagicMock()
    lease.start_date = start
    lease.end_date = end
    lease.deposit = deposit
    lease.monthly_rent = monthly_rent
    lease.notice_period_days = notice_days
    tenant = MagicMock()
    tenant.full_name = primary_name
    lease.primary_tenant = tenant
    unit = MagicMock()
    unit.__str__ = lambda self: "Unit 3"
    lease.unit = unit
    lease.events = MagicMock()
    lease.events.exclude.return_value.delete = MagicMock()
    lease.onboarding_steps = MagicMock()
    lease.onboarding_steps.all.return_value.delete = MagicMock()
    return lease


def _patch_lease_event():
    """
    Patch LeaseEvent at the events module import location.
    Returns (patcher, captured_list) — captured_list is populated by bulk_create calls.
    """
    from apps.leases.models import LeaseEvent as RealLeaseEvent
    captured = []

    mock_cls = MagicMock()
    mock_cls.EventType = RealLeaseEvent.EventType

    def make_event(**kwargs):
        m = MagicMock()
        for k, v in kwargs.items():
            setattr(m, k, v)
        return m

    mock_cls.side_effect = make_event
    mock_cls.objects.bulk_create.side_effect = lambda evts: captured.extend(evts) or evts

    return patch("apps.leases.events.LeaseEvent", mock_cls), captured


def _patch_onboarding_step():
    """
    Patch OnboardingStep at the events module import location.
    Returns (patcher, captured_list).
    """
    from apps.leases.models import OnboardingStep as RealStep
    captured = []

    mock_cls = MagicMock()
    mock_cls.StepType = RealStep.StepType

    def make_step(**kwargs):
        m = MagicMock()
        for k, v in kwargs.items():
            setattr(m, k, v)
        captured.append(m)
        return m

    mock_cls.side_effect = make_step
    mock_cls.objects.bulk_create.side_effect = lambda steps: steps

    return patch("apps.leases.events.OnboardingStep", mock_cls), captured


# ---------------------------------------------------------------------------
# generate_lease_events
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_generate_lease_events_creates_bulk():
    """generate_lease_events should call LeaseEvent.objects.bulk_create."""
    from apps.leases.events import generate_lease_events
    lease = _make_lease(date(2026, 1, 1), date(2027, 1, 1))
    patcher, captured = _patch_lease_event()
    with patcher:
        generate_lease_events(lease)
    assert len(captured) > 0


@pytest.mark.green
def test_generate_lease_events_includes_contract_start_and_end():
    """Contract start and end events must always be generated."""
    from apps.leases.events import generate_lease_events
    from apps.leases.models import LeaseEvent
    lease = _make_lease(date(2026, 1, 1), date(2027, 1, 1))
    patcher, captured = _patch_lease_event()
    with patcher:
        generate_lease_events(lease)
    event_types = [e.event_type for e in captured]
    assert LeaseEvent.EventType.CONTRACT_START in event_types
    assert LeaseEvent.EventType.CONTRACT_END in event_types


@pytest.mark.green
def test_generate_lease_events_includes_deposit_due():
    """A deposit_due event must be generated."""
    from apps.leases.events import generate_lease_events
    from apps.leases.models import LeaseEvent
    lease = _make_lease(date(2026, 1, 1), date(2027, 1, 1))
    patcher, captured = _patch_lease_event()
    with patcher:
        generate_lease_events(lease)
    event_types = [e.event_type for e in captured]
    assert LeaseEvent.EventType.DEPOSIT_DUE in event_types


@pytest.mark.green
def test_generate_lease_events_includes_move_in_inspection():
    """A move-in inspection event must be generated."""
    from apps.leases.events import generate_lease_events
    from apps.leases.models import LeaseEvent
    lease = _make_lease(date(2026, 1, 1), date(2027, 1, 1))
    patcher, captured = _patch_lease_event()
    with patcher:
        generate_lease_events(lease)
    event_types = [e.event_type for e in captured]
    assert LeaseEvent.EventType.INSPECTION_IN in event_types


@pytest.mark.green
def test_generate_lease_events_includes_renewal_review_for_long_lease():
    """A 12-month lease should generate a renewal_review 60 days before end."""
    from apps.leases.events import generate_lease_events
    from apps.leases.models import LeaseEvent
    lease = _make_lease(date(2026, 1, 1), date(2027, 1, 1))
    patcher, captured = _patch_lease_event()
    with patcher:
        generate_lease_events(lease)
    event_types = [e.event_type for e in captured]
    assert LeaseEvent.EventType.RENEWAL_REVIEW in event_types


@pytest.mark.green
def test_generate_lease_events_clears_non_custom_first():
    """generate_lease_events must delete existing non-custom events first."""
    from apps.leases.events import generate_lease_events
    from apps.leases.models import LeaseEvent
    lease = _make_lease(date(2026, 1, 1), date(2027, 1, 1))
    patcher, _ = _patch_lease_event()
    with patcher:
        generate_lease_events(lease)
    lease.events.exclude.assert_called_once_with(event_type=LeaseEvent.EventType.CUSTOM)
    lease.events.exclude.return_value.delete.assert_called_once()


@pytest.mark.green
def test_generate_lease_events_no_primary_tenant():
    """generate_lease_events should not crash when primary_tenant is None."""
    from apps.leases.events import generate_lease_events
    lease = _make_lease(date(2026, 1, 1), date(2027, 1, 1))
    lease.primary_tenant = None
    patcher, _ = _patch_lease_event()
    with patcher:
        generate_lease_events(lease)  # must not raise


@pytest.mark.green
def test_first_rent_on_first_of_month():
    """If lease starts on the 1st, first rent event date equals start_date."""
    from apps.leases.events import generate_lease_events
    from apps.leases.models import LeaseEvent
    lease = _make_lease(date(2026, 3, 1), date(2027, 3, 1))
    patcher, captured = _patch_lease_event()
    with patcher:
        generate_lease_events(lease)
    first_rent = next((e for e in captured if e.event_type == LeaseEvent.EventType.FIRST_RENT), None)
    assert first_rent is not None
    assert first_rent.date == date(2026, 3, 1)


@pytest.mark.green
def test_first_rent_rolls_to_next_month():
    """If lease starts mid-month (e.g. Jan 15), first rent rolls to Feb 1."""
    from apps.leases.events import generate_lease_events
    from apps.leases.models import LeaseEvent
    lease = _make_lease(date(2026, 1, 15), date(2027, 1, 15))
    patcher, captured = _patch_lease_event()
    with patcher:
        generate_lease_events(lease)
    first_rent = next((e for e in captured if e.event_type == LeaseEvent.EventType.FIRST_RENT), None)
    assert first_rent is not None
    assert first_rent.date == date(2026, 2, 1)


# ---------------------------------------------------------------------------
# generate_onboarding_steps
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_generate_onboarding_steps_creates_8_steps():
    """Standard onboarding should create exactly 8 steps."""
    from apps.leases.events import generate_onboarding_steps
    lease = _make_lease(date(2026, 1, 1), date(2027, 1, 1))
    patcher, captured = _patch_onboarding_step()
    with patcher:
        generate_onboarding_steps(lease)
    assert len(captured) == 8


@pytest.mark.green
def test_generate_onboarding_steps_includes_lease_signed():
    """LEASE_SIGNED step must be in the standard onboarding checklist."""
    from apps.leases.events import generate_onboarding_steps
    from apps.leases.models import OnboardingStep
    lease = _make_lease(date(2026, 1, 1), date(2027, 1, 1))
    patcher, captured = _patch_onboarding_step()
    with patcher:
        generate_onboarding_steps(lease)
    step_types = [s.step_type for s in captured]
    assert OnboardingStep.StepType.LEASE_SIGNED in step_types


@pytest.mark.green
def test_generate_onboarding_steps_ordered():
    """Steps must have incrementing order values starting at 1."""
    from apps.leases.events import generate_onboarding_steps
    lease = _make_lease(date(2026, 1, 1), date(2027, 1, 1))
    patcher, captured = _patch_onboarding_step()
    with patcher:
        generate_onboarding_steps(lease)
    orders = [s.order for s in captured]
    assert orders == sorted(orders)
    assert min(orders) == 1


@pytest.mark.green
def test_generate_onboarding_steps_clears_existing():
    """generate_onboarding_steps must delete all existing steps first."""
    from apps.leases.events import generate_onboarding_steps
    lease = _make_lease(date(2026, 1, 1), date(2027, 1, 1))
    patcher, _ = _patch_onboarding_step()
    with patcher:
        generate_onboarding_steps(lease)
    lease.onboarding_steps.all.assert_called_once()
    lease.onboarding_steps.all.return_value.delete.assert_called_once()
