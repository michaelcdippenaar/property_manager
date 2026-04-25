"""
Tests for the AI knowledge loader and save endpoint.

pytest apps/ai/tests/test_knowledge.py

Scenarios
---------
1. load_happy_path             — get_knowledge() returns file content
2. cache_ttl_respected         — second call within TTL does not re-read disk
3. bust_cache_forces_reload    — bust_cache() makes next call re-read disk
4. save_knowledge_busts_cache  — save_knowledge() writes file and busts cache
5. endpoint_get_returns_content— GET /api/v1/ai/knowledge/ returns content
6. endpoint_save_200           — POST /api/v1/ai/knowledge/ with content → 200
7. endpoint_save_busts_cache   — POST wipes the in-process cache
8. endpoint_403_non_admin      — non-admin gets 403
9. endpoint_401_unauthenticated— unauthenticated gets 401
10. knowledge_injected_in_prompt— knowledge content appears in string passed to Anthropic
11. add_tenant_query_hints_lease— knowledge mentioning "lease creation" is in system prompt
    for "add tenant" query
"""
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

KNOWLEDGE_URL = "/api/v1/ai/knowledge/"

_ANTHROPIC_CLS = "apps.ai.guide_views.anthropic.Anthropic"
GUIDE_URL = "/api/v1/ai/guide/"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="ai_knowledge_admin@test.klikk.co.za",
        password="T3stPass!",
        role=User.Role.ADMIN,
    )


@pytest.fixture
def agent_user(db):
    return User.objects.create_user(
        email="ai_knowledge_agent@test.klikk.co.za",
        password="T3stPass!",
        role=User.Role.ESTATE_AGENT,
    )


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(user=admin_user)
    return c


@pytest.fixture
def agent_client(agent_user):
    c = APIClient()
    c.force_authenticate(user=agent_user)
    return c


@pytest.fixture(autouse=True)
def reset_knowledge_cache():
    """Bust the in-process cache before every test to prevent cross-test contamination."""
    from apps.ai.knowledge import bust_cache
    bust_cache()
    yield
    bust_cache()


# ---------------------------------------------------------------------------
# Unit tests — knowledge loader
# ---------------------------------------------------------------------------

def test_load_happy_path(tmp_path):
    """get_knowledge() returns the file contents when the file exists."""
    from apps.ai import knowledge as km

    fake_file = tmp_path / "knowledge.md"
    fake_file.write_text("# Test Knowledge\nSome domain rule.", encoding="utf-8")

    with patch.object(km, "_KNOWLEDGE_FILE", fake_file):
        km.bust_cache()
        result = km.get_knowledge()

    assert "Test Knowledge" in result
    assert "Some domain rule." in result


def test_load_missing_file_returns_empty(tmp_path):
    """get_knowledge() returns '' when the file is missing."""
    from apps.ai import knowledge as km

    missing = tmp_path / "nonexistent.md"

    with patch.object(km, "_KNOWLEDGE_FILE", missing):
        km.bust_cache()
        result = km.get_knowledge()

    assert result == ""


def test_cache_ttl_respected(tmp_path):
    """Second call within TTL does not re-read the file."""
    from apps.ai import knowledge as km

    fake_file = tmp_path / "knowledge.md"
    fake_file.write_text("original", encoding="utf-8")

    with patch.object(km, "_KNOWLEDGE_FILE", fake_file):
        km.bust_cache()
        first = km.get_knowledge()  # reads from disk
        # Overwrite the file on disk — cache should shield the old value
        fake_file.write_text("updated", encoding="utf-8")
        second = km.get_knowledge()  # should still return cached "original"

    assert first == "original"
    assert second == "original"  # cache was not busted


def test_bust_cache_forces_reload(tmp_path):
    """bust_cache() makes the next call read fresh content from disk."""
    from apps.ai import knowledge as km

    fake_file = tmp_path / "knowledge.md"
    fake_file.write_text("original", encoding="utf-8")

    with patch.object(km, "_KNOWLEDGE_FILE", fake_file):
        km.bust_cache()
        km.get_knowledge()  # primes cache
        fake_file.write_text("updated", encoding="utf-8")
        km.bust_cache()
        result = km.get_knowledge()

    assert result == "updated"


def test_save_knowledge_writes_and_busts(tmp_path):
    """save_knowledge() writes the new content and immediately busts the cache."""
    from apps.ai import knowledge as km

    fake_file = tmp_path / "knowledge.md"
    fake_file.write_text("old content", encoding="utf-8")

    with patch.object(km, "_KNOWLEDGE_FILE", fake_file):
        km.bust_cache()
        km.get_knowledge()  # primes cache with "old content"
        km.save_knowledge("new content")
        result = km.get_knowledge()

    assert fake_file.read_text(encoding="utf-8") == "new content"
    assert result == "new content"


# ---------------------------------------------------------------------------
# HTTP endpoint tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_endpoint_get_returns_content(admin_client, tmp_path):
    """GET /api/v1/ai/knowledge/ returns the current knowledge content."""
    from apps.ai import knowledge as km

    fake_file = tmp_path / "knowledge.md"
    fake_file.write_text("# Domain Rules\nRule one.", encoding="utf-8")

    with patch.object(km, "_KNOWLEDGE_FILE", fake_file):
        km.bust_cache()
        resp = admin_client.get(KNOWLEDGE_URL)

    assert resp.status_code == 200
    data = resp.json()
    assert "content" in data
    assert "Domain Rules" in data["content"]


@pytest.mark.django_db
def test_endpoint_save_returns_200(admin_client, tmp_path):
    """POST /api/v1/ai/knowledge/ with valid content returns 200."""
    from apps.ai import knowledge as km

    fake_file = tmp_path / "knowledge.md"
    fake_file.write_text("old", encoding="utf-8")

    with patch.object(km, "_KNOWLEDGE_FILE", fake_file):
        km.bust_cache()
        resp = admin_client.post(
            KNOWLEDGE_URL,
            {"content": "# New Rules\nNew domain rule."},
            format="json",
        )

    assert resp.status_code == 200
    assert "saved_at" in resp.json()


@pytest.mark.django_db
def test_endpoint_save_busts_cache(admin_client, tmp_path):
    """POST writes to disk and the cache is busted so next GET sees the new content."""
    from apps.ai import knowledge as km

    fake_file = tmp_path / "knowledge.md"
    fake_file.write_text("old content", encoding="utf-8")

    with patch.object(km, "_KNOWLEDGE_FILE", fake_file):
        km.bust_cache()
        # prime the cache with old content
        km.get_knowledge()

        admin_client.post(
            KNOWLEDGE_URL,
            {"content": "fresh content"},
            format="json",
        )

        result = km.get_knowledge()

    assert result == "fresh content"


@pytest.mark.django_db
def test_endpoint_logs_audit_event(admin_client, tmp_path):
    """POST creates an AuditEvent with action 'ai.knowledge.updated'."""
    from apps.ai import knowledge as km
    from apps.audit.models import AuditEvent

    fake_file = tmp_path / "knowledge.md"
    fake_file.write_text("old", encoding="utf-8")

    before_count = AuditEvent.objects.filter(action="ai.knowledge.updated").count()

    with patch.object(km, "_KNOWLEDGE_FILE", fake_file):
        km.bust_cache()
        admin_client.post(
            KNOWLEDGE_URL,
            {"content": "new content"},
            format="json",
        )

    after_count = AuditEvent.objects.filter(action="ai.knowledge.updated").count()
    assert after_count == before_count + 1

    event = AuditEvent.objects.filter(action="ai.knowledge.updated").latest("timestamp")
    assert event.after_snapshot["content"] == "new content"
    assert event.before_snapshot["content"] == "old"


@pytest.mark.django_db
def test_endpoint_403_non_admin(agent_client):
    """Non-admin user receives 403 on both GET and POST."""
    get_resp = agent_client.get(KNOWLEDGE_URL)
    post_resp = agent_client.post(
        KNOWLEDGE_URL, {"content": "hack"}, format="json"
    )
    assert get_resp.status_code == 403
    assert post_resp.status_code == 403


@pytest.mark.django_db
def test_endpoint_401_unauthenticated():
    """Unauthenticated requests receive 401."""
    c = APIClient()
    assert c.get(KNOWLEDGE_URL).status_code == 401
    assert c.post(KNOWLEDGE_URL, {"content": "x"}, format="json").status_code == 401


@pytest.mark.django_db
def test_endpoint_400_missing_content(admin_client):
    """POST without 'content' returns 400."""
    resp = admin_client.post(KNOWLEDGE_URL, {}, format="json")
    assert resp.status_code == 400
    assert "content" in resp.json().get("detail", "").lower()


# ---------------------------------------------------------------------------
# Integration: knowledge injected into guide system prompt
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@patch(_ANTHROPIC_CLS)
def test_knowledge_appears_in_system_prompt(mock_anthropic_cls, agent_client, tmp_path, settings):
    """The knowledge content appears in the system prompt sent to Anthropic."""
    from apps.ai import knowledge as km

    settings.ANTHROPIC_API_KEY = "test-key"

    fake_file = tmp_path / "knowledge.md"
    fake_file.write_text("Tenants are created via lease creation.", encoding="utf-8")

    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    txt_block = MagicMock()
    txt_block.type = "text"
    txt_block.text = "You should create a lease to add a tenant."
    response = MagicMock()
    response.content = [txt_block]
    mock_client.messages.create.return_value = response

    with patch.object(km, "_KNOWLEDGE_FILE", fake_file):
        km.bust_cache()
        agent_client.post(GUIDE_URL, {"message": "add tenant"}, format="json")

    # Inspect the system kwarg passed to messages.create
    assert mock_client.messages.create.called
    call_kwargs = mock_client.messages.create.call_args
    system_prompt = call_kwargs.kwargs.get("system") or call_kwargs[1].get("system", "")
    assert "Klikk Domain Rules" in system_prompt
    assert "Tenants are created via lease creation." in system_prompt


@pytest.mark.django_db
@patch(_ANTHROPIC_CLS)
def test_add_tenant_query_knowledge_in_prompt(mock_anthropic_cls, agent_client, tmp_path, settings):
    """
    With knowledge mentioning 'lease creation', the system prompt sent for an
    'add tenant' query must contain 'lease' — confirming the knowledge was injected.

    This is a unit-level check: we verify the *prompt* contains the hint rather
    than mocking a full Anthropic reasoning chain.
    """
    from apps.ai import knowledge as km

    settings.ANTHROPIC_API_KEY = "test-key"

    fake_file = tmp_path / "knowledge.md"
    fake_file.write_text(
        "Tenants are created via lease creation — no standalone Add Tenant flow.",
        encoding="utf-8",
    )

    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    txt_block = MagicMock()
    txt_block.type = "text"
    txt_block.text = "To add a tenant, please create a lease."
    response = MagicMock()
    response.content = [txt_block]
    mock_client.messages.create.return_value = response

    with patch.object(km, "_KNOWLEDGE_FILE", fake_file):
        km.bust_cache()
        resp = agent_client.post(GUIDE_URL, {"message": "add tenant"}, format="json")

    assert resp.status_code == 200

    call_kwargs = mock_client.messages.create.call_args
    system_prompt = call_kwargs.kwargs.get("system") or call_kwargs[1].get("system", "")

    # The injected knowledge must be present in the prompt
    assert "lease creation" in system_prompt
    # And the model's reply (mocked) must mention lease
    assert "lease" in resp.json()["reply"].lower()
