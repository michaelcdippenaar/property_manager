"""Unit tests for message serialization and windowing utilities in tenant_portal/views.py."""
import pytest
from unittest.mock import MagicMock
from django.utils import timezone


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _serialize_stored_message
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_serialize_stored_message_basic_fields():
    """_serialize_stored_message returns id, role, content."""
    from apps.tenant_portal.views import _serialize_stored_message

    msg = {"id": 1, "role": "user", "content": "Hello there"}
    result = _serialize_stored_message(msg, request=None)
    assert result["id"] == 1
    assert result["role"] == "user"
    assert result["content"] == "Hello there"


@pytest.mark.green
def test_serialize_stored_message_no_attachment():
    """Without an attachment, attachment_url should be None."""
    from apps.tenant_portal.views import _serialize_stored_message

    msg = {"id": 2, "role": "assistant", "content": "OK", "attachment_storage": "", "attachment_kind": ""}
    result = _serialize_stored_message(msg, request=None)
    assert result["attachment_url"] is None


@pytest.mark.green
def test_serialize_stored_message_empty_content_defaults_to_empty_string():
    """Missing content key should default to empty string, not None."""
    from apps.tenant_portal.views import _serialize_stored_message

    msg = {"id": 3, "role": "user"}
    result = _serialize_stored_message(msg, request=None)
    assert result["content"] == ""


@pytest.mark.green
def test_serialize_stored_message_attachment_kind_passthrough():
    """attachment_kind from stored message should appear in output."""
    from apps.tenant_portal.views import _serialize_stored_message

    msg = {"id": 4, "role": "user", "content": "see pic", "attachment_kind": "image", "attachment_storage": ""}
    result = _serialize_stored_message(msg, request=None)
    assert result["attachment_kind"] == "image"


# ---------------------------------------------------------------------------
# _next_message_id
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_next_message_id_empty_list():
    """Empty message list should produce id=1."""
    from apps.tenant_portal.views import _next_message_id
    assert _next_message_id([]) == 1


@pytest.mark.green
def test_next_message_id_sequential():
    """Message list with highest id=5 should produce id=6."""
    from apps.tenant_portal.views import _next_message_id
    messages = [{"id": 1}, {"id": 3}, {"id": 5}]
    assert _next_message_id(messages) == 6


@pytest.mark.green
def test_next_message_id_missing_id_ignored():
    """Messages without 'id' key should not crash _next_message_id."""
    from apps.tenant_portal.views import _next_message_id
    messages = [{"id": 2}, {"role": "user"}]  # second has no id
    result = _next_message_id(messages)
    assert result >= 3  # at least 2+1


# ---------------------------------------------------------------------------
# _build_windowed_messages
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_build_windowed_messages_short_conversation():
    """Short conversations (≤ MAX_CHAT_WINDOW) are returned in full."""
    from apps.tenant_portal.views import _build_windowed_messages, MAX_CHAT_WINDOW

    messages = [
        {"id": i, "role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}", "attachment_kind": ""}
        for i in range(1, min(MAX_CHAT_WINDOW, 6) + 1)
    ]
    result = _build_windowed_messages(messages)
    assert len(result) == len(messages)


@pytest.mark.green
def test_build_windowed_messages_empty():
    """Empty message list returns empty list."""
    from apps.tenant_portal.views import _build_windowed_messages
    assert _build_windowed_messages([]) == []


@pytest.mark.green
def test_build_windowed_messages_long_conversation_prepends_summary():
    """Long conversations have a summary + ack prepended, then recent messages."""
    from apps.tenant_portal.views import _build_windowed_messages, MAX_CHAT_WINDOW

    # Build more messages than the window
    messages = [
        {"id": i, "role": "user" if i % 2 == 1 else "assistant", "content": f"content {i}", "attachment_kind": ""}
        for i in range(1, MAX_CHAT_WINDOW + 5)
    ]
    result = _build_windowed_messages(messages)

    # First two items must be the summary user-message and assistant ack
    assert result[0]["role"] == "user"
    assert "Summary" in result[0]["content"]
    assert result[1]["role"] == "assistant"


@pytest.mark.green
def test_build_windowed_messages_long_conversation_has_recent_messages():
    """Long conversations include the MAX_CHAT_WINDOW most recent messages after the summary."""
    from apps.tenant_portal.views import _build_windowed_messages, MAX_CHAT_WINDOW

    messages = [
        {"id": i, "role": "user" if i % 2 == 1 else "assistant", "content": f"content {i}", "attachment_kind": ""}
        for i in range(1, MAX_CHAT_WINDOW + 5)
    ]
    result = _build_windowed_messages(messages)

    # 2 prefix items + MAX_CHAT_WINDOW recent items
    assert len(result) == 2 + MAX_CHAT_WINDOW


@pytest.mark.green
def test_build_windowed_messages_role_mapping():
    """'assistant' role in stored messages maps to 'assistant' in output; everything else to 'user'."""
    from apps.tenant_portal.views import _build_windowed_messages

    messages = [
        {"id": 1, "role": "user", "content": "Hello", "attachment_kind": ""},
        {"id": 2, "role": "assistant", "content": "Hi", "attachment_kind": ""},
    ]
    result = _build_windowed_messages(messages)
    roles = [m["role"] for m in result]
    assert "user" in roles
    assert "assistant" in roles


# ---------------------------------------------------------------------------
# _serialize_skills_used
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_serialize_skills_used_empty_string():
    """Empty skills text: used=False, preview=[]."""
    from apps.tenant_portal.views import _serialize_skills_used

    result = _serialize_skills_used("")
    assert result["used"] is False
    assert result["preview"] == []


@pytest.mark.green
def test_serialize_skills_used_with_content():
    """Non-empty skills text should produce a non-empty preview."""
    from apps.tenant_portal.views import _serialize_skills_used

    text = "Used: plumbing_repair, water_shutoff"
    result = _serialize_skills_used(text)
    assert isinstance(result["preview"], list)
    assert result["used"] is True


# ---------------------------------------------------------------------------
# _is_generic_conv_title
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_is_generic_conv_title_new_conversation():
    """'New conversation' is a generic title."""
    from apps.tenant_portal.views import _is_generic_conv_title
    assert _is_generic_conv_title("New conversation") is True


@pytest.mark.green
def test_is_generic_conv_title_ai_assistant():
    """'AI Assistant' is a generic title."""
    from apps.tenant_portal.views import _is_generic_conv_title
    assert _is_generic_conv_title("AI Assistant") is True


@pytest.mark.green
def test_is_generic_conv_title_specific():
    """A specific descriptive title is not generic."""
    from apps.tenant_portal.views import _is_generic_conv_title
    assert _is_generic_conv_title("Kitchen tap leaking") is False
