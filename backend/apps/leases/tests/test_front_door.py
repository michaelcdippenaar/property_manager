"""Front Door tests — Phase 2 Day 1-2.

Three regression checks per the build brief:

  * ``test_classify_intent_keywords`` — every :class:`IntentEnum` value
    maps cleanly from at least one canonical user phrase.
  * ``test_clarifying_question_for_missing_context`` — a ``generate``
    request missing ``property_type`` yields a non-None
    ``clarifying_question``.
  * ``test_three_system_blocks_have_cache_control_markers`` —
    decision 18 invariant: the three system blocks each carry
    ``cache_control={"type":"ephemeral"}``.
"""
from __future__ import annotations

import unittest

from apps.leases.agents import LeaseContext
from apps.leases.agents.context import IntentEnum
from apps.leases.agents.front_door import (
    build_dispatch,
    classify_intent,
)


# ── Tests ───────────────────────────────────────────────────────────── #


class ClassifyIntentTests(unittest.TestCase):
    """Heuristic intent table — every enum value must map from prose."""

    EXAMPLE_PHRASES: dict[IntentEnum, str] = {
        IntentEnum.GENERATE: "Please write me a lease for the property at 1 Test Way",
        IntentEnum.EDIT: "Rewrite line 23 of the deposit clause",
        IntentEnum.INSERT_CLAUSE: "Add a no-pets clause after the parties section",
        IntentEnum.FORMAT: "Add a table of contents and a running header",
        IntentEnum.AUDIT: "Audit my lease for compliance",
        IntentEnum.AUDIT_CASE_LAW: "Audit my lease against case law decisions too",
        IntentEnum.ANSWER: "What does RHA s5(3)(f) say?",
    }

    def test_classify_intent_keywords(self):
        """Every IntentEnum value MUST be reachable from a canonical phrase."""
        for intent, phrase in self.EXAMPLE_PHRASES.items():
            with self.subTest(intent=intent):
                self.assertEqual(
                    classify_intent(phrase),
                    intent,
                    f"Phrase {phrase!r} should classify as {intent.value}.",
                )

    def test_classify_intent_empty_defaults_to_answer(self):
        """Empty / whitespace-only messages default to ANSWER."""
        self.assertEqual(classify_intent(""), IntentEnum.ANSWER)
        self.assertEqual(classify_intent("   "), IntentEnum.ANSWER)


class ClarifyingQuestionTests(unittest.TestCase):
    """Front Door MUST detect missing required context."""

    def test_clarifying_question_for_missing_context(self):
        """A generate request without property_type / tenant_count /
        lease_type MUST get a clarifying question, not a dispatch."""
        # GENERATE requires property_type + tenant_count + lease_type.
        bare_ctx = LeaseContext(
            intent=IntentEnum.GENERATE,
            user_message="draft me a lease please",
            property_type=None,
            tenant_count=None,
            lease_type=None,
        )
        dispatch = build_dispatch(bare_ctx)

        self.assertIsNotNone(dispatch.clarifying_question)
        self.assertIn("property type", dispatch.clarifying_question.lower())
        self.assertEqual(dispatch.system_blocks, [])
        self.assertEqual(dispatch.route, ())

    def test_no_clarifying_question_when_context_complete(self):
        """All required fields populated → no clarifying question, full route."""
        ctx = LeaseContext(
            intent=IntentEnum.GENERATE,
            user_message="draft me a sectional title lease",
            property_type="sectional_title",
            tenant_count=1,
            lease_type="fixed_term",
        )
        dispatch = build_dispatch(ctx)

        self.assertIsNone(dispatch.clarifying_question)
        self.assertEqual(len(dispatch.system_blocks), 3)
        self.assertEqual(dispatch.route, ("drafter", "reviewer"))


class CacheControlMarkerTests(unittest.TestCase):
    """Decision 18 invariant: every system block must be cacheable."""

    def test_three_system_blocks_have_cache_control_markers(self):
        """All three blocks (persona, merge-fields, RAG) MUST carry
        ``cache_control={"type":"ephemeral"}``."""
        ctx = LeaseContext(
            intent=IntentEnum.GENERATE,
            user_message="draft me a sectional title lease",
            property_type="sectional_title",
            tenant_count=1,
            lease_type="fixed_term",
        )
        dispatch = build_dispatch(ctx)

        self.assertEqual(len(dispatch.system_blocks), 3)
        for idx, block in enumerate(dispatch.system_blocks):
            with self.subTest(block_idx=idx):
                self.assertIn("cache_control", block)
                self.assertEqual(
                    block["cache_control"],
                    {"type": "ephemeral"},
                    f"Block {idx} cache_control must be ephemeral.",
                )
                self.assertEqual(block.get("type"), "text")
                self.assertGreater(len(block.get("text", "")), 0)


class FrontDoorRAGFallbackTests(unittest.TestCase):
    """Wave 2A — RAG corpus missing → placeholder + warning, not silence."""

    def test_front_door_rag_fallback_when_corpus_missing(self):
        """When ``query_clauses`` raises ``RuntimeError`` (corpus not
        indexed / Chroma down), the Front Door MUST:

          * Log a ``logger.warning("RAG corpus not indexed; ...")``.
          * Render the
            :data:`RAG_CORPUS_UNAVAILABLE_PLACEHOLDER` string into the
            RAG block so the 3-block cache layout (decision 18) is
            preserved.
        """
        from apps.leases import lease_law_corpus_queries
        from apps.leases.agents.front_door import (
            RAG_CORPUS_UNAVAILABLE_PLACEHOLDER,
        )

        original_clauses = lease_law_corpus_queries.query_clauses

        def _raise(**kwargs):
            raise RuntimeError("ChromaDB collection not initialised.")

        lease_law_corpus_queries.query_clauses = _raise

        try:
            from apps.leases.agents.front_door import build_dispatch

            ctx = LeaseContext(
                intent=IntentEnum.GENERATE,
                user_message="draft me a sectional title lease",
                property_type="sectional_title",
                tenant_count=1,
                lease_type="fixed_term",
            )
            with self.assertLogs(
                "apps.leases.agents.front_door", level="WARNING"
            ) as captured:
                dispatch = build_dispatch(ctx)

            self.assertEqual(len(dispatch.system_blocks), 3)
            rag_block = dispatch.system_blocks[2]["text"]
            self.assertIn(RAG_CORPUS_UNAVAILABLE_PLACEHOLDER, rag_block)
            # The warning was actually emitted.
            self.assertTrue(
                any("RAG corpus not indexed" in msg for msg in captured.output),
                f"Expected a 'RAG corpus not indexed' warning; got: "
                f"{captured.output}",
            )
        finally:
            lease_law_corpus_queries.query_clauses = original_clauses


if __name__ == "__main__":
    unittest.main()
