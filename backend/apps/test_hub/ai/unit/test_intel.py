"""Unit tests for apps/ai/intel.py — _classify_category, _extract_facts, and severity tracking."""
import pytest
from unittest.mock import MagicMock, patch


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _classify_category — pure function (no DB, no API)
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_classify_category_with_valid_ticket():
    """Returns 'maintenance_ticket' when json_ok=True and ticket has a title."""
    from apps.ai.intel import _classify_category
    ticket = {"title": "Leaking tap", "description": "Drips", "priority": "medium"}
    assert _classify_category(ticket, json_ok=True) == "maintenance_ticket"


@pytest.mark.green
def test_classify_category_no_ticket():
    """Returns 'general_enquiry' when maintenance_ticket is None."""
    from apps.ai.intel import _classify_category
    assert _classify_category(None, json_ok=True) == "general_enquiry"


@pytest.mark.green
def test_classify_category_json_not_ok():
    """Returns 'general_enquiry' when json_ok=False regardless of ticket content."""
    from apps.ai.intel import _classify_category
    ticket = {"title": "Something", "description": "x"}
    assert _classify_category(ticket, json_ok=False) == "general_enquiry"


@pytest.mark.green
def test_classify_category_empty_title():
    """Returns 'general_enquiry' when ticket title is empty string."""
    from apps.ai.intel import _classify_category
    ticket = {"title": "   ", "description": "something"}
    assert _classify_category(ticket, json_ok=True) == "general_enquiry"


@pytest.mark.green
def test_classify_category_empty_dict():
    """Returns 'general_enquiry' when ticket is an empty dict."""
    from apps.ai.intel import _classify_category
    assert _classify_category({}, json_ok=True) == "general_enquiry"


# ---------------------------------------------------------------------------
# _extract_facts — pure function (no DB, no API)
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_extract_facts_detects_whatsapp_preference():
    """'prefer whatsapp' in a user message should set contact_preference=whatsapp."""
    from apps.ai.intel import _extract_facts
    messages = [{"role": "user", "content": "I prefer whatsapp for updates"}]
    facts = _extract_facts(messages)
    assert facts.get("contact_preference") == "whatsapp"


@pytest.mark.green
def test_extract_facts_detects_pets():
    """'my dog' in a user message should set has_pets=true."""
    from apps.ai.intel import _extract_facts
    messages = [{"role": "user", "content": "I have my dog staying with me"}]
    facts = _extract_facts(messages)
    assert facts.get("has_pets") == "true"


@pytest.mark.green
def test_extract_facts_detects_wfh():
    """'work from home' should set works_from_home=true."""
    from apps.ai.intel import _extract_facts
    messages = [{"role": "user", "content": "I work from home most days"}]
    facts = _extract_facts(messages)
    assert facts.get("works_from_home") == "true"


@pytest.mark.green
def test_extract_facts_detects_vehicle():
    """'my car' should set has_vehicle=true."""
    from apps.ai.intel import _extract_facts
    messages = [{"role": "user", "content": "I need a parking bay for my car"}]
    facts = _extract_facts(messages)
    assert facts.get("has_vehicle") == "true"


@pytest.mark.green
def test_extract_facts_ignores_assistant_messages():
    """Assistant messages should not be scanned for facts."""
    from apps.ai.intel import _extract_facts
    messages = [
        {"role": "assistant", "content": "I prefer whatsapp contact"},
    ]
    facts = _extract_facts(messages)
    assert "contact_preference" not in facts


@pytest.mark.green
def test_extract_facts_empty_messages():
    """Empty message list returns empty facts dict."""
    from apps.ai.intel import _extract_facts
    assert _extract_facts([]) == {}


@pytest.mark.green
def test_extract_facts_none_messages():
    """None message list returns empty facts dict."""
    from apps.ai.intel import _extract_facts
    assert _extract_facts(None) == {}


@pytest.mark.green
def test_extract_facts_only_last_10_user_messages():
    """Only the last 10 user messages are scanned (performance guard)."""
    from apps.ai.intel import _extract_facts
    # 11 user messages — the first one has the whatsapp hint but is beyond the window
    messages = [{"role": "user", "content": "I prefer whatsapp"}]
    messages += [{"role": "user", "content": "nothing special"} for _ in range(10)]
    facts = _extract_facts(messages)
    # The 11th-oldest user message is outside the last-10 window
    assert "contact_preference" not in facts


@pytest.mark.green
def test_extract_facts_detects_recurring_water_pressure():
    """'low water pressure' should set recurring_issue=water_pressure."""
    from apps.ai.intel import _extract_facts
    messages = [{"role": "user", "content": "The low water pressure is still an issue"}]
    facts = _extract_facts(messages)
    assert facts.get("recurring_issue") == "water_pressure"


# ---------------------------------------------------------------------------
# update_tenant_intel — requires DB; marked red (needs DB fixture)
# ---------------------------------------------------------------------------

@pytest.mark.red
def test_update_tenant_intel_upserts_record():
    """
    RED: update_tenant_intel() calls TenantIntelligence.objects.get_or_create —
    this requires a real DB transaction. Mark red until a DB fixture is wired.

    When green, verify:
      - TenantIntelligence created on first call
      - total_chats and total_messages updated
      - question_categories incremented
      - complaint_score recalculated
    """
    # Placeholder — implement with pytest-django db fixture
    pytest.skip("Requires DB — implement with @pytest.mark.django_db")
