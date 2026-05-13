"""Lease AI v2 view tests — Phase 2 Day 1-2.

Three regression checks per the build brief:

  * ``test_v2_endpoint_returns_sse_response`` — the response is a
    ``StreamingHttpResponse`` with ``Content-Type: text/event-stream``
    and the buffering-disable headers.
  * ``test_v2_endpoint_emits_done_event`` — the stream contains an
    ``event: done`` frame.
  * ``test_v2_endpoint_async_def`` — the view's ``post`` is a real
    async coroutine function (decision per ASGI ADR step 1).

The tests use Django's :class:`~django.test.AsyncClient` so the
async view dispatches natively. We inject a scripted Anthropic client
through a module-level monkeypatch on the v2 view's anthropic builder.

``test_v2_endpoint_async_def`` is intentionally DB-independent
(pure introspection) so it runs even when the test DB has migration
drift — the async/sync split is a load-bearing invariant we want
checked on every run.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import unittest
from types import SimpleNamespace
from typing import Any

import pytest
from django.test import AsyncClient, TransactionTestCase

from apps.leases import template_views_v2 as v2_module
from apps.leases.template_views_v2 import LeaseTemplateAIChatV2View


# ── Fake Anthropic client ───────────────────────────────────────────── #


def _usage(
    input_tokens: int = 100, output_tokens: int = 50
) -> SimpleNamespace:
    return SimpleNamespace(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
    )


def _drafter_response() -> SimpleNamespace:
    return SimpleNamespace(
        id="msg_v2_drafter",
        type="message",
        role="assistant",
        model="claude-sonnet-4-5",
        stop_reason="end_turn",
        stop_sequence=None,
        content=[
            SimpleNamespace(
                type="text",
                text="<section><h2>PARTIES</h2><p>Drafter output</p></section>",
            )
        ],
        usage=_usage(),
    )


def _reviewer_response() -> SimpleNamespace:
    return SimpleNamespace(
        id="msg_v2_reviewer",
        type="message",
        role="assistant",
        model="claude-haiku-4-5-20251001",
        stop_reason="tool_use",
        stop_sequence=None,
        content=[
            SimpleNamespace(
                type="tool_use",
                id="toolu_v2_audit",
                name="submit_audit_report",
                input={
                    "verdict": "pass",
                    "summary": "Compliant.",
                    "statute_findings": [],
                    "case_law_findings": [],
                    "format_findings": [],
                },
            )
        ],
        usage=_usage(),
    )


class _ScriptedClient:
    """``client.messages.create`` returns the queued response in order."""

    def __init__(self):
        self._responses = [_drafter_response(), _reviewer_response()]
        self.calls: list[dict[str, Any]] = []
        self.messages = self

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        return self._responses.pop(0)


# ── DB-independent introspection test ───────────────────────────────── #


class LeaseAIV2AsyncSignatureTests(unittest.TestCase):
    """Pure-introspection test — runs without the test DB.

    The async/sync split for the v2 view is a load-bearing invariant
    (decision per the ASGI ADR step 1). Keep this test DB-independent
    so a stale migration in the dev DB never blocks the signature
    regression check.
    """

    def test_v2_endpoint_async_def(self):
        """``LeaseTemplateAIChatV2View.post`` MUST be a coroutine function."""
        self.assertTrue(
            inspect.iscoroutinefunction(LeaseTemplateAIChatV2View.post),
            "LeaseTemplateAIChatV2View.post must be async def.",
        )


# ── Test base for DB-bound SSE tests ────────────────────────────────── #


@pytest.mark.django_db(transaction=True)
class V2EndpointTestBase(TransactionTestCase):
    """Set up one agency + one template + one agent user.

    Uses ``transaction=True`` so the AsyncClient's sync_to_async wrappers
    (which run in a separate thread with its own DB connection) see the
    test fixtures via committed reads rather than the test's still-open
    transaction.
    """

    def setUp(self):
        # Lazy-import inside setUp so the module imports cleanly even
        # when DB migrations haven't run (the introspection test above
        # doesn't need them).
        from apps.accounts.models import Agency, User
        from apps.leases.models import LeaseTemplate

        self.agency = Agency.objects.create(name="Test Agency v2")
        self.user = User.objects.create_user(
            email="v2_agent@klikk.local",
            password="pass",
            role=User.Role.AGENCY_ADMIN,
        )
        self.user.agency = self.agency
        self.user.save(update_fields=["agency"])

        self.template = LeaseTemplate.objects.create(
            agency=self.agency,
            name="V2 Test Template",
            content_html="<p>placeholder body</p>",
        )
        # AsyncClient + JWT bearer — matches v1's auth pattern. Async-
        # native dispatch on daphne so the view's coroutine runs without
        # the threading shim. AsyncClient defaults use lower-cased ASGI
        # header names, so we pass the Authorization header via the
        # ``headers`` kwarg on each ``.post`` call rather than relying
        # on the deprecated ``HTTP_AUTHORIZATION`` kwarg.
        from rest_framework_simplejwt.tokens import RefreshToken

        token = RefreshToken.for_user(self.user)
        self.access = str(token.access_token)
        self.auth_headers = {"Authorization": f"Bearer {self.access}"}
        self.async_client = AsyncClient()

    @staticmethod
    def _install_scripted_anthropic(monkeypatched_client: "_ScriptedClient"):
        """Swap ``_build_anthropic_client`` to return our scripted client."""
        v2_module._build_anthropic_client = lambda: monkeypatched_client


# ── DB-bound SSE tests ──────────────────────────────────────────────── #


@pytest.mark.django_db(transaction=True)
class LeaseAIV2EndpointTests(V2EndpointTestBase):
    """SSE shape + done-event presence."""

    URL_TPL = "/api/v1/leases/templates/{tid}/ai-chat-v2/"

    def _payload(self) -> str:
        return json.dumps(
            {
                "message": "draft me a sectional title lease",
                "intent": "generate",
                "property_type": "sectional_title",
                "tenant_count": 1,
                "lease_type": "fixed_term",
            }
        )

    def test_v2_endpoint_returns_sse_response(self):
        """Response is streaming with the right headers."""
        scripted = _ScriptedClient()
        self._install_scripted_anthropic(scripted)

        async def _drive() -> Any:
            return await self.async_client.post(
                self.URL_TPL.format(tid=self.template.pk),
                data=self._payload(),
                content_type="application/json",
                headers=self.auth_headers,
            )

        response = asyncio.run(_drive())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"].split(";")[0].strip(),
            "text/event-stream",
        )
        self.assertEqual(response["X-Accel-Buffering"], "no")
        self.assertIn("no-cache", response["Cache-Control"])
        self.assertIn("no-transform", response["Cache-Control"])

    def test_v2_endpoint_emits_done_event(self):
        """The stream MUST contain a ``event: done`` SSE frame."""
        scripted = _ScriptedClient()
        self._install_scripted_anthropic(scripted)

        async def _drive_and_drain() -> str:
            resp = await self.async_client.post(
                self.URL_TPL.format(tid=self.template.pk),
                data=self._payload(),
                content_type="application/json",
                headers=self.auth_headers,
            )
            # ``streaming_content`` is async-iterable on AsyncClient.
            parts: list[str] = []
            async for chunk in resp.streaming_content:
                if isinstance(chunk, bytes):
                    parts.append(chunk.decode("utf-8", errors="replace"))
                else:
                    parts.append(str(chunk))
            return "".join(parts)

        body = asyncio.run(_drive_and_drain())
        self.assertIn("event: done", body)
        # Sanity — the SSE generator emitted the start and finish frames.
        self.assertIn("event: status", body)
        self.assertIn("event: agent_started", body)
        self.assertIn("event: agent_finished", body)

    def test_v2_endpoint_persists_ailease_agent_run(self):
        """After the SSE stream closes the ``AILeaseAgentRun`` row MUST
        exist with the right ``request_id`` and budget counters.

        Sends a deterministic ``request_id`` so we can ``.get()`` the
        row by primary key after the stream finishes.
        """
        from apps.leases.models import AILeaseAgentRun

        scripted = _ScriptedClient()
        self._install_scripted_anthropic(scripted)
        deterministic_id = "test-wave-2a-finalize-uuid"

        payload = json.dumps(
            {
                "message": "draft me a sectional title lease",
                "intent": "generate",
                "property_type": "sectional_title",
                "tenant_count": 1,
                "lease_type": "fixed_term",
                "request_id": deterministic_id,
            }
        )

        async def _drive_and_drain() -> str:
            resp = await self.async_client.post(
                self.URL_TPL.format(tid=self.template.pk),
                data=payload,
                content_type="application/json",
                headers=self.auth_headers,
            )
            parts: list[str] = []
            async for chunk in resp.streaming_content:
                if isinstance(chunk, bytes):
                    parts.append(chunk.decode("utf-8", errors="replace"))
                else:
                    parts.append(str(chunk))
            return "".join(parts)

        body = asyncio.run(_drive_and_drain())
        # The audit_persisted event MUST appear after the done event.
        done_idx = body.find("event: done")
        persisted_idx = body.find("event: audit_persisted")
        self.assertGreater(done_idx, 0, "done event must be in the stream")
        self.assertGreater(
            persisted_idx,
            done_idx,
            "audit_persisted MUST follow done in the SSE order.",
        )

        # The row exists with the expected fields populated.
        run = AILeaseAgentRun.objects.get(request_id=deterministic_id)
        self.assertEqual(run.intent, "generate")
        self.assertGreaterEqual(run.llm_call_count, 1)
        self.assertEqual(run.terminated_reason, "completed")
        self.assertIsNotNone(run.completed_at)
        # call_log carries one entry per dispatch.
        self.assertGreaterEqual(len(run.call_log), 1)
