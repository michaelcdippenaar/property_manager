"""Front Door — pure-Python coordinator for the lease-AI cluster.

Per ``docs/system/lease-ai-agent-architecture.md`` §5.1 the Front Door is
a Python coordinator (NOT an LLM call). Responsibilities:

  1. Classify the user's intent from message + chat history (heuristic
     keyword matching — promote to a haiku call only if routing grows
     complex).
  2. Detect missing required context for the chosen intent — return a
     clarifying question if any required field is None and do nothing
     else this turn.
  3. Build the three cached system blocks every Drafter / Reviewer call
     receives (persona + merge-fields + RAG-chunks), each tagged with
     ``cache_control: {"type": "ephemeral"}`` per decision 18 + §6.6.
  4. Pull RAG chunks (clauses + statutes) so the Drafter receives them
     by push, and the Reviewer receives the same statute set so the
     review is grounded in the same law the Drafter was working from.
  5. Decide the route — which agent(s) to dispatch.

Phase 2 Day 1-2 scope: classification + system-block assembly +
clarifying-question detection + route selection. Live RAG calls are
guarded (any exception is swallowed → empty list) so the harness keeps
working under cassette replay where the corpus may not be indexed.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from apps.leases.agents.context import IntentEnum, LeaseContext
from apps.leases.agents.drafter import PERSONA as DRAFTER_PERSONA
from apps.leases.agents.reviewer import PERSONA as REVIEWER_PERSONA

logger = logging.getLogger(__name__)


# ── Intent classification keyword table ──────────────────────────────── #


# Architecture §5.1 — heuristic intent classification. Order matters:
# the first regex/keyword to match wins, so put narrow intents above
# broad ones (e.g. ``audit_case_law`` before ``audit``).
#
# Each row: (intent, set of trigger-substrings, set of phrase-fragments
# that must NOT appear). The "not" set lets us exclude false positives
# (e.g. "audit my draft" → audit; "draft an audit clause" → generate).
_INTENT_KEYWORDS: tuple[tuple[IntentEnum, frozenset[str], frozenset[str]], ...] = (
    (
        IntentEnum.AUDIT_CASE_LAW,
        frozenset({"case law", "case-law", "tribunal decisions", "rht ruling"}),
        frozenset(),
    ),
    (
        IntentEnum.AUDIT,
        frozenset(
            {
                "audit my lease",
                "is this compliant",
                "is this lease compliant",
                "review this lease",
                "review my lease",
                "audit the lease",
                "compliance check",
                "audit",
            }
        ),
        frozenset({"draft", "write", "generate", "create"}),
    ),
    (
        IntentEnum.FORMAT,
        frozenset(
            {
                "headings bigger",
                "add a toc",
                "table of contents",
                "running header",
                "page break",
                "format the document",
                "reformat",
                "restructure layout",
            }
        ),
        frozenset({"rewrite", "edit"}),
    ),
    (
        IntentEnum.INSERT_CLAUSE,
        frozenset(
            {
                "add a clause",
                "add a no-pets clause",
                "add a guarantor",
                "add a no pets clause",
                "insert clause",
                "add clause",
                "add a section",
            }
        ),
        frozenset(),
    ),
    (
        IntentEnum.EDIT,
        frozenset(
            {
                "fix the",
                "rewrite line",
                "rewrite the",
                "edit line",
                "change line",
                "update the deposit clause",
                "tweak",
            }
        ),
        frozenset(),
    ),
    (
        IntentEnum.GENERATE,
        frozenset(
            {
                "write me a lease",
                "write a lease",
                "draft a lease",
                "draft me a lease",
                "draft a sectional title",
                "draft a sectional-title",
                "generate a lease",
                "generate me a lease",
                "create a lease",
                "make me a lease",
                "draw up a lease",
            }
        ),
        frozenset(),
    ),
    (
        IntentEnum.ANSWER,
        frozenset(
            {
                "what does rha",
                "what does popia",
                "what does cpa",
                "what is rha",
                "explain rha",
                "what fields are available",
                "list the merge fields",
                "what merge fields",
            }
        ),
        frozenset(),
    ),
)


# Required fields per intent. Front Door asks a clarifying question if
# any of these are None.
_REQUIRED_BY_INTENT: dict[IntentEnum, frozenset[str]] = {
    IntentEnum.GENERATE: frozenset({"property_type", "tenant_count", "lease_type"}),
    IntentEnum.INSERT_CLAUSE: frozenset({"property_type"}),
    IntentEnum.EDIT: frozenset(),
    IntentEnum.FORMAT: frozenset(),
    IntentEnum.AUDIT: frozenset(),
    IntentEnum.AUDIT_CASE_LAW: frozenset(),
    IntentEnum.ANSWER: frozenset(),
}


# ── Routes ───────────────────────────────────────────────────────────── #


# Pipeline routes per architecture §8.2. ``("drafter",)`` means single
# Drafter call. ``("drafter", "reviewer")`` means Drafter then Reviewer
# gate (with possible 1-retry per decision 10).
_ROUTE_BY_INTENT: dict[IntentEnum, tuple[str, ...]] = {
    IntentEnum.GENERATE: ("drafter", "reviewer"),
    IntentEnum.EDIT: ("drafter",),
    IntentEnum.INSERT_CLAUSE: ("drafter",),
    IntentEnum.FORMAT: ("formatter",),
    IntentEnum.AUDIT: ("reviewer",),
    IntentEnum.AUDIT_CASE_LAW: ("reviewer",),
    IntentEnum.ANSWER: ("drafter",),
}


# ── Dispatch dataclass ───────────────────────────────────────────────── #


@dataclass(frozen=True)
class FrontDoorDispatch:
    """Return value of :func:`build_dispatch`.

    Carries everything the view needs to either ship a clarifying
    question (``clarifying_question is not None`` → return JSON,
    no SSE) or kick off the pipeline (``clarifying_question is None``
    → stream events).

    Fields:
      * ``context``           — frozen :class:`LeaseContext`.
      * ``system_blocks``     — list of dicts ready to pass as the
        ``system=`` kwarg on ``messages.create``. Three blocks: persona,
        merge-fields, RAG-chunks. Each carries
        ``cache_control: {"type": "ephemeral"}`` per §6.6.
      * ``pushed_clauses``    — list of clause-chunk dicts inlined into
        the Drafter's RAG block. Empty when retrieval failed (Phase 2
        Day 1-2 — corpus may not be indexed yet).
      * ``pushed_statutes``   — list of statute-fact dicts ditto.
      * ``route``             — agent dispatch order (e.g.
        ``("drafter", "reviewer")``).
      * ``clarifying_question`` — non-None when required context is
        missing; the view should return it as a JSON response.
    """

    context: LeaseContext
    system_blocks: list[dict[str, Any]]
    pushed_clauses: list[dict[str, Any]]
    pushed_statutes: list[dict[str, Any]]
    route: tuple[str, ...]
    clarifying_question: str | None = None
    intent_label: str = ""

    # Sub-block strings (kept for tests + caching telemetry).
    _persona_text: str = field(default="", repr=False)
    _merge_fields_text: str = field(default="", repr=False)
    _rag_text: str = field(default="", repr=False)


# ── Public surface ──────────────────────────────────────────────────── #


def classify_intent(user_message: str) -> IntentEnum:
    """Map a user message to a :class:`IntentEnum` value.

    Pure heuristic. The match priority follows ``_INTENT_KEYWORDS`` —
    longest-match-first, with explicit negative keywords that disqualify
    a row (so "draft an audit clause" doesn't trip ``AUDIT``).

    Defaults to :attr:`IntentEnum.ANSWER` when nothing matches — the
    Drafter Q&A persona will then either answer the question or politely
    ask for clarification.
    """
    haystack = (user_message or "").lower()
    if not haystack.strip():
        return IntentEnum.ANSWER

    for intent, includes, excludes in _INTENT_KEYWORDS:
        if any(bad in haystack for bad in excludes):
            continue
        if any(needle in haystack for needle in includes):
            return intent

    return IntentEnum.ANSWER


def build_dispatch(context: LeaseContext) -> FrontDoorDispatch:
    """Build the dispatch object the view consumes.

    Steps:
      1. Resolve required-field gaps; if any → clarifying-question route.
      2. Pull RAG chunks (clauses + statutes) under broad except so
         retrieval failure doesn't fail the request — the Drafter just
         sees an empty RAG block in that turn.
      3. Build the three cached system blocks.
      4. Pick the route per intent.

    The result is fully constructed even when retrieval fails — the
    Drafter call still goes out, just with the empty RAG section.
    """
    gaps = context.gaps(_required_for_intent(context.intent))
    if gaps:
        question = _build_clarifying_question(context, sorted(gaps))
        return FrontDoorDispatch(
            context=context,
            system_blocks=[],
            pushed_clauses=[],
            pushed_statutes=[],
            route=(),
            clarifying_question=question,
            intent_label=context.intent.value,
        )

    pushed_clauses = _pull_clauses(context)
    pushed_statutes = _pull_statutes(context)

    # Pick the agent persona for the leading agent. The Reviewer is the
    # leading agent for audit intents; everything else leads with the
    # Drafter. The third (RAG) block is shared either way; the merge-
    # fields block is only relevant to the Drafter but inlining it on
    # both calls keeps the cache layout uniform.
    is_review_leading = context.intent in {
        IntentEnum.AUDIT,
        IntentEnum.AUDIT_CASE_LAW,
    }
    persona_text = REVIEWER_PERSONA if is_review_leading else DRAFTER_PERSONA

    merge_fields_text = _build_merge_fields_block(context)
    rag_text = _build_rag_chunks_block(pushed_clauses, pushed_statutes)

    system_blocks: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": persona_text,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": merge_fields_text,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": rag_text,
            "cache_control": {"type": "ephemeral"},
        },
    ]

    return FrontDoorDispatch(
        context=context,
        system_blocks=system_blocks,
        pushed_clauses=pushed_clauses,
        pushed_statutes=pushed_statutes,
        route=_ROUTE_BY_INTENT.get(context.intent, ("drafter",)),
        clarifying_question=None,
        intent_label=context.intent.value,
        _persona_text=persona_text,
        _merge_fields_text=merge_fields_text,
        _rag_text=rag_text,
    )


# ── Internals ────────────────────────────────────────────────────────── #


def _required_for_intent(intent: IntentEnum) -> frozenset[str]:
    """Required-fields lookup. Defaults to the empty set so unknown
    intents (added in a future Phase) don't accidentally block routing.
    """
    return _REQUIRED_BY_INTENT.get(intent, frozenset())


def _build_clarifying_question(context: LeaseContext, gaps: list[str]) -> str:
    """Render a polite clarifying question listing the missing fields.

    The Front Door is a Python coordinator, so we hand-roll the prose
    rather than asking an LLM. The user replies on the next turn; the
    view re-runs the Front Door which now has the answers in
    ``chat_history`` and proceeds.
    """
    pretty = ", ".join(name.replace("_", " ") for name in gaps)
    return (
        "I need a couple of details before I can put together the lease — "
        f"specifically: {pretty}. "
        "Could you let me know each of those so I can continue?"
    )


def _pull_clauses(context: LeaseContext) -> list[dict[str, Any]]:
    """Pull clause chunks from ``lease_law_corpus_queries.query_clauses``.

    Defensive: if Chroma isn't installed / indexed / reachable, return
    an empty list. The harness's cassette replay path uses a stable
    system block (deterministic) — Phase 2 Day 3+ will reshape this once
    the corpus is real.
    """
    try:
        from apps.leases.lease_law_corpus_queries import query_clauses

        chunks = query_clauses(
            topic_tags=list(context.conditions) or None,
            property_type=context.property_type,
            tenant_count=context.tenant_count,
            lease_type=context.lease_type,
            k=20,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Front Door: query_clauses failed; using empty push.")
        return []

    out: list[dict[str, Any]] = []
    for chunk in chunks:
        out.append(
            {
                "id": chunk.id,
                "clause_title": chunk.clause_title,
                "clause_body": chunk.clause_body,
                "topic_tags": list(chunk.topic_tags),
                "related_citations": list(chunk.related_citations),
                "citation_confidence": chunk.citation_confidence,
            }
        )
    return out


def _pull_statutes(context: LeaseContext) -> list[dict[str, Any]]:
    """Pull statute facts from ``apps.legal_rag.queries.query_facts_by_topic``.

    Same defensive shape as :func:`_pull_clauses`.
    """
    try:
        from apps.legal_rag.queries import query_facts_by_topic

        topics = list(context.conditions) or ["deposit"]
        facts = query_facts_by_topic(
            topic_tags=topics,
            statute="RHA",
            min_confidence="medium",
            include_provisional=False,
            k=10,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Front Door: query_facts_by_topic failed; using empty push.")
        return []

    out: list[dict[str, Any]] = []
    for fact in facts:
        out.append(
            {
                "concept_id": fact.concept_id,
                "citation": fact.citation_string,
                "summary": fact.plain_english_summary,
                "citation_confidence": fact.citation_confidence,
                "legal_provisional": fact.legal_provisional,
            }
        )
    return out


def _build_merge_fields_block(context: LeaseContext) -> str:
    """Render the cached merge-fields block (§6.6).

    Uses the YAML-backed
    :func:`apps.leases.merge_fields_loader.filter_by_context` +
    :func:`render_for_drafter_system_block` so the block stays
    deterministic for a given context (cache-friendly) and is capped
    under 4 kB by the loader's own budget invariants.
    """
    try:
        from apps.leases.merge_fields_loader import (
            filter_by_context,
            render_for_drafter_system_block,
        )

        tenant_count = context.tenant_count or 1
        property_type = context.property_type or "sectional_title"
        lease_type = context.lease_type or "fixed_term"
        fields = filter_by_context(
            tenant_count=tenant_count,
            property_type=property_type,
            lease_type=lease_type,
        )
        return render_for_drafter_system_block(fields)
    except Exception:  # noqa: BLE001
        logger.exception(
            "Front Door: merge-fields render failed; using empty block."
        )
        return "## Available merge fields\n\n_(merge fields catalogue unavailable)_\n"


def _build_rag_chunks_block(
    clauses: list[dict[str, Any]], statutes: list[dict[str, Any]]
) -> str:
    """Render the cached RAG-chunks block.

    Compact, deterministic format. Same Context Object always produces
    the same string so the block is cacheable.
    """
    if not clauses and not statutes:
        return "## Pushed legal corpus\n\n_(no chunks retrieved for this context)_\n"

    lines: list[str] = ["## Pushed legal corpus", ""]
    if statutes:
        lines.append("### Statute facts")
        for s in statutes:
            tag = (
                " [provisional]"
                if s.get("legal_provisional")
                else f" ({s.get('citation_confidence', 'medium')})"
            )
            lines.append(f"- **{s['citation']}**{tag} — {s['summary']}")
        lines.append("")
    if clauses:
        lines.append("### Clause chunks")
        for c in clauses:
            cites = ", ".join(c.get("related_citations") or [])
            cite_tag = f" — {cites}" if cites else ""
            lines.append(f"- `{c['id']}` **{c['clause_title']}**{cite_tag}")
        lines.append("")
    return "\n".join(lines) + "\n"


__all__ = [
    "FrontDoorDispatch",
    "build_dispatch",
    "classify_intent",
]
