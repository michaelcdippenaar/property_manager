"""Unit tests for apps/ai/parsing.py — pure string parsing, no DB or mocks needed."""
import json
import pytest

from apps.ai.parsing import (
    strip_json_fence,
    parse_tenant_ai_response,
    parse_maintenance_draft_response,
    MAINTENANCE_DRAFT_CATEGORIES,
    MAINTENANCE_DRAFT_PRIORITIES,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# strip_json_fence
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_strip_json_fence_plain_passthrough():
    s = '{"key": "value"}'
    assert strip_json_fence(s) == s


@pytest.mark.green
def test_strip_json_fence_removes_json_fence():
    raw = '```json\n{"x": 1}\n```'
    assert strip_json_fence(raw) == '{"x": 1}'


@pytest.mark.green
def test_strip_json_fence_removes_plain_fence():
    raw = '```\n{"x": 1}\n```'
    assert strip_json_fence(raw) == '{"x": 1}'


@pytest.mark.green
def test_strip_json_fence_empty_string():
    assert strip_json_fence("") == ""


@pytest.mark.green
def test_strip_json_fence_none():
    assert strip_json_fence(None) == ""


# ---------------------------------------------------------------------------
# parse_tenant_ai_response
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_parse_tenant_ai_response_valid():
    raw = '{"reply": "Hello", "conversation_title": "Test", "maintenance_ticket": null}'
    reply, mt, ok, title = parse_tenant_ai_response(raw)
    assert ok is True
    assert reply == "Hello"
    assert title == "Test"
    assert mt is None


@pytest.mark.green
def test_parse_tenant_ai_response_with_ticket():
    raw = json.dumps({
        "reply": "I have noted the leak.",
        "conversation_title": "Kitchen leak",
        "maintenance_ticket": {"title": "Leak", "description": "Drip", "priority": "medium"},
    })
    reply, mt, ok, title = parse_tenant_ai_response(raw)
    assert ok is True
    assert reply == "I have noted the leak."
    assert mt is not None
    assert mt["title"] == "Leak"
    assert title == "Kitchen leak"


@pytest.mark.green
def test_parse_tenant_ai_response_invalid_json():
    raw = "this is not json"
    reply, mt, ok, title = parse_tenant_ai_response(raw)
    assert ok is False
    assert reply == raw
    assert mt is None
    assert title is None


@pytest.mark.green
def test_parse_tenant_ai_response_non_object_ticket_dropped():
    raw = '{"reply": "ok", "maintenance_ticket": "bad", "conversation_title": null}'
    _, mt, ok, _ = parse_tenant_ai_response(raw)
    assert ok is True
    assert mt is None


@pytest.mark.green
def test_parse_tenant_ai_response_strips_markdown_fence():
    raw = '```\n{"reply": "Hi", "maintenance_ticket": null, "conversation_title": null}\n```'
    reply, mt, ok, title = parse_tenant_ai_response(raw)
    assert ok is True
    assert reply == "Hi"


@pytest.mark.green
def test_parse_tenant_ai_response_title_truncated_at_200():
    long_title = "A" * 300
    raw = json.dumps({"reply": "x", "conversation_title": long_title, "maintenance_ticket": None})
    _, _, ok, title = parse_tenant_ai_response(raw)
    assert ok is True
    assert len(title) <= 200


@pytest.mark.green
def test_parse_tenant_ai_response_empty_title_returns_none():
    raw = json.dumps({"reply": "x", "conversation_title": "", "maintenance_ticket": None})
    _, _, ok, title = parse_tenant_ai_response(raw)
    assert ok is True
    assert title is None


# ---------------------------------------------------------------------------
# parse_maintenance_draft_response
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_parse_maintenance_draft_valid():
    raw = json.dumps({
        "title": "Leaking tap",
        "description": "Drips constantly",
        "priority": "medium",
        "category": "plumbing",
    })
    result = parse_maintenance_draft_response(raw)
    assert result is not None
    assert result["title"] == "Leaking tap"
    assert result["priority"] == "medium"
    assert result["category"] == "plumbing"


@pytest.mark.green
def test_parse_maintenance_draft_empty_title_returns_none():
    raw = json.dumps({"title": "", "description": "d", "priority": "low", "category": "other"})
    assert parse_maintenance_draft_response(raw) is None


@pytest.mark.green
def test_parse_maintenance_draft_unknown_category_maps_to_other():
    raw = json.dumps({"title": "Thing", "description": "d", "priority": "low", "category": "quantum"})
    result = parse_maintenance_draft_response(raw)
    assert result["category"] == "other"


@pytest.mark.green
def test_parse_maintenance_draft_unknown_priority_maps_to_medium():
    raw = json.dumps({"title": "Thing", "description": "d", "priority": "mega", "category": "other"})
    result = parse_maintenance_draft_response(raw)
    assert result["priority"] == "medium"


@pytest.mark.green
def test_parse_maintenance_draft_invalid_json_returns_none():
    assert parse_maintenance_draft_response("not json") is None


@pytest.mark.green
def test_parse_maintenance_draft_all_valid_categories():
    """All MAINTENANCE_DRAFT_CATEGORIES values must be accepted without remapping."""
    for cat in MAINTENANCE_DRAFT_CATEGORIES:
        raw = json.dumps({"title": "Test", "description": "d", "priority": "low", "category": cat})
        result = parse_maintenance_draft_response(raw)
        assert result["category"] == cat, f"Category {cat!r} was remapped unexpectedly"


@pytest.mark.green
def test_parse_maintenance_draft_all_valid_priorities():
    """All MAINTENANCE_DRAFT_PRIORITIES values must be accepted without remapping."""
    for pri in MAINTENANCE_DRAFT_PRIORITIES:
        raw = json.dumps({"title": "Test", "description": "d", "priority": pri, "category": "other"})
        result = parse_maintenance_draft_response(raw)
        assert result["priority"] == pri, f"Priority {pri!r} was remapped unexpectedly"


@pytest.mark.green
def test_parse_maintenance_draft_title_truncated_at_200():
    long_title = "X" * 300
    raw = json.dumps({"title": long_title, "description": "d", "priority": "low", "category": "other"})
    result = parse_maintenance_draft_response(raw)
    assert len(result["title"]) <= 200
