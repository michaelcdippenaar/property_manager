"""
Unit tests for the AI Guide endpoint.

Tests use unittest.mock to patch the Anthropic client so no real API calls
are made.

Scenarios:
1. valid_intent         — model returns a tool call → action in response
2. unknown_intent       — model returns prose only → action is null
3. role_scoped          — model returns an agent-only tool while portal=owner → blocked
4. unauthenticated      — 401
5. missing_message      — 400
6. interaction_persisted— GuideInteraction row created on valid request
7. tenant_portal_spoof  — TENANT user gets 403 (portal derived from role, not payload)
8. oversized_message    — >2000 chars returns 400
9. rate_limit           — AIGuideThrottle triggers 429 after burst
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

GUIDE_URL = "/api/v1/ai/guide/"

# Patch target for the Anthropic client constructor inside guide_views
_ANTHROPIC_CLS = "apps.ai.guide_views.anthropic.Anthropic"
# Patch target for settings.ANTHROPIC_API_KEY (simpler than full settings mock)
_SETTINGS_KEY = "apps.ai.guide_views.settings"


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


def _mock_settings(mocker):
    """Patch settings so ANTHROPIC_API_KEY is non-empty."""
    mocker.patch(_SETTINGS_KEY + ".ANTHROPIC_API_KEY", "test-key", create=True)


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
def tenant_user(db):
    return User.objects.create_user(
        email="guide_tenant@test.klikk.co.za",
        password="T3stPass!",
        role=User.Role.TENANT,
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


@pytest.fixture
def tenant_client(tenant_user):
    c = APIClient()
    c.force_authenticate(user=tenant_user)
    return c


# ---------------------------------------------------------------------------
# Tests — original six (updated to patch settings key, not removed function)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@patch(_ANTHROPIC_CLS)
def test_valid_intent_returns_action(mock_anthropic_cls, agent_client, settings):
    """A recognised intent should return a non-null action with a route."""
    settings.ANTHROPIC_API_KEY = "test-key"
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _make_tool_use_response(
        "list_leases",
        text="Navigating to Leases.",
    )

    resp = agent_client.post(GUIDE_URL, {"message": "show me my leases"}, format="json")

    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] is not None
    assert data["action"]["route"] == "/leases"
    assert data["reply"]  # non-empty reply


@pytest.mark.django_db
@patch(_ANTHROPIC_CLS)
def test_unknown_intent_returns_null_action(mock_anthropic_cls, agent_client, settings):
    """When the model returns prose only (no tool), action must be null."""
    settings.ANTHROPIC_API_KEY = "test-key"
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _make_text_response(
        "I'm not sure what you mean. Could you clarify?"
    )

    resp = agent_client.post(GUIDE_URL, {"message": "xyzzy what is this"}, format="json")

    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] is None
    assert data["reply"]  # non-empty


@pytest.mark.django_db
@patch(_ANTHROPIC_CLS)
def test_role_scoped_action_blocked(mock_anthropic_cls, owner_client, settings):
    """An agent-only tool returned for an owner portal must be blocked."""
    settings.ANTHROPIC_API_KEY = "test-key"
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    # The model (mis-)returns an agent-only tool while we're in owner portal
    mock_client.messages.create.return_value = _make_tool_use_response("create_property")

    resp = owner_client.post(GUIDE_URL, {"message": "add a property"}, format="json")

    assert resp.status_code == 200
    data = resp.json()
    # Action must be blocked — not forwarded to the frontend
    assert data["action"] is None
    assert data["reply"]  # a refusal message


@pytest.mark.django_db
def test_unauthenticated_rejected():
    """Unauthenticated requests must receive 401."""
    client = APIClient()
    resp = client.post(GUIDE_URL, {"message": "go to leases"}, format="json")
    assert resp.status_code == 401


@pytest.mark.django_db
def test_missing_message_returns_400(agent_client):
    """Empty message should return 400."""
    resp = agent_client.post(GUIDE_URL, {"message": ""}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
@patch(_ANTHROPIC_CLS)
def test_guide_interaction_persisted(mock_anthropic_cls, agent_client, settings):
    """A valid request must persist a GuideInteraction row."""
    from apps.ai.models import GuideInteraction

    settings.ANTHROPIC_API_KEY = "test-key"
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _make_tool_use_response(
        "go_to_dashboard",
        text="Taking you to the Dashboard.",
    )

    initial_count = GuideInteraction.objects.count()
    agent_client.post(GUIDE_URL, {"message": "go home"}, format="json")
    assert GuideInteraction.objects.count() == initial_count + 1
    interaction = GuideInteraction.objects.latest("created_at")
    assert interaction.intent == "go_to_dashboard"
    assert interaction.completed is True


# ---------------------------------------------------------------------------
# Tests — new fixes (blockers 1–4)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_tenant_cannot_use_ai_guide_returns_403(tenant_client):
    """
    Blocker 1: a TENANT user must receive 403 regardless of any portal field
    they supply.  The portal is derived from user.role, not the request body.
    """
    resp = tenant_client.post(
        GUIDE_URL,
        {"message": "show me agent tools", "portal": "agent"},
        format="json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_tenant_portal_field_ignored_still_403(tenant_client):
    """
    Blocker 1: supplying no portal field at all must also yield 403 for a tenant.
    """
    resp = tenant_client.post(GUIDE_URL, {"message": "show me leases"}, format="json")
    assert resp.status_code == 403


@pytest.mark.django_db
@patch(_ANTHROPIC_CLS)
def test_agent_portal_derived_from_role(mock_anthropic_cls, agent_client, settings):
    """
    Blocker 1: an ESTATE_AGENT user gets the 'agent' portal even if they send
    portal='owner' in the body — portal comes from role, not payload.
    """
    settings.ANTHROPIC_API_KEY = "test-key"
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _make_tool_use_response(
        "go_to_dashboard", text="Going to dashboard."
    )

    resp = agent_client.post(
        GUIDE_URL,
        {"message": "go home", "portal": "owner"},  # payload portal must be ignored
        format="json",
    )
    assert resp.status_code == 200
    # Verify the GuideInteraction was stored with portal='agent', not 'owner'
    from apps.ai.models import GuideInteraction
    interaction = GuideInteraction.objects.latest("created_at")
    assert interaction.portal == "agent"


@pytest.mark.django_db
def test_oversized_message_returns_400(agent_client):
    """
    Blocker 2: messages longer than MESSAGE_MAX_LENGTH (2000) must return 400
    before reaching Anthropic.
    """
    oversized = "x" * 2001
    resp = agent_client.post(GUIDE_URL, {"message": oversized}, format="json")
    assert resp.status_code == 400
    assert "2000" in resp.json().get("detail", "")


@pytest.mark.django_db
def test_message_at_max_length_is_allowed(agent_client, settings):
    """
    Blocker 2: a message of exactly MESSAGE_MAX_LENGTH chars must not be rejected
    by the length guard (it will fail at Anthropic, but that's a different check).
    """
    from unittest.mock import patch, MagicMock
    exactly_max = "x" * 2000

    with patch(_ANTHROPIC_CLS) as mock_cls:
        settings.ANTHROPIC_API_KEY = "test-key"
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_text_response("ok")

        resp = agent_client.post(GUIDE_URL, {"message": exactly_max}, format="json")

    # Must not be rejected with 400 by our length guard
    assert resp.status_code != 400 or "2000" not in resp.json().get("detail", "")


@pytest.mark.django_db
def test_rate_limit_triggers_429(agent_user, settings):
    """
    Blocker 4: AIGuideThrottle must return 429 once the burst is exhausted.
    We override the cache to an in-memory one so the test is self-contained.
    """
    from unittest.mock import patch, MagicMock
    from django.test.utils import override_settings

    settings.ANTHROPIC_API_KEY = "test-key"

    # Force a very tight rate so we only need 2 requests to trip it.
    with override_settings(
        DEFAULT_THROTTLE_CLASSES=["rest_framework.throttling.UserRateThrottle"],
        DEFAULT_THROTTLE_RATES={"user": "1/min"},
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "throttle-test"}},
    ):
        with patch("apps.ai.guide_views.AIGuideThrottle.rate", "1/min"):
            with patch(_ANTHROPIC_CLS) as mock_cls:
                mock_client = MagicMock()
                mock_cls.return_value = mock_client
                mock_client.messages.create.return_value = _make_text_response("ok")

                c = APIClient()
                c.force_authenticate(user=agent_user)

                r1 = c.post(GUIDE_URL, {"message": "go home"}, format="json")
                r2 = c.post(GUIDE_URL, {"message": "go home"}, format="json")

    # First request passes (or hits Anthropic), second triggers throttle
    assert r1.status_code in (200, 503)  # 503 if no API key leaks through mock
    assert r2.status_code == 429
