"""Reviewer agent tests — Phase 2 Day 1-2.

Three regression checks per the build brief:

  * ``test_reviewer_uses_force_tool_choice`` — every Reviewer dispatch
    sets ``tool_choice={"type":"tool","name":"submit_audit_report"}``
    (decision 22 invariant).
  * ``test_reviewer_validates_tool_use_against_schema`` — a malformed
    payload raises :class:`ReviewerSchemaError`.
  * ``test_reviewer_raises_on_truncated_tool_use`` — when the response's
    ``stop_reason='max_tokens'`` with a forced tool_choice the handler
    raises :class:`ReviewerTruncatedError`.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import Any

from apps.leases.agent_runner import LeaseAgentRunner
from apps.leases.agents import LeaseContext
from apps.leases.agents.context import IntentEnum
from apps.leases.agents.reviewer import (
    ReviewerHandler,
    ReviewerSchemaError,
    ReviewerTruncatedError,
)


# ── Fakes ───────────────────────────────────────────────────────────── #


def _fake_usage(
    input_tokens: int = 100, output_tokens: int = 50
) -> SimpleNamespace:
    return SimpleNamespace(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
    )


def _fake_response(
    content: list[dict[str, Any]],
    *,
    stop_reason: str = "tool_use",
) -> SimpleNamespace:
    blocks = []
    for c in content:
        blocks.append(SimpleNamespace(**c))
    return SimpleNamespace(
        id="msg_fake",
        type="message",
        role="assistant",
        model="claude-haiku-4-5-20251001",
        stop_reason=stop_reason,
        stop_sequence=None,
        content=blocks,
        usage=_fake_usage(),
    )


class _ScriptedAnthropic:
    """Anthropic-shaped client returning scripted responses in order."""

    def __init__(self, responses: list[SimpleNamespace]):
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []
        self.messages = self

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        if not self._responses:
            raise RuntimeError("no more responses")
        return self._responses.pop(0)


def _ctx() -> LeaseContext:
    return LeaseContext(
        intent=IntentEnum.AUDIT,
        user_message="audit this lease",
        property_type="sectional_title",
        tenant_count=1,
        lease_type="fixed_term",
    )


def _runner(client: _ScriptedAnthropic) -> LeaseAgentRunner:
    return LeaseAgentRunner(
        request_id="test-req",
        intent="audit",
        anthropic_client=client,
        max_calls=8,
        max_wallclock_seconds=60.0,
        max_retries=1,
        max_cost_usd=1.0,
    )


def _valid_audit_input() -> dict[str, Any]:
    return {
        "verdict": "pass",
        "summary": "All compliant.",
        "statute_findings": [],
        "case_law_findings": [],
        "format_findings": [],
    }


def _audit_tool_use_block(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "tool_use",
        "id": "toolu_audit_1",
        "name": "submit_audit_report",
        "input": payload,
    }


# ── Tests ───────────────────────────────────────────────────────────── #


class ReviewerForceToolChoiceTests(unittest.TestCase):
    """Decision 22 — Reviewer call MUST set ``tool_choice``."""

    def test_reviewer_uses_force_tool_choice(self):
        """Inspect dispatch kwargs to verify tool_choice is forced."""
        client = _ScriptedAnthropic(
            [_fake_response([_audit_tool_use_block(_valid_audit_input())])]
        )
        runner = _runner(client)

        handler = ReviewerHandler()
        result = handler.run(
            runner=runner,
            context=_ctx(),
            document_html="<section><h1>LEASE</h1></section>",
            system_blocks=[{"type": "text", "text": "stub"}],
        )

        self.assertEqual(len(client.calls), 1, "Reviewer must dispatch exactly once.")
        tool_choice = client.calls[0].get("tool_choice")
        self.assertIsNotNone(tool_choice, "tool_choice must be set.")
        self.assertEqual(tool_choice["type"], "tool")
        self.assertEqual(tool_choice["name"], "submit_audit_report")

        # Sanity — the result reflects the audit input.
        self.assertEqual(result.verdict, "pass")
        self.assertEqual(result.summary, "All compliant.")


class ReviewerSchemaValidationTests(unittest.TestCase):
    """Decision 22 — schema validation guards against drift."""

    def test_reviewer_validates_tool_use_against_schema(self):
        """A payload missing required fields MUST raise
        :class:`ReviewerSchemaError`."""
        bad_input = {
            "verdict": "pass",
            "summary": "OK",
            # missing `statute_findings`, `case_law_findings`, `format_findings`
        }
        client = _ScriptedAnthropic(
            [_fake_response([_audit_tool_use_block(bad_input)])]
        )
        runner = _runner(client)

        handler = ReviewerHandler()
        with self.assertRaises(ReviewerSchemaError):
            handler.run(
                runner=runner,
                context=_ctx(),
                document_html="<section />",
                system_blocks=[{"type": "text", "text": "stub"}],
            )

    def test_reviewer_validates_unexpected_field_rejection(self):
        """``additionalProperties: false`` MUST reject unknown keys."""
        bad_input = dict(_valid_audit_input())
        bad_input["unexpected_key"] = "should-be-rejected"
        client = _ScriptedAnthropic(
            [_fake_response([_audit_tool_use_block(bad_input)])]
        )
        runner = _runner(client)

        handler = ReviewerHandler()
        with self.assertRaises(ReviewerSchemaError):
            handler.run(
                runner=runner,
                context=_ctx(),
                document_html="<section />",
                system_blocks=[{"type": "text", "text": "stub"}],
            )


class ReviewerTruncationTests(unittest.TestCase):
    """Edge case: forced tool_choice + max_tokens → truncated partial-JSON."""

    def test_reviewer_raises_on_truncated_tool_use(self):
        """``stop_reason='max_tokens'`` with forced tool_choice MUST
        surface as :class:`ReviewerTruncatedError`."""
        # The tool_use is shaped fine but the response signals truncation.
        client = _ScriptedAnthropic(
            [
                _fake_response(
                    [_audit_tool_use_block(_valid_audit_input())],
                    stop_reason="max_tokens",
                )
            ]
        )
        runner = _runner(client)

        handler = ReviewerHandler()
        with self.assertRaises(ReviewerTruncatedError):
            handler.run(
                runner=runner,
                context=_ctx(),
                document_html="<section />",
                system_blocks=[{"type": "text", "text": "stub"}],
            )


if __name__ == "__main__":
    unittest.main()
