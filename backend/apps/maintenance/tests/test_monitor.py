"""Tests for the Agent Monitor API endpoints."""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.maintenance.models import AgentTokenLog, MaintenanceSkill
from tests.base import TremlyAPITestCase


class AgentMonitorDashboardTests(TremlyAPITestCase):
    """Test the monitor dashboard endpoint."""

    def setUp(self):
        self.agent = self.create_agent()

    def test_unauthenticated_returns_401(self):
        resp = self.client.get(reverse("agent-monitor-dashboard"))
        self.assertEqual(resp.status_code, 401)

    def test_tenant_cannot_access(self):
        tenant = self.create_tenant()
        self.authenticate(tenant)
        resp = self.client.get(reverse("agent-monitor-dashboard"))
        self.assertEqual(resp.status_code, 403)

    def test_agent_can_access(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("agent-monitor-dashboard"))
        self.assertEqual(resp.status_code, 200)
        data = resp.data
        self.assertIn("rag", data)
        self.assertIn("mcp", data)
        self.assertIn("skills", data)
        self.assertIn("token_usage", data)
        self.assertIn("indexed_data", data)
        self.assertIn("agents", data)
        self.assertIn("system", data)

    def test_dashboard_rag_fields(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("agent-monitor-dashboard"))
        rag = resp.data["rag"]
        self.assertIn("status", rag)
        self.assertIn("contracts", rag)
        self.assertIn("agent_qa", rag)
        self.assertIn("chat_knowledge", rag)
        self.assertIn("embedding_model", rag)

    def test_dashboard_mcp_fields(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("agent-monitor-dashboard"))
        mcp = resp.data["mcp"]
        self.assertIn("tools", mcp)
        self.assertIn("resources", mcp)
        self.assertIn("tool_count", mcp)
        self.assertGreater(mcp["tool_count"], 0)

    def test_dashboard_skills_with_data(self):
        """Skills summary reflects actual database state."""
        MaintenanceSkill.objects.create(
            name="Test Skill", trade="plumbing", is_active=True,
        )
        self.authenticate(self.agent)
        resp = self.client.get(reverse("agent-monitor-dashboard"))
        skills = resp.data["skills"]
        self.assertGreaterEqual(skills["total_active"], 1)

    def test_dashboard_agents_list(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("agent-monitor-dashboard"))
        agents = resp.data["agents"]
        self.assertGreaterEqual(len(agents), 3)
        names = [a["name"] for a in agents]
        self.assertIn("Tenant AI Chat", names)
        self.assertIn("Agent Assist", names)


class AgentHealthCheckTests(TremlyAPITestCase):
    """Test the health check endpoint."""

    def setUp(self):
        self.agent = self.create_agent()

    def test_health_check_returns_checks(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("agent-monitor-health"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("overall", resp.data)
        self.assertIn("checks", resp.data)
        self.assertIsInstance(resp.data["checks"], list)
        self.assertGreater(len(resp.data["checks"]), 0)

    def test_health_check_includes_key_checks(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("agent-monitor-health"))
        check_names = [c["name"] for c in resp.data["checks"]]
        self.assertIn("Anthropic API Key", check_names)
        self.assertIn("MCP Server", check_names)

    def test_overall_status_values(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("agent-monitor-health"))
        self.assertIn(resp.data["overall"], ["healthy", "degraded", "unhealthy"])


class AgentTokenLogTests(TremlyAPITestCase):
    """Test token logging model and API."""

    def setUp(self):
        self.agent = self.create_agent()

    def test_token_log_creation(self):
        """Verify AgentTokenLog.log_call creates a record."""
        # Simulate an Anthropic-like response object
        class MockUsage:
            input_tokens = 1500
            output_tokens = 300

        class MockResponse:
            usage = MockUsage()
            model = "claude-sonnet-4-6"

        AgentTokenLog.log_call(
            endpoint="test_endpoint",
            response=MockResponse(),
            user=self.agent,
            latency_ms=250,
            metadata={"test": True},
        )
        log = AgentTokenLog.objects.latest("created_at")
        self.assertEqual(log.endpoint, "test_endpoint")
        self.assertEqual(log.input_tokens, 1500)
        self.assertEqual(log.output_tokens, 300)
        self.assertEqual(log.latency_ms, 250)
        self.assertEqual(log.user, self.agent)
        self.assertEqual(log.model, "claude-sonnet-4-6")

    def test_token_log_view(self):
        """Token log API returns recent entries."""
        AgentTokenLog.objects.create(
            endpoint="agent_assist",
            model="claude-sonnet-4-6",
            input_tokens=2000,
            output_tokens=500,
            latency_ms=400,
        )
        self.authenticate(self.agent)
        resp = self.client.get(reverse("agent-monitor-tokens"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("logs", resp.data)
        self.assertGreaterEqual(len(resp.data["logs"]), 1)

    def test_token_log_filter_by_endpoint(self):
        AgentTokenLog.objects.create(endpoint="tenant_chat", input_tokens=100, output_tokens=50)
        AgentTokenLog.objects.create(endpoint="agent_assist", input_tokens=200, output_tokens=80)
        self.authenticate(self.agent)
        resp = self.client.get(reverse("agent-monitor-tokens"), {"endpoint": "tenant_chat"})
        self.assertEqual(resp.status_code, 200)
        for log in resp.data["logs"]:
            self.assertEqual(log["endpoint"], "tenant_chat")

    def test_token_log_filter_by_min_input(self):
        AgentTokenLog.objects.create(endpoint="test", input_tokens=100, output_tokens=50)
        AgentTokenLog.objects.create(endpoint="test", input_tokens=60000, output_tokens=500)
        self.authenticate(self.agent)
        resp = self.client.get(reverse("agent-monitor-tokens"), {"min_input": "50000"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["logs"]), 1)
        self.assertGreaterEqual(resp.data["logs"][0]["input_tokens"], 50000)

    def test_token_log_graceful_on_missing_usage(self):
        """log_call handles responses without .usage gracefully."""
        class NoUsageResponse:
            model = "unknown"

        AgentTokenLog.log_call(endpoint="no_usage", response=NoUsageResponse())
        log = AgentTokenLog.objects.filter(endpoint="no_usage").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.input_tokens, 0)
        self.assertEqual(log.output_tokens, 0)


class ProgressiveTestTests(TremlyAPITestCase):
    """Test progressive test execution and history."""

    def setUp(self):
        self.agent = self.create_agent()

    def test_get_history_empty(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("agent-monitor-tests"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("runs", resp.data)

    def test_run_level_1_test(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("agent-monitor-tests"),
            {"level": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("score", resp.data)
        self.assertIn("tests", resp.data)
        self.assertEqual(resp.data["level"], 1)
        self.assertGreater(len(resp.data["tests"]), 0)

    def test_progressive_comparison(self):
        """Second run should include comparison with first."""
        self.authenticate(self.agent)
        # Run 1
        self.client.post(reverse("agent-monitor-tests"), {"level": 1}, format="json")
        # Run 2
        resp = self.client.post(reverse("agent-monitor-tests"), {"level": 1}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.data.get("comparison"))
        self.assertIn("improvement", resp.data["comparison"])

    def test_level_clamped(self):
        """Level should be clamped between 1 and 5."""
        self.authenticate(self.agent)
        resp = self.client.post(reverse("agent-monitor-tests"), {"level": 99}, format="json")
        self.assertEqual(resp.data["level"], 5)

        resp = self.client.post(reverse("agent-monitor-tests"), {"level": -5}, format="json")
        self.assertEqual(resp.data["level"], 1)
