"""
Badge count consistency tests for MaintenanceBadgesView.

Verifies that ``GET /maintenance/badges/`` returns ``open_issues`` counts
that exactly match what ``GET /maintenance/`` returns for the same
user/agency scope, across a mix of statuses and soft-deletes.

Test cases:
  - Admin sees all open+in_progress requests globally.
  - Agent sees only open+in_progress for their assigned properties.
  - Agent's badge count == count of items in their scoped list view.
  - Closed and resolved requests are excluded from the badge count.
  - Requests for other agents' properties do NOT bleed into the badge.
  - Tenant badge shows 0 pending_questions (tenants are not agents).
"""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.maintenance.models import AgentQuestion, MaintenanceRequest
from apps.properties.models import PropertyAgentAssignment
from apps.test_hub.base.test_case import TremlyAPITestCase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _client_for(user) -> APIClient:
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture()
def f(db):
    """Return a fresh TremlyAPITestCase instance (factory only, no transactions)."""
    return TremlyAPITestCase()


# ---------------------------------------------------------------------------
# Badge count == list count
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBadgeCountMatchesListCount:
    """
    Core assertion: badge open_issues == len(list items with active status)
    for the same authenticated user, across several role/scope combinations.
    """

    def _badge_count(self, user) -> int:
        client = _client_for(user)
        resp = client.get("/api/v1/maintenance/badges/", HTTP_ACCEPT="application/json")
        assert resp.status_code == 200, resp.content
        return resp.json()["open_issues"]

    def _list_count(self, user, status_filter: str | None = None) -> int:
        client = _client_for(user)
        params = {}
        if status_filter:
            params["status"] = status_filter
        else:
            params["exclude_status"] = "closed"
        resp = client.get("/api/v1/maintenance/", params, HTTP_ACCEPT="application/json")
        assert resp.status_code == 200, resp.content
        data = resp.json()
        items = data.get("results", data) if isinstance(data, dict) else data
        return len(items)

    def test_admin_badge_matches_list(self, f):
        """Admin badge count == total open+in_progress across all properties."""
        admin = f.create_admin(email="admin-badge@test.com")

        prop = f.create_property()
        unit = f.create_unit(property_obj=prop)

        f.create_maintenance_request(unit=unit, status="open")
        f.create_maintenance_request(unit=unit, status="in_progress")
        f.create_maintenance_request(unit=unit, status="resolved")   # should NOT count
        f.create_maintenance_request(unit=unit, status="closed")     # should NOT count

        badge = self._badge_count(admin)
        # Admin badge should be exactly 2 (open + in_progress)
        assert badge == 2

    def test_agent_badge_only_sees_own_properties(self, f):
        """Agent badge must not include requests from another agent's properties."""
        agent_a = f.create_agent(email="agent-a-badge@test.com")
        agent_b = f.create_agent(email="agent-b-badge@test.com")

        prop_a = f.create_property(agent=agent_a, name="Prop A")
        prop_b = f.create_property(agent=agent_b, name="Prop B")

        unit_a = f.create_unit(property_obj=prop_a)
        unit_b = f.create_unit(property_obj=prop_b)

        # 2 open issues on agent_a's property
        f.create_maintenance_request(unit=unit_a, status="open")
        f.create_maintenance_request(unit=unit_a, status="in_progress")

        # 3 open issues on agent_b's property — must NOT show in agent_a's badge
        f.create_maintenance_request(unit=unit_b, status="open")
        f.create_maintenance_request(unit=unit_b, status="open")
        f.create_maintenance_request(unit=unit_b, status="open")

        badge_a = self._badge_count(agent_a)
        assert badge_a == 2, (
            f"Expected 2 (agent_a's own issues), got {badge_a}. "
            "Badge is leaking other agents' requests."
        )

    def test_badge_count_equals_active_list_count_for_agent(self, f):
        """
        For an agent user: badges.open_issues == count of status=open|in_progress
        in the list endpoint with the same user auth.
        """
        agent = f.create_agent(email="agent-list-badge@test.com")
        prop = f.create_property(agent=agent, name="Agent List Prop")
        unit = f.create_unit(property_obj=prop)

        f.create_maintenance_request(unit=unit, status="open")
        f.create_maintenance_request(unit=unit, status="in_progress")
        f.create_maintenance_request(unit=unit, status="resolved")

        badge = self._badge_count(agent)

        # Count list items that are open or in_progress
        client = _client_for(agent)
        resp_open = client.get(
            "/api/v1/maintenance/", {"status": "open"}, HTTP_ACCEPT="application/json"
        )
        resp_ip = client.get(
            "/api/v1/maintenance/", {"status": "in_progress"}, HTTP_ACCEPT="application/json"
        )
        assert resp_open.status_code == 200
        assert resp_ip.status_code == 200

        open_items = resp_open.json().get("results", resp_open.json())
        ip_items = resp_ip.json().get("results", resp_ip.json())
        list_active_count = len(open_items) + len(ip_items)

        assert badge == list_active_count, (
            f"Badge ({badge}) != list active count ({list_active_count}). "
            "Scoping mismatch between badge and list endpoints."
        )

    def test_closed_and_resolved_excluded_from_badge(self, f):
        """Closed and resolved requests must not contribute to open_issues badge."""
        admin = f.create_admin(email="admin-closed-badge@test.com")
        prop = f.create_property()
        unit = f.create_unit(property_obj=prop)

        f.create_maintenance_request(unit=unit, status="closed")
        f.create_maintenance_request(unit=unit, status="resolved")

        badge = self._badge_count(admin)
        assert badge == 0, f"Expected 0 (all closed/resolved), got {badge}."

    def test_mixed_statuses_open_count_correct(self, f):
        """Mix of all four statuses: badge counts only open + in_progress."""
        admin = f.create_admin(email="admin-mix-badge@test.com")
        prop = f.create_property()
        unit = f.create_unit(property_obj=prop)

        f.create_maintenance_request(unit=unit, status="open")
        f.create_maintenance_request(unit=unit, status="open")
        f.create_maintenance_request(unit=unit, status="in_progress")
        f.create_maintenance_request(unit=unit, status="resolved")
        f.create_maintenance_request(unit=unit, status="closed")

        badge = self._badge_count(admin)
        assert badge == 3, f"Expected 3 (2 open + 1 in_progress), got {badge}."


# ---------------------------------------------------------------------------
# AgentQuestion pending_questions scoping
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPendingQuestionsBadgeScoping:
    """pending_questions badge is scoped to accessible properties for agents."""

    def _badge(self, user) -> dict:
        client = _client_for(user)
        resp = client.get("/api/v1/maintenance/badges/", HTTP_ACCEPT="application/json")
        assert resp.status_code == 200, resp.content
        return resp.json()

    def test_admin_sees_all_pending_questions(self, f):
        admin = f.create_admin(email="admin-q-badge@test.com")
        prop = f.create_property()
        AgentQuestion.objects.create(
            question="What is the levy?",
            property=prop,
            status=AgentQuestion.Status.PENDING,
        )
        AgentQuestion.objects.create(
            question="Who fixes the geyser?",
            status=AgentQuestion.Status.PENDING,
        )
        badge = self._badge(admin)
        assert badge["pending_questions"] == 2

    def test_tenant_sees_zero_pending_questions(self, f):
        """Tenants are not agents — pending_questions should be 0."""
        tenant = f.create_tenant(email="tenant-q-badge@test.com")
        AgentQuestion.objects.create(
            question="Random question",
            status=AgentQuestion.Status.PENDING,
        )
        badge = self._badge(tenant)
        assert badge["pending_questions"] == 0

    def test_answered_questions_not_counted(self, f):
        admin = f.create_admin(email="admin-answered-badge@test.com")
        AgentQuestion.objects.create(
            question="Already answered",
            status=AgentQuestion.Status.ANSWERED,
        )
        badge = self._badge(admin)
        assert badge["pending_questions"] == 0
