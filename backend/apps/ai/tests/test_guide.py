"""
Unit tests for the AI Guide endpoint.

Tests use unittest.mock to patch the Anthropic client so no real API calls
are made.  Three scenarios are covered:

1. valid_intent   — model returns a tool call → action in response
2. unknown_intent — model returns prose only → action is null
3. role_scoped    — model returns an agent-only tool while portal=owner → blocked
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

GUIDE_URL = "/api/v1/ai/guide/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tool_use_response(tool_name: str, text: str | None = None):
    """Build a mock Anthropic Messages response with a tool_use block."""
    blocks = []

    if text:
        txt_block = MagicMock()
        txt_block.type = "text"
        txt_block.text = text
        blocks.append(txt_block)

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = tool_name
    tool_block.input = {}
    blocks.append(tool_block)

    response = MagicMock()
    response.content = blocks
    return response


def _make_text_response(text: str):
    """Build a mock Anthropic Messages response with text only."""
    txt_block = MagicMock()
    txt_block.type = "text"
    txt_block.text = text

    response = MagicMock()
    response.content = [txt_block]
    return response


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def agent_user(db):
    return User.objects.create_user(
        email="guide_agent@test.klikk.co.za",
        password="T3stPass!",
        role=User.Role.ESTATE_AGENT,
    )


@pytest.fixture
def owner_user(db):
    return User.objects.create_user(
        email="guide_owner@test.klikk.co.za",
        password="T3stPass!",
        role=User.Role.OWNER,
    )


@pytest.fixture
def agent_client(agent_user):
    c = APIClient()
    c.force_authenticate(user=agent_user)
    return c


@pytest.fixture
def owner_client(owner_user):
    c = APIClient()
    c.force_authenticate(user=owner_user)
    return c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@patch("apps.ai.guide_views._get_anthropic_api_key", return_value="test-key")
@patch("apps.ai.guide_views.anthropic.Anthropic")
def test_valid_intent_returns_action(mock_anthropic_cls, _mock_key, agent_client):
    """A recognised intent should return a non-null action with a route."""
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _make_tool_use_response(
        "list_leases",
        text="Navigating to Leases.",
    )

    resp = agent_client.post(GUIDE_URL, {"message": "show me my leases", "portal": "agent"}, format="json")

    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] is not None
    assert data["action"]["route"] == "/leases"
    assert "leases" in data["reply"].lower() or data["reply"]  # non-empty reply


@pytest.mark.django_db
@patch("apps.ai.guide_views._get_anthropic_api_key", return_value="test-key")
@patch("apps.ai.guide_views.anthropic.Anthropic")
def test_unknown_intent_returns_null_action(mock_anthropic_cls, _mock_key, agent_client):
    """When the model returns prose only (no tool), action must be null."""
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _make_text_response(
        "I'm not sure what you mean. Could you clarify?"
    )

    resp = agent_client.post(GUIDE_URL, {"message": "xyzzy what is this", "portal": "agent"}, format="json")

    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] is None
    assert data["reply"]  # non-empty


@pytest.mark.django_db
@patch("apps.ai.guide_views._get_anthropic_api_key", return_value="test-key")
@patch("apps.ai.guide_views.anthropic.Anthropic")
def test_role_scoped_action_blocked(mock_anthropic_cls, _mock_key, owner_client):
    """An agent-only tool returned for an owner portal must be blocked."""
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    # The model (mis-)returns an agent-only tool while we're in owner portal
    mock_client.messages.create.return_value = _make_tool_use_response("create_property")

    resp = owner_client.post(GUIDE_URL, {"message": "add a property", "portal": "owner"}, format="json")

    assert resp.status_code == 200
    data = resp.json()
    # Action must be blocked — not forwarded to the frontend
    assert data["action"] is None
    assert data["reply"]  # a refusal message


@pytest.mark.django_db
def test_unauthenticated_rejected():
    """Unauthenticated requests must receive 401."""
    client = APIClient()
    resp = client.post(GUIDE_URL, {"message": "go to leases", "portal": "agent"}, format="json")
    assert resp.status_code == 401


@pytest.mark.django_db
def test_missing_message_returns_400(agent_client):
    """Empty message should return 400."""
    resp = agent_client.post(GUIDE_URL, {"message": "", "portal": "agent"}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
@patch("apps.ai.guide_views._get_anthropic_api_key", return_value="test-key")
@patch("apps.ai.guide_views.anthropic.Anthropic")
def test_guide_interaction_persisted(mock_anthropic_cls, _mock_key, agent_client):
    """A valid request must persist a GuideInteraction row."""
    from apps.ai.models import GuideInteraction

    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _make_tool_use_response(
        "go_to_dashboard",
        text="Taking you to the Dashboard.",
    )

    initial_count = GuideInteraction.objects.count()
    agent_client.post(GUIDE_URL, {"message": "go home", "portal": "agent"}, format="json")
    assert GuideInteraction.objects.count() == initial_count + 1
    interaction = GuideInteraction.objects.latest("created_at")
    assert interaction.intent == "go_to_dashboard"
    assert interaction.completed is True
