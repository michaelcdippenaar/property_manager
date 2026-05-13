"""Public read-API for the centralised legal RAG store.

This module locks the **signatures** that every consumer will call.
Implementations land in Day 3+ of Phase A, after ``sync_legal_facts``
populates the runtime cache. Until then every function raises
``NotImplementedError`` — call sites should fail loudly during the
scaffold period rather than silently return empty.

See plan §6 for the full contract description. The signatures here
are the stable v1 surface; the v2 MCP server (Phase B) will preserve
them verbatim.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from .exceptions import LegalFactNotFound  # noqa: F401 (re-export for consumers)
from .models import LegalFact


def query_statute(
    citation: str,
    *,
    at_date: date | None = None,
) -> LegalFact:
    """Look up a statute provision by canonical citation string.

    Returns the latest version effective at ``at_date`` (defaults to today).
    Raises ``LegalFactNotFound`` if the citation is not in the corpus.

    Example::

        fact = query_statute("RHA s5(3)(f)")
        fact.plain_english_summary
        fact.citation_confidence   # "low"
        fact.legal_provisional     # True
        fact.disclaimers           # ["Not legal advice.", ...]
    """
    raise NotImplementedError(
        "Phase A Day 3+: implement after sync_legal_facts lands"
    )


def query_concept(
    concept_id: str,
    *,
    at_date: date | None = None,
) -> LegalFact:
    """Look up a fact by stable concept_id (kebab-case).

    Used when the consumer knows the internal slug rather than the
    citation_string (e.g. cross-statute concepts that span multiple
    sections of multiple Acts).
    """
    raise NotImplementedError(
        "Phase A Day 3+: implement after sync_legal_facts lands"
    )


def query_facts_by_topic(
    topic_tags: list[str],
    *,
    statute: str | None = None,
    min_confidence: Literal["high", "medium", "low"] = "medium",
    include_provisional: bool = False,
    k: int = 10,
) -> list[LegalFact]:
    """Tag-and-filter retrieval.

    Used by the lease-AI Drafter to pull e.g. "all the deposit-related
    facts for a sectional-title lease" before assembling clauses.
    """
    raise NotImplementedError(
        "Phase A Day 3+: implement after sync_legal_facts lands"
    )


def query_semantic(
    natural_query: str,
    *,
    fact_types: list[Literal["statute_provision", "case_law", "pitfall", "concept"]]
    | None = None,
    min_confidence: Literal["high", "medium", "low"] = "medium",
    k: int = 10,
) -> list[LegalFact]:
    """Embedding-similarity retrieval via ChromaDB.

    Used by the lease-AI Reviewer when it doesn't know which citation
    to look up. Backed by the ``klikk_legal_v1`` ChromaDB collection
    (populated by ``manage.py reindex_legal_corpus`` — Day 4+).
    """
    raise NotImplementedError(
        "Phase A Day 3+: implement after sync_legal_facts lands"
    )


def query_case_law(
    topic_tags: list[str] | None = None,
    jurisdiction: str | None = None,
    since_year: int | None = None,
    natural_query: str | None = None,
    k: int = 10,
) -> list[LegalFact]:
    """Case-law retrieval — tag/jurisdiction/year filter + optional semantic.

    Returns ``LegalFact`` rows with ``type='case_law'``.
    """
    raise NotImplementedError(
        "Phase A Day 3+: implement after sync_legal_facts lands"
    )


def list_pitfall_patterns(
    topic_tags: list[str] | None = None,
) -> list[LegalFact]:
    """List pitfall patterns, optionally filtered by topic tags.

    Returns ``LegalFact`` rows with ``type='pitfall'``.
    """
    raise NotImplementedError(
        "Phase A Day 3+: implement after sync_legal_facts lands"
    )


def list_facts_at_version(corpus_version: str) -> list[LegalFact]:
    """Snapshot view — every fact's content at a given corpus version.

    Used by the audit log when reconstructing "what did the corpus look
    like when this lease was generated". Per-lease ``corpus_version`` is
    persisted on ``AILeaseAgentRun`` so this lookup is stable.
    """
    raise NotImplementedError(
        "Phase A Day 3+: implement after sync_legal_facts lands"
    )


__all__ = [
    "LegalFactNotFound",
    "query_statute",
    "query_concept",
    "query_facts_by_topic",
    "query_semantic",
    "query_case_law",
    "list_pitfall_patterns",
    "list_facts_at_version",
]
