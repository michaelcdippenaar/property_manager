"""
Regression tests: AgentHealthCheckView RBAC restriction.

RNT-SEC-038 — non-admin agents must receive 403; admin receives full detail.

Leak fixed: `settings.RAG_EMBEDDING_MODEL`, `settings.MAINTENANCE_CHAT_LOG`,
MCP server file path, and API key presence were previously visible to any
IsAgentOrAdmin caller.  The view now requires IsAdmin.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User


HEALTH_URL = "/api/v1/maintenance/monitor/health/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(role: str, email: str) -> User:
    return User.objects.create_user(
        email=email,
        password="testpass123",
        role=role,
    )


def _client_for(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def admin(db):
    return _make_user(User.Role.ADMIN, "admin-health@test.com")


@pytest.fixture()
def estate_agent(db):
    return _make_user(User.Role.ESTATE_AGENT, "estate-health@test.com")


@pytest.fixture()
def agency_admin(db):
    return _make_user(User.Role.AGENCY_ADMIN, "agencyadmin-health@test.com")


# ---------------------------------------------------------------------------
# Mocks — prevent live IO calls to RAG, model, filesystem
# ---------------------------------------------------------------------------

def _patch_health_deps():
    """Context-manager stack that stubs out all IO inside AgentHealthCheckView."""
    return [
        patch("apps.maintenance.monitor_views.rag_collection_stats", return_value={"chunks": 42}),
        patch("core.contract_rag.get_embedding_function", return_value=object()),
        patch("apps.maintenance.models.MaintenanceSkill.objects"),
    ]


# ---------------------------------------------------------------------------
# Non-admin: expect 403
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestNonAdminHealthCheckForbidden:

    def _assert_403(self, user: User):
        client = _client_for(user)
        response = client.get(HEALTH_URL)
        assert response.status_code == 403, (
            f"Expected 403 for role={user.role}, got {response.status_code}"
        )

    def test_estate_agent_gets_403(self, estate_agent):
        self._assert_403(estate_agent)

    def test_agency_admin_gets_403(self, agency_admin):
        self._assert_403(agency_admin)

    def test_unauthenticated_gets_401_or_403(self, db):
        client = APIClient()
        response = client.get(HEALTH_URL)
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Admin: expect 200 with full payload
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAdminHealthCheckFullDetail:

    def test_admin_receives_200_with_checks(self, admin, settings):
        settings.RAG_EMBEDDING_MODEL = "test-embedding-model"
        settings.MAINTENANCE_CHAT_LOG = "/tmp/test_chat.jsonl"
        settings.ANTHROPIC_API_KEY = "sk-test-key"

        client = _client_for(admin)

        with patch(
            "apps.maintenance.monitor_views.rag_collection_stats",
            return_value={"chunks": 5},
        ), patch(
            "core.contract_rag.get_embedding_function",
            return_value=object(),
        ):
            response = client.get(HEALTH_URL)

        assert response.status_code == 200
        data = response.json()
        assert "overall" in data
        assert "checks" in data
        assert isinstance(data["checks"], list)
        assert len(data["checks"]) > 0

    def test_admin_response_contains_embedding_model_detail(self, admin, settings):
        """Embedding model name must appear in the checks for admin."""
        settings.RAG_EMBEDDING_MODEL = "nomic-embed-text"
        settings.MAINTENANCE_CHAT_LOG = "/tmp/test_chat.jsonl"
        settings.ANTHROPIC_API_KEY = "sk-ant-test"

        client = _client_for(admin)

        with patch(
            "apps.maintenance.monitor_views.rag_collection_stats",
            return_value={"chunks": 1},
        ), patch(
            "core.contract_rag.get_embedding_function",
            return_value=object(),
        ):
            response = client.get(HEALTH_URL)

        assert response.status_code == 200
        checks = response.json()["checks"]
        embedding_check = next(
            (c for c in checks if "Embedding" in c.get("name", "")), None
        )
        assert embedding_check is not None
        # Admin must see the model name in the detail field
        assert "nomic-embed-text" in embedding_check.get("detail", "")
