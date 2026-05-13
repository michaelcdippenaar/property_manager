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
    _apply_check_rha_compliance,
    _apply_edit_lines,
    _apply_format_sa_standard,
    _apply_highlight_fields,
    _apply_insert_signature_field,
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


class DrafterEditLinesTests(unittest.TestCase):
    """Wave 2A — ``edit_lines`` tool implementation."""

    def test_apply_edit_lines_preserves_signature_tokens(self):
        """Edit a range that contains a ``⟪SIG#0⟫`` token; assert the
        token is still in the document after the edit."""
        # ⟪SIG#1⟫ inside the range that gets replaced. Note: signature
        # tokens are 1-indexed per _apply_insert_signature_field, so we
        # plant ⟪SIG#1⟫ which is the canonical first token.
        html = (
            "<p>Pre</p>"
            "<p>⟪SIG#1⟫</p>"
            "<p>Post</p>"
        )
        new_html, summary = _apply_edit_lines(
            {
                "from_index": 1,
                "to_index": 2,
                "new_lines": [{"tag": "p", "text": "replacement body"}],
                "summary": "replace line 1",
            },
            document_html=html,
        )
        self.assertIn("⟪SIG#1⟫", new_html)
        self.assertIn("replacement body", new_html)
        self.assertIn("Pre", new_html)
        self.assertIn("Post", new_html)
        self.assertIn("Preserved 1", summary)

    def test_apply_edit_lines_replaces_range(self):
        """Replacing 2 elements with 1 reduces the block count by 1."""
        html = "<p>A</p><p>B</p><p>C</p><p>D</p>"
        new_html, summary = _apply_edit_lines(
            {
                "from_index": 1,
                "to_index": 3,
                "new_lines": [{"tag": "p", "text": "merged BC"}],
            },
            document_html=html,
        )
        self.assertIn("merged BC", new_html)
        self.assertNotIn(">B<", new_html)
        self.assertNotIn(">C<", new_html)
        self.assertIn(">A<", new_html)
        self.assertIn(">D<", new_html)
        self.assertIn("[1:3]", summary)


class DrafterFormatSAStandardTests(unittest.TestCase):
    """Wave 2A — ``format_sa_standard`` tool implementation."""

    def test_apply_format_sa_standard_adds_missing_sections(self):
        """A document missing several standard sections gets placeholders
        appended when ``add_missing=True``."""
        html = "<section><h2>PARTIES</h2><p>...</p></section>"
        new_html, summary = _apply_format_sa_standard(
            {"add_missing": True, "preserve_custom": True},
            document_html=html,
        )
        # PARTIES already present — won't be added.
        # Everything else should appear as a placeholder.
        self.assertIn("PROPERTY", new_html)
        self.assertIn("RENT", new_html)
        self.assertIn("DEPOSIT", new_html)
        self.assertIn("SIGNATURES", new_html)
        # The placeholder MUST NOT use the banned phrases.
        self.assertNotIn("[needs completion]", new_html)
        self.assertNotIn("[TBD]", new_html)
        self.assertIn("Section to be drafted", new_html)
        self.assertIn("inserted", summary)

    def test_apply_format_sa_standard_preserves_custom_when_flagged(self):
        """``preserve_custom=True`` keeps non-standard sections in place
        (today: all non-standard sections stay in place regardless, but
        the flag is exercised so the contract is locked)."""
        html = (
            "<section><h2>PARTIES</h2><p>X</p></section>"
            "<section><h2>HOUSE RULES</h2><p>No loud music.</p></section>"
        )
        new_html, summary = _apply_format_sa_standard(
            {"add_missing": True, "preserve_custom": True},
            document_html=html,
        )
        self.assertIn("HOUSE RULES", new_html)
        self.assertIn("No loud music.", new_html)
        self.assertIn("preserve_custom=True", summary)


class DrafterInsertSignatureFieldTests(unittest.TestCase):
    """Wave 2A — ``insert_signature_field`` tool implementation."""

    def test_apply_insert_signature_field_allocates_next_token(self):
        """A document with ⟪SIG#1⟫ already present gets ⟪SIG#2⟫ next."""
        html = "<p>⟪SIG#1⟫</p>"
        new_html, summary = _apply_insert_signature_field(
            {
                "after_line_index": -1,
                "field_type": "signature",
                "signer_role": "tenant",
                "field_name": "tenant_1_signature",
            },
            document_html=html,
        )
        self.assertIn("⟪SIG#1⟫", new_html)
        self.assertIn("⟪SIG#2⟫", new_html)
        self.assertIn("⟪SIG#2⟫", summary)
        self.assertIn("data-signature-role=\"tenant\"", new_html)


class DrafterHighlightFieldsTests(unittest.TestCase):
    """Wave 2A — ``highlight_fields`` is conversational, doesn't mutate."""

    def test_apply_highlight_fields_does_not_mutate_html(self):
        """The returned HTML is byte-identical and the payload carries
        the field list + message."""
        html = "<p>some body</p>"
        new_html, summary, payload = _apply_highlight_fields(
            {
                "field_names": ["deposit_account_bank_name", "deposit_account_no"],
                "message": "These deposit fields are blank — please fill them.",
            },
            document_html=html,
        )
        self.assertEqual(new_html, html, "highlight_fields MUST NOT mutate HTML.")
        self.assertEqual(
            payload["field_names"],
            ["deposit_account_bank_name", "deposit_account_no"],
        )
        self.assertIn("blank", payload["message"])
        self.assertIn("2 field(s)", summary)


class DrafterCheckRHAComplianceTests(unittest.TestCase):
    """Wave 2A — ``check_rha_compliance`` is a read-only diagnostic."""

    def test_apply_check_rha_compliance_flags_known_wrong_citation(self):
        """Planting a known-wrong citation (RHA s13 claim about Tribunal
        establishment) MUST be flagged ``wrong``."""
        # "RHA:s13|tribunal_established" is in KNOWN_WRONG_CITATIONS.
        # The detector keys off RHA:s13 (any sub-section) when no other
        # context disambiguates — Day 1-2 behaviour is to flag every
        # RHA s13 occurrence as wrong because the only KNOWN_WRONG entry
        # for that section points to the tribunal-established mis-cite.
        html = (
            "<p>The Tribunal is established under RHA s13.</p>"
            "<p>Deposit per RHA s5(3)(e).</p>"
        )
        new_html, summary, findings = _apply_check_rha_compliance(
            {}, document_html=html
        )
        # Read-only: HTML is byte-identical.
        self.assertEqual(new_html, html)
        # Wrong citation flagged.
        wrong = [f for f in findings if f["status"] == "wrong"]
        self.assertEqual(
            len(wrong),
            1,
            f"Expected 1 wrong finding for RHA s13. Got: {findings}",
        )
        self.assertIn("Tribunal", wrong[0]["message"])
        # Right citation passes.
        ok = [f for f in findings if f["status"] == "ok"]
        self.assertGreaterEqual(len(ok), 1)
        self.assertIn("wrong=1", summary)


if __name__ == "__main__":
    unittest.main()
