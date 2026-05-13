"""Drafter agent tests — Phase 2 Day 1-2.

Three regression checks per the build brief:

  * ``test_drafter_pulls_clause_by_id_via_add_clause_tool`` — the
    ``add_clause`` tool path looks up the clause via
    :func:`query_clauses` and appends the rendered snippet.
  * ``test_drafter_respects_internal_turn_cap`` — the per-agent
    3-turn cap (decision 10) terminates a runaway tool loop without
    blowing through the runner's outer 8-call cap.
  * ``test_drafter_persona_forbids_placeholders`` — the persona
    contains the literal "MUST NOT emit '[needs completion]'"
    instruction so the regression battery can grep for it.

All tests use a fake ``anthropic_client`` whose
``messages.create`` returns a hand-rolled :class:`SimpleNamespace` —
no cassette dependency, no live API.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import Any

from apps.leases.agent_runner import LeaseAgentRunner
from apps.leases.agents import LeaseContext
from apps.leases.agents.context import IntentEnum
from apps.leases.agents.drafter import (
    PERSONA as DRAFTER_PERSONA,
)
from apps.leases.agents.drafter import (
    DrafterHandler,
    _apply_add_clause,
)


# ── Fakes ───────────────────────────────────────────────────────────── #


def _fake_usage(input_tokens: int = 100, output_tokens: int = 50) -> SimpleNamespace:
    return SimpleNamespace(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
    )


def _fake_response(
    content: list[dict[str, Any]],
    *,
    stop_reason: str = "end_turn",
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> SimpleNamespace:
    """Build a mock SDK response matching the runner's read surface."""
    blocks = []
    for c in content:
        blocks.append(SimpleNamespace(**c))
    return SimpleNamespace(
        id="msg_fake",
        type="message",
        role="assistant",
        model="claude-sonnet-4-5",
        stop_reason=stop_reason,
        stop_sequence=None,
        content=blocks,
        usage=_fake_usage(input_tokens, output_tokens),
    )


class _ScriptedAnthropic:
    """Anthropic-shaped client that returns scripted responses in order."""

    def __init__(self, responses: list[SimpleNamespace]):
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []
        self.messages = self  # ``client.messages.create`` shape

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        if not self._responses:
            raise RuntimeError(
                "ScriptedAnthropic: no more scripted responses queued."
            )
        return self._responses.pop(0)


def _ctx(user_message: str = "draft a sectional title lease") -> LeaseContext:
    return LeaseContext(
        intent=IntentEnum.GENERATE,
        user_message=user_message,
        property_type="sectional_title",
        tenant_count=1,
        lease_type="fixed_term",
        chat_history=({"role": "user", "content": user_message},),
    )


def _runner(client: _ScriptedAnthropic) -> LeaseAgentRunner:
    return LeaseAgentRunner(
        request_id="test-req",
        intent="generate",
        anthropic_client=client,
        max_calls=8,
        max_wallclock_seconds=60.0,
        max_retries=1,
        max_cost_usd=1.0,
    )


# ── Tests ───────────────────────────────────────────────────────────── #


class DrafterAddClauseTests(unittest.TestCase):
    """Verify the ``add_clause`` tool path."""

    def test_drafter_pulls_clause_by_id_via_add_clause_tool(self):
        """The Drafter's ``add_clause`` tool routes through
        :func:`_apply_add_clause`, which calls ``query_clauses`` and
        renders the matched clause body into the document.

        We stub ``apps.leases.lease_law_corpus_queries.query_clauses``
        with a single ``ClauseChunk`` so the test runs without the
        ChromaDB index.
        """
        from apps.leases.lease_law_corpus_queries import ClauseChunk

        fake_chunk = ClauseChunk(
            id="clause-deposit-interest-bearing-account-v1",
            version=1,
            content_hash="abc123",
            clause_title="Deposit — Interest-Bearing Account",
            clause_body="The deposit is held in an interest-bearing account.",
            topic_tags=("deposit",),
            related_citations=("RHA_5_3_f",),
            property_types=("sectional_title",),
            tenant_counts=("any",),
            lease_types=("fixed_term",),
            merge_fields_used=("deposit",),
            citation_confidence="high",
            legal_provisional=False,
            confidence_level="mc_reviewed",
            source_path="",
        )

        # Patch query_clauses
        from apps.leases import lease_law_corpus_queries

        original = lease_law_corpus_queries.query_clauses
        lease_law_corpus_queries.query_clauses = (
            lambda **kwargs: [fake_chunk]
        )
        try:
            new_html, summary = _apply_add_clause(
                {
                    "after_line_index": -1,
                    "clause_id": fake_chunk.id,
                },
                document_html="<section><h2>EXISTING</h2></section>",
            )
        finally:
            lease_law_corpus_queries.query_clauses = original

        self.assertIn(fake_chunk.id, new_html)
        self.assertIn("Deposit — Interest-Bearing Account", new_html)
        self.assertIn("interest-bearing account", new_html)
        self.assertIn(fake_chunk.id, summary)
        # Original content still present.
        self.assertIn("EXISTING", new_html)


class DrafterInternalTurnCapTests(unittest.TestCase):
    """Decision 10 — Drafter cannot exceed 3 internal turns."""

    def test_drafter_respects_internal_turn_cap(self):
        """If every dispatch returns a ``tool_use``, the loop MUST exit
        after :attr:`DrafterHandler.MAX_INTERNAL_TURNS` turns and report
        ``terminated_reason='internal_turn_cap'`` — never call the
        client a 4th time within one Drafter pass."""
        cap = DrafterHandler.MAX_INTERNAL_TURNS

        def _turn(idx: int) -> SimpleNamespace:
            return _fake_response(
                content=[
                    {
                        "type": "tool_use",
                        "id": f"toolu_{idx}",
                        "name": "highlight_fields",
                        "input": {"field_names": [f"field_{idx}"]},
                    }
                ],
                stop_reason="tool_use",
            )

        client = _ScriptedAnthropic([_turn(i) for i in range(cap + 2)])
        runner = _runner(client)

        handler = DrafterHandler()
        result = handler.run(
            runner=runner,
            context=_ctx(),
            system_blocks=[{"type": "text", "text": "stub"}],
        )

        # The client must NOT have been called more than `cap` times in
        # one Drafter pass — the cap is the per-agent guard against
        # tool-loop runaways.
        self.assertEqual(
            len(client.calls), cap,
            f"DrafterHandler should cap at {cap} internal dispatches "
            f"but issued {len(client.calls)}.",
        )
        self.assertEqual(result.terminated_reason, "internal_turn_cap")
        self.assertEqual(runner.llm_call_count, cap)


class DrafterPersonaTests(unittest.TestCase):
    """Persona-text invariants the regression battery greps for."""

    def test_drafter_persona_forbids_placeholders(self):
        """The persona MUST contain the literal placeholder-ban
        instruction so a model-prompt regression is easy to catch.

        Two assertions per the build brief:

          1. The "[needs completion]" prohibition is spelled out.
          2. The "canonical merge fields" rule appears.
        """
        self.assertIn("[needs completion]", DRAFTER_PERSONA)
        self.assertIn("MUST NOT emit", DRAFTER_PERSONA)
        self.assertIn("canonical merge fields", DRAFTER_PERSONA.lower())


if __name__ == "__main__":
    unittest.main()
