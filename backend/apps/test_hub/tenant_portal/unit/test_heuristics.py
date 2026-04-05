"""Unit tests for heuristic functions in apps/tenant_portal/views.py.

These are pure string classification functions — no DB or mocks needed.
"""
import pytest

# Import the functions directly from views — they are module-level helpers.
from apps.tenant_portal.views import (
    _heuristic_maintenance_ticket,
    _heuristic_severe_ticket,
    _has_usable_maintenance_ticket,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _heuristic_maintenance_ticket
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_heuristic_maintenance_ticket_leaking_tap():
    """'my tap is leaking' should trigger a maintenance ticket."""
    result = _heuristic_maintenance_ticket("my tap is leaking badly")
    assert result is not None
    assert "title" in result
    assert "category" in result


@pytest.mark.green
def test_heuristic_maintenance_ticket_returns_none_for_general():
    """'how do I pay rent' should NOT trigger a maintenance ticket."""
    result = _heuristic_maintenance_ticket("how do I pay rent")
    assert result is None


@pytest.mark.green
def test_heuristic_maintenance_ticket_broken_door():
    """'broken door' should trigger a maintenance ticket."""
    result = _heuristic_maintenance_ticket("my front door is broken and won't close")
    assert result is not None


@pytest.mark.green
def test_heuristic_maintenance_ticket_no_power():
    """'no power' should trigger a maintenance ticket."""
    result = _heuristic_maintenance_ticket("we have no power in the kitchen")
    assert result is not None


@pytest.mark.green
def test_heuristic_maintenance_ticket_pest():
    """'cockroach' should trigger a maintenance ticket."""
    result = _heuristic_maintenance_ticket("there is a cockroach in the bathroom")
    assert result is not None


@pytest.mark.green
def test_heuristic_maintenance_ticket_plumbing_category():
    """'tap leaking' should categorise as plumbing."""
    result = _heuristic_maintenance_ticket("my kitchen tap is dripping")
    assert result is not None
    assert result["category"] == "plumbing"


@pytest.mark.green
def test_heuristic_maintenance_ticket_electrical_category():
    """'socket sparking' should categorise as electrical."""
    result = _heuristic_maintenance_ticket("the wall socket is sparking")
    assert result is not None
    assert result["category"] == "electrical"


@pytest.mark.green
def test_heuristic_maintenance_ticket_returns_dict_with_required_keys():
    """Returned ticket must have title, description, priority, and category."""
    result = _heuristic_maintenance_ticket("the roof is leaking")
    assert result is not None
    assert "title" in result
    assert "description" in result
    assert "priority" in result
    assert "category" in result


@pytest.mark.green
def test_heuristic_maintenance_ticket_title_truncated_at_80():
    """Title in heuristic ticket should not exceed 80 characters."""
    long_msg = "my tap is leaking " + "x" * 200
    result = _heuristic_maintenance_ticket(long_msg)
    assert result is not None
    assert len(result["title"]) <= 80


@pytest.mark.green
def test_heuristic_maintenance_ticket_case_insensitive():
    """Hint matching should be case-insensitive."""
    result = _heuristic_maintenance_ticket("THE GEYSER IS BROKEN")
    assert result is not None


# ---------------------------------------------------------------------------
# _heuristic_severe_ticket
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_heuristic_severe_ticket_flood():
    """'the flat flooded' should trigger a severe ticket."""
    result = _heuristic_severe_ticket("the flat flooded — everything is soaked")
    assert result is not None


@pytest.mark.green
def test_heuristic_severe_ticket_burst_pipe():
    """'burst pipe' should trigger a severe ticket."""
    result = _heuristic_severe_ticket("there is a burst pipe in the bathroom")
    assert result is not None


@pytest.mark.green
def test_heuristic_severe_ticket_break_in():
    """'break-in' should trigger a severe ticket."""
    result = _heuristic_severe_ticket("there was a break-in last night")
    assert result is not None


@pytest.mark.green
def test_heuristic_severe_ticket_returns_none_for_light_bulb():
    """'light bulb' should NOT trigger a severe ticket."""
    result = _heuristic_severe_ticket("my light bulb needs replacing")
    assert result is None


@pytest.mark.green
def test_heuristic_severe_ticket_returns_none_for_pay_rent():
    """'how do I pay rent' should NOT trigger a severe ticket."""
    result = _heuristic_severe_ticket("how do I pay rent this month")
    assert result is None


@pytest.mark.green
def test_heuristic_severe_ticket_gas_smell():
    """'gas smell' should trigger a severe ticket."""
    result = _heuristic_severe_ticket("there is a strong gas smell in the flat")
    assert result is not None


@pytest.mark.green
def test_heuristic_severe_ticket_returns_dict_with_required_keys():
    """Returned severe ticket must have title, description, priority, and category."""
    result = _heuristic_severe_ticket("burst pipe flooding the unit")
    assert result is not None
    assert "title" in result
    assert "description" in result
    assert "priority" in result
    assert "category" in result


@pytest.mark.green
def test_heuristic_severe_ticket_burglary_is_security_category():
    """'burglary' should map to security category."""
    result = _heuristic_severe_ticket("there was a burglary at my flat")
    assert result is not None
    assert result["category"] == "security"


@pytest.mark.green
def test_heuristic_severe_ticket_leak_is_plumbing_category():
    """'leak' in a severe context should map to plumbing."""
    result = _heuristic_severe_ticket("massive leak the flat flooded")
    assert result is not None
    assert result["category"] == "plumbing"


# ---------------------------------------------------------------------------
# _has_usable_maintenance_ticket
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_has_usable_ticket_with_title():
    """Returns True when ticket has a non-empty title."""
    assert _has_usable_maintenance_ticket({"title": "Leaking tap", "description": "x"}) is True


@pytest.mark.green
def test_has_usable_ticket_with_empty_title():
    """Returns False when ticket title is empty."""
    assert _has_usable_maintenance_ticket({"title": "   ", "description": "x"}) is False


@pytest.mark.green
def test_has_usable_ticket_none():
    """Returns False when ticket is None."""
    assert _has_usable_maintenance_ticket(None) is False


@pytest.mark.green
def test_has_usable_ticket_empty_dict():
    """Returns False for an empty dict."""
    assert _has_usable_maintenance_ticket({}) is False
