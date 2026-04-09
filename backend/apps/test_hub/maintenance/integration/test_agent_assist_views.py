"""
Integration tests for the agent-assist AI endpoints.

Source file under test: apps/maintenance/agent_assist_views.py
  - AgentAssistRagStatusView → GET  /api/v1/maintenance/agent-assist/rag-status/
  - AgentAssistChatView      → POST /api/v1/maintenance/agent-assist/chat/

Covers:
  - Auth / permission gates (401 unauth, 403 tenant)
  - RAG status endpoint stats shape
  - Chat happy path (Claude mocked) returns parsed reply + RAG flags
  - Missing message → 400
  - Missing ANTHROPIC_API_KEY → 503
  - Claude APIError → 502
  - Empty model reply → 502
  - maintenance_request_id injection pulls context + category filter
  - Conversation history is forwarded to Claude
  - AgentTokenLog row is created on success

All Claude and RAG calls are mocked — no real API traffic, no Chroma.
"""
from unittest import mock

import pytest
from django.test import override_settings
from django.urls import reverse

from apps.maintenance.models import AgentTokenLog, MaintenanceSkill
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


CHAT_URL = reverse("agent-assist-chat")
STATUS_URL = reverse("agent-assist-rag-status")


def _fake_claude_reply(text: str, input_tokens: int = 100, output_tokens: int = 50):
    """Build a minimal fake anthropic SDK response."""
    block = mock.MagicMock()
    block.type = "text"
    block.text = text
    resp = mock.MagicMock()
    resp.content = [block]
    resp.usage = mock.MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)
    resp.model = "claude-sonnet-4-6"
    return resp


# ─────────────────────────────────────────────────────────────────────────────
# AgentAssistRagStatusView
# ─────────────────────────────────────────────────────────────────────────────
class AgentAssistRagStatusViewTests(TremlyAPITestCase):
    def test_unauthenticated_returns_401(self):
        resp = self.client.get(STATUS_URL)
        self.assertEqual(resp.status_code, 401)

    def test_tenant_is_forbidden(self):
        self.authenticate(self.create_tenant(email="tenant@rag.test"))
        resp = self.client.get(STATUS_URL)
        self.assertEqual(resp.status_code, 403)

    def test_agent_sees_stats(self):
        self.authenticate(self.create_agent(email="agent@rag.test"))
        fake_stats = {
            "contracts_chunks": 42,
            "agent_qa_chunks": 5,
            "chat_knowledge_chunks": 0,
            "embedding_model": "text-embedding-3-small",
        }
        with mock.patch(
            "apps.maintenance.agent_assist_views.rag_collection_stats",
            return_value=fake_stats,
        ), mock.patch(
            "apps.maintenance.agent_assist_views.anthropic_web_fetch_enabled",
            return_value=True,
        ):
            resp = self.client.get(STATUS_URL)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["contracts_chunks"], 42)
        self.assertEqual(resp.data["agent_qa_chunks"], 5)
        self.assertEqual(resp.data["embedding_model"], "text-embedding-3-small")
        self.assertTrue(resp.data["web_fetch_enabled"])
        self.assertIn("documents_root", resp.data)


# ─────────────────────────────────────────────────────────────────────────────
# AgentAssistChatView
# ─────────────────────────────────────────────────────────────────────────────
@override_settings(ANTHROPIC_API_KEY="test-key-sk-fake")
class AgentAssistChatViewTests(TremlyAPITestCase):
    """Chat endpoint — Claude + RAG fully mocked."""

    def setUp(self):
        self.agent = self.create_agent(email="agent@chat.test")
        self.authenticate(self.agent)
        # Shared RAG/web-fetch patches so individual tests stay small.
        self._rag_patches = []
        for path, value in [
            ("apps.maintenance.agent_assist_views.query_contracts", "[excerpt] some rental clause"),
            ("apps.maintenance.agent_assist_views.query_agent_qa", ""),
            ("apps.maintenance.agent_assist_views.query_maintenance_issues", ""),
            ("apps.maintenance.agent_assist_views.build_web_fetch_tools", None),
        ]:
            p = mock.patch(path, return_value=value)
            p.start()
            self._rag_patches.append(p)

    def tearDown(self):
        for p in self._rag_patches:
            p.stop()

    # ── Auth / permission ──

    def test_unauthenticated_returns_401(self):
        self.client.force_authenticate(user=None)
        resp = self.client.post(CHAT_URL, {"message": "hi"}, format="json")
        self.assertEqual(resp.status_code, 401)

    def test_tenant_is_forbidden(self):
        self.client.force_authenticate(user=None)
        self.authenticate(self.create_tenant(email="tenant@chat.test"))
        resp = self.client.post(CHAT_URL, {"message": "hi"}, format="json")
        self.assertEqual(resp.status_code, 403)

    # ── Input validation ──

    def test_missing_message_returns_400(self):
        resp = self.client.post(CHAT_URL, {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("message is required", resp.data["error"])

    def test_blank_message_returns_400(self):
        resp = self.client.post(CHAT_URL, {"message": "   "}, format="json")
        self.assertEqual(resp.status_code, 400)

    # ── Configuration ──

    def test_missing_api_key_returns_503(self):
        with mock.patch(
            "apps.maintenance.agent_assist_views._get_anthropic_api_key",
            return_value="",
        ):
            resp = self.client.post(CHAT_URL, {"message": "hi"}, format="json")
        self.assertEqual(resp.status_code, 503)
        self.assertIn("ANTHROPIC_API_KEY", resp.data["error"])

    # ── Claude failure modes ──

    def test_claude_error_returns_502(self):
        with mock.patch(
            "apps.maintenance.agent_assist_views.anthropic.Anthropic"
        ) as client_cls:
            client = client_cls.return_value
            client.messages.create.side_effect = RuntimeError("server on fire")
            resp = self.client.post(CHAT_URL, {"message": "hi"}, format="json")

        self.assertEqual(resp.status_code, 502)
        self.assertIn("AI error", resp.data["error"])

    def test_empty_reply_returns_502(self):
        with mock.patch(
            "apps.maintenance.agent_assist_views.anthropic.Anthropic"
        ) as client_cls:
            client_cls.return_value.messages.create.return_value = _fake_claude_reply("")
            resp = self.client.post(CHAT_URL, {"message": "hi"}, format="json")

        self.assertEqual(resp.status_code, 502)
        self.assertIn("Empty", resp.data["error"])

    # ── Happy paths ──

    def test_happy_path_returns_reply_and_flags(self):
        with mock.patch(
            "apps.maintenance.agent_assist_views.anthropic.Anthropic"
        ) as client_cls:
            client_cls.return_value.messages.create.return_value = _fake_claude_reply(
                "Here's what the lease says about pets."
            )
            resp = self.client.post(
                CHAT_URL, {"message": "are pets allowed?"}, format="json"
            )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["reply"], "Here's what the lease says about pets.")
        self.assertTrue(resp.data["rag_populated"])
        self.assertFalse(resp.data["qa_populated"])  # patched to ""
        self.assertFalse(resp.data["web_fetch_enabled"])  # patched to None

    def test_history_is_forwarded_to_claude(self):
        history = [
            {"role": "user", "content": "What's the notice period?"},
            {"role": "assistant", "content": "Typically 2 months."},
            {"role": "invalid-role", "content": "should be skipped"},
        ]
        with mock.patch(
            "apps.maintenance.agent_assist_views.anthropic.Anthropic"
        ) as client_cls:
            client_cls.return_value.messages.create.return_value = _fake_claude_reply("ok")
            resp = self.client.post(
                CHAT_URL,
                {"message": "And for leases under 6 months?", "history": history},
                format="json",
            )

        self.assertEqual(resp.status_code, 200)
        kwargs = client_cls.return_value.messages.create.call_args.kwargs
        sent_msgs = kwargs["messages"]
        # 2 valid history items + current message = 3
        self.assertEqual(len(sent_msgs), 3)
        self.assertEqual(sent_msgs[0]["content"], "What's the notice period?")
        self.assertEqual(sent_msgs[-1]["content"], "And for leases under 6 months?")

    def test_web_fetch_tool_wired_when_enabled(self):
        """When build_web_fetch_tools returns a non-empty list, kwargs must
        include it and max_tokens bumps to 3072."""
        # Re-patch build_web_fetch_tools to return a tool
        for p in self._rag_patches:
            p.stop()
        self._rag_patches = []
        patches = [
            ("apps.maintenance.agent_assist_views.query_contracts", "excerpt"),
            ("apps.maintenance.agent_assist_views.query_agent_qa", ""),
            ("apps.maintenance.agent_assist_views.query_maintenance_issues", ""),
            (
                "apps.maintenance.agent_assist_views.build_web_fetch_tools",
                [{"type": "web_fetch_20250618", "name": "web_fetch"}],
            ),
        ]
        for path, value in patches:
            p = mock.patch(path, return_value=value)
            p.start()
            self._rag_patches.append(p)

        with mock.patch(
            "apps.maintenance.agent_assist_views.anthropic.Anthropic"
        ) as client_cls:
            client_cls.return_value.messages.create.return_value = _fake_claude_reply("ok")
            resp = self.client.post(CHAT_URL, {"message": "hi"}, format="json")

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["web_fetch_enabled"])
        kwargs = client_cls.return_value.messages.create.call_args.kwargs
        self.assertIn("tools", kwargs)
        self.assertEqual(kwargs["max_tokens"], 3072)

    def test_maintenance_request_context_is_injected(self):
        """When maintenance_request_id is present, the request info and chat
        activities must end up in the system prompt."""
        unit = self.create_unit()
        tenant = self.create_tenant(email="reporter@chat.test")
        req = self.create_maintenance_request(
            unit=unit,
            tenant=tenant,
            title="Kitchen tap leaking",
            category="plumbing",
        )

        with mock.patch(
            "apps.maintenance.agent_assist_views.anthropic.Anthropic"
        ) as client_cls:
            client_cls.return_value.messages.create.return_value = _fake_claude_reply("ok")
            resp = self.client.post(
                CHAT_URL,
                {
                    "message": "What should I do?",
                    "maintenance_request_id": req.pk,
                },
                format="json",
            )

        self.assertEqual(resp.status_code, 200)
        kwargs = client_cls.return_value.messages.create.call_args.kwargs
        system = kwargs["system"]
        self.assertIn("CURRENT MAINTENANCE REQUEST", system)
        self.assertIn("Kitchen tap leaking", system)
        self.assertIn(str(req.pk), system)

    def test_unknown_maintenance_request_id_adds_warning_not_500(self):
        with mock.patch(
            "apps.maintenance.agent_assist_views.anthropic.Anthropic"
        ) as client_cls:
            client_cls.return_value.messages.create.return_value = _fake_claude_reply("ok")
            resp = self.client.post(
                CHAT_URL,
                {"message": "hi", "maintenance_request_id": 9_999_999},
                format="json",
            )
        self.assertEqual(resp.status_code, 200)
        kwargs = client_cls.return_value.messages.create.call_args.kwargs
        self.assertIn("could not load maintenance request", kwargs["system"])

    def test_token_usage_is_logged(self):
        before = AgentTokenLog.objects.count()
        with mock.patch(
            "apps.maintenance.agent_assist_views.anthropic.Anthropic"
        ) as client_cls:
            client_cls.return_value.messages.create.return_value = _fake_claude_reply(
                "ok", input_tokens=1234, output_tokens=567
            )
            resp = self.client.post(CHAT_URL, {"message": "hi"}, format="json")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(AgentTokenLog.objects.count(), before + 1)
        log = AgentTokenLog.objects.latest("created_at")
        self.assertEqual(log.endpoint, "agent_assist")
        self.assertEqual(log.input_tokens, 1234)
        self.assertEqual(log.output_tokens, 567)
        self.assertEqual(log.user, self.agent)

    def test_system_prompt_contains_skills_digest_section(self):
        """A MaintenanceSkill row in the DB should surface in the system
        prompt under the MAINTENANCE SKILLS section."""
        # Clear module cache
        from apps.maintenance.agent_assist_views import _skills_cache
        _skills_cache["objects"] = None
        _skills_cache["objects_expires"] = 0.0

        MaintenanceSkill.objects.create(
            name="Leaking tap",
            trade="plumbing",
            symptom_phrases=["dripping water"],
            steps=["shut water", "replace washer"],
            is_active=True,
        )

        with mock.patch(
            "apps.maintenance.agent_assist_views.anthropic.Anthropic"
        ) as client_cls:
            client_cls.return_value.messages.create.return_value = _fake_claude_reply("ok")
            resp = self.client.post(
                CHAT_URL, {"message": "tap dripping water"}, format="json"
            )

        self.assertEqual(resp.status_code, 200)
        kwargs = client_cls.return_value.messages.create.call_args.kwargs
        self.assertIn("MAINTENANCE SKILLS", kwargs["system"])
        self.assertIn("Leaking tap", kwargs["system"])

        # Clean up cache again for other tests
        _skills_cache["objects"] = None
        _skills_cache["objects_expires"] = 0.0
