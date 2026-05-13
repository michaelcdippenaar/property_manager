"""Reviewer agent tests — Wave 2A multi-turn shape.

Day 1-2 shipped a single forced ``submit_audit_report`` dispatch. Wave
2A extends the Reviewer into a multi-turn pull-tool loop (decision 10
analogue): turns ``1..MAX-1`` allow pull tools with ``tool_choice='auto'``
and the final turn forces ``submit_audit_report``.

Checks:

  * ``test_reviewer_final_dispatch_forces_submit_audit_report`` — the
    LAST dispatch (when no submission has been seen yet) forces
    ``tool_choice={"type":"tool","name":"submit_audit_report"}``.
  * ``test_reviewer_validates_tool_use_against_schema`` — a malformed
    payload raises :class:`ReviewerSchemaError`.
  * ``test_reviewer_raises_on_truncated_tool_use`` — when the FORCED
    dispatch's ``stop_reason='max_tokens'`` the handler raises
    :class:`ReviewerTruncatedError`.
  * ``test_reviewer_can_use_query_statute_pull_tool`` — the model emits
    a pull-tool ``tool_use``, the handler executes it + feeds the result
    back, and the next turn returns ``submit_audit_report``.
  * ``test_reviewer_force_submits_when_3_internal_turns_exceeded`` —
    after MAX_INTERNAL_TURNS pull-tool dispatches the final turn forces
    submit and the loop ends.
  * ``test_reviewer_handles_unknown_tool_name_gracefully`` — an unknown
    tool name raises :class:`ReviewerInvalidToolError` with the offender.
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
    ReviewerInvalidToolError,
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
    """Decision 22 — the FINAL Reviewer dispatch MUST force tool_choice."""

    def test_reviewer_final_dispatch_forces_submit_audit_report(self):
        """When the first turn yields only text, the next dispatch
        MUST be ``tool_choice={"type":"tool","name":"submit_audit_report"}``.
        """
        text_only = _fake_response(
            [{"type": "text", "text": "thinking..."}], stop_reason="end_turn"
        )
        submit = _fake_response(
            [_audit_tool_use_block(_valid_audit_input())]
        )
        client = _ScriptedAnthropic([text_only, submit])
        runner = _runner(client)

        handler = ReviewerHandler()
        result = handler.run(
            runner=runner,
            context=_ctx(),
            document_html="<section><h1>LEASE</h1></section>",
            system_blocks=[{"type": "text", "text": "stub"}],
        )

        # 2 dispatches; the second was forced.
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(client.calls[0]["tool_choice"], {"type": "auto"})
        final_tool_choice = client.calls[-1].get("tool_choice")
        self.assertIsNotNone(final_tool_choice, "Final tool_choice must be set.")
        self.assertEqual(final_tool_choice["type"], "tool")
        self.assertEqual(final_tool_choice["name"], "submit_audit_report")

        # Sanity — the result reflects the audit input.
        self.assertEqual(result.verdict, "pass")
        self.assertEqual(result.summary, "All compliant.")
        # terminated_reason was set to stale_progress when text-only
        # forced the next turn, then submit landed via that forced turn.
        self.assertEqual(result.terminated_reason, "stale_progress")


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
        """``stop_reason='max_tokens'`` on the FORCED dispatch MUST
        surface as :class:`ReviewerTruncatedError`.

        Scripts a text-only first turn so the second (forced) turn is
        the truncated one we want the handler to detect.
        """
        text_only = _fake_response(
            [{"type": "text", "text": "considering..."}], stop_reason="end_turn"
        )
        truncated = _fake_response(
            [_audit_tool_use_block(_valid_audit_input())],
            stop_reason="max_tokens",
        )
        client = _ScriptedAnthropic([text_only, truncated])
        runner = _runner(client)

        handler = ReviewerHandler()
        with self.assertRaises(ReviewerTruncatedError):
            handler.run(
                runner=runner,
                context=_ctx(),
                document_html="<section />",
                system_blocks=[{"type": "text", "text": "stub"}],
            )


def _pull_tool_use_block(
    *,
    block_id: str,
    name: str,
    inp: dict[str, Any],
) -> dict[str, Any]:
    """Build a SimpleNamespace-friendly tool_use dict for a pull tool."""
    return {"type": "tool_use", "id": block_id, "name": name, "input": inp}


class ReviewerPullToolLoopTests(unittest.TestCase):
    """Multi-turn pull-tool loop — Wave 2A."""

    def test_reviewer_can_use_query_statute_pull_tool(self):
        """The Reviewer emits ``query_statute``, the handler executes it
        via :func:`apps.legal_rag.queries.query_statute`, feeds the
        result back, and the next turn returns ``submit_audit_report``.
        """
        # Patch query_statute so the handler doesn't hit the DB.
        from apps.legal_rag import queries as legal_rag_queries

        class _FakeFact:
            concept_id = "rha-s7"
            citation_string = "RHA s7"
            plain_english_summary = "Tribunal is established."
            citation_confidence = "high"
            legal_provisional = False
            topic_tags = ("tribunal",)

        original = legal_rag_queries.query_statute
        legal_rag_queries.query_statute = lambda *args, **kwargs: _FakeFact()

        try:
            turn1 = _fake_response(
                [
                    _pull_tool_use_block(
                        block_id="toolu_qs_1",
                        name="query_statute",
                        inp={"citation": "RHA s7"},
                    )
                ],
                stop_reason="tool_use",
            )
            turn2 = _fake_response(
                [_audit_tool_use_block(_valid_audit_input())]
            )
            client = _ScriptedAnthropic([turn1, turn2])
            runner = _runner(client)

            handler = ReviewerHandler()
            result = handler.run(
                runner=runner,
                context=_ctx(),
                document_html="<section><h1>LEASE</h1></section>",
                system_blocks=[{"type": "text", "text": "stub"}],
            )
        finally:
            legal_rag_queries.query_statute = original

        # 2 dispatches: pull tool + submit_audit_report.
        self.assertEqual(len(client.calls), 2)
        # First dispatch: tool_choice='auto'.
        self.assertEqual(client.calls[0].get("tool_choice"), {"type": "auto"})
        # Pull-tool call recorded.
        self.assertEqual(len(result.pull_tool_calls), 1)
        self.assertEqual(result.pull_tool_calls[0]["name"], "query_statute")
        self.assertIn("RHA s7", result.pull_tool_calls[0]["result_summary"])
        self.assertEqual(result.internal_turns, 2)
        self.assertEqual(result.verdict, "pass")

    def test_reviewer_force_submits_when_3_internal_turns_exceeded(self):
        """If the model never emits ``submit_audit_report`` on its own
        within MAX_INTERNAL_TURNS, the loop's final turn forces submit
        and the test verifies that the dispatched tool_choice was forced.
        """
        # Stub query_clauses since the model will call it on pull turns.
        from apps.leases import lease_law_corpus_queries

        original = lease_law_corpus_queries.query_clauses
        lease_law_corpus_queries.query_clauses = lambda **kwargs: []

        try:
            # Turns 1 + 2: model keeps calling query_clauses with no
            # progress. Turn 3 (forced): model finally submits.
            pull_turn = _fake_response(
                [
                    _pull_tool_use_block(
                        block_id="toolu_qc_x",
                        name="query_clauses",
                        inp={"topic_tags": ["deposit"]},
                    )
                ],
                stop_reason="tool_use",
            )
            submit = _fake_response(
                [_audit_tool_use_block(_valid_audit_input())]
            )
            client = _ScriptedAnthropic([pull_turn, pull_turn, submit])
            runner = _runner(client)

            handler = ReviewerHandler()
            result = handler.run(
                runner=runner,
                context=_ctx(),
                document_html="<section />",
                system_blocks=[{"type": "text", "text": "stub"}],
            )
        finally:
            lease_law_corpus_queries.query_clauses = original

        self.assertEqual(len(client.calls), ReviewerHandler.MAX_INTERNAL_TURNS)
        # First two dispatches: tool_choice='auto'.
        self.assertEqual(client.calls[0]["tool_choice"], {"type": "auto"})
        self.assertEqual(client.calls[1]["tool_choice"], {"type": "auto"})
        # Final dispatch: forced submit_audit_report.
        self.assertEqual(
            client.calls[2]["tool_choice"],
            {"type": "tool", "name": "submit_audit_report"},
        )
        # 2 pull tool calls recorded.
        self.assertEqual(len(result.pull_tool_calls), 2)
        self.assertEqual(result.internal_turns, ReviewerHandler.MAX_INTERNAL_TURNS)

    def test_reviewer_handles_unknown_tool_name_gracefully(self):
        """An unknown tool name MUST raise :class:`ReviewerInvalidToolError`
        with the offending name on the exception."""
        bogus = _fake_response(
            [
                _pull_tool_use_block(
                    block_id="toolu_bogus",
                    name="hallucinated_tool",
                    inp={"foo": "bar"},
                )
            ],
            stop_reason="tool_use",
        )
        client = _ScriptedAnthropic([bogus])
        runner = _runner(client)

        handler = ReviewerHandler()
        with self.assertRaises(ReviewerInvalidToolError) as ctx:
            handler.run(
                runner=runner,
                context=_ctx(),
                document_html="<section />",
                system_blocks=[{"type": "text", "text": "stub"}],
            )
        self.assertEqual(ctx.exception.tool_name, "hallucinated_tool")
        self.assertIn("hallucinated_tool", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
