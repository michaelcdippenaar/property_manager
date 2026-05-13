"""Public read-API for the centralised legal RAG store.

This module locks the **signatures** that every consumer will call. The
in-process Python implementation here is v1; the v2 MCP server (Phase B)
preserves these signatures verbatim.

See ``content/cto/centralised-legal-rag-store-plan.md`` §6 for the full
contract description and §11 for the tech stack picks (PostgreSQL via
Django ORM for keyed lookups, ChromaDB ``klikk_legal_v1`` collection for
semantic retrieval).

Consumer rules — read these before calling anything:

  - Every return value is a frozen :class:`LegalFact` dataclass — never
    the ORM model. The dataclass is the stable contract; the ORM model is
    internal-only and not safe to mutate from consumer code.
  - ``disclaimers`` is mandatory output. Every consumer surface must
    render the disclaimers attached to a fact. POPIA s17/18 openness
    bar — do not strip them.
  - ``LegalFactNotFound`` is the only "soft miss". There is NO implicit
    fallback to a "best effort" fact. Catch it explicitly.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import reduce
from operator import or_
from typing import Any, Literal

from django.db.models import Q

from .exceptions import LegalFactNotFound
from .models import LegalCorpusVersion
from .models import LegalFact as LegalFactModel
from .models import LegalFactVersion


# ── Confidence ordering ─────────────────────────────────────────────── #


_CONFIDENCE_RANK: dict[str, int] = {"high": 3, "medium": 2, "low": 1}


# ── Stable consumer dataclass ───────────────────────────────────────── #


@dataclass(frozen=True)
class LegalFact:
    """The stable contract returned to consumers.

    Mirrors plan §6 "Response shape — what a consumer gets back". 18 fields,
    immutable so consumers cannot accidentally mutate a cached object.
    """

    concept_id: str
    type: Literal["statute_provision", "case_law", "pitfall", "concept"]
    citation_string: str
    plain_english_summary: str
    statute_text: str | None
    statute_text_verbatim: bool
    citation_confidence: Literal["high", "medium", "low"]
    legal_provisional: bool
    provisional_reason: str | None
    verification_status: Literal["ai_curated", "mc_reviewed", "lawyer_reviewed"]
    attested_by: str | None
    attested_at: date | None
    applicability: dict[str, Any]
    topic_tags: tuple[str, ...]
    related_concepts: tuple[str, ...]
    sources: tuple[dict[str, Any], ...]
    disclaimers: tuple[str, ...]
    fact_version: int
    corpus_version: str
    effective_from: date | None
    last_verified_at: date | None


# ── ORM → dataclass adapter ─────────────────────────────────────────── #


def _to_dataclass(
    fact: LegalFactModel,
    *,
    version: LegalFactVersion | None = None,
) -> LegalFact:
    """Materialise an ORM ``LegalFactModel`` into the stable dataclass.

    Pulls fields the ORM doesn't denormalise (``related_concepts``,
    ``sources``, ``effective_from``, ``last_verified_at``,
    ``provisional_reason``, ``attested_by``, ``attested_at``) from the
    JSON payload on the matched ``LegalFactVersion`` row.

    Args:
        fact: the ORM row.
        version: the specific ``LegalFactVersion`` to use as the JSON
            source. Defaults to ``fact.current_version``.
    """
    version = version or fact.current_version
    payload: dict[str, Any] = (version.content if version is not None else {}) or {}

    effective_from = _parse_iso_date(payload.get("effective_from"))
    last_verified_at = _parse_iso_date(payload.get("last_verified_at"))
    attested_at = _parse_iso_date(payload.get("attested_at"))

    return LegalFact(
        concept_id=fact.concept_id,
        type=fact.type,  # type: ignore[arg-type]
        citation_string=fact.citation_string,
        plain_english_summary=fact.plain_english_summary,
        statute_text=fact.statute_text or None,
        statute_text_verbatim=bool(fact.statute_text_verbatim),
        citation_confidence=fact.citation_confidence,  # type: ignore[arg-type]
        legal_provisional=bool(fact.legal_provisional),
        provisional_reason=payload.get("provisional_reason"),
        verification_status=fact.verification_status,  # type: ignore[arg-type]
        attested_by=payload.get("attested_by"),
        attested_at=attested_at,
        applicability=dict(fact.applicability or {}),
        topic_tags=tuple(fact.topic_tags or []),
        related_concepts=tuple(payload.get("related_concepts") or []),
        sources=tuple(payload.get("sources") or []),
        disclaimers=tuple(fact.disclaimers or []),
        fact_version=int(fact.fact_version),
        corpus_version=(
            fact.corpus_version.version if fact.corpus_version_id else ""
        ),
        effective_from=effective_from,
        last_verified_at=last_verified_at,
    )


def _parse_iso_date(value: Any) -> date | None:
    """Best-effort parse of an ISO date string back to a ``date``.

    Returns ``None`` for missing or unparseable values. Used because the
    YAML loader keeps dates as strings (so the schema validator is happy)
    but consumers expect ``datetime.date`` instances on the dataclass.
    """
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


# ── Citation normalisation ──────────────────────────────────────────── #


def _normalise_citation(citation: str) -> str:
    """Strip whitespace, collapse internal whitespace, preserve case.

    The canonical citation_string is already case-correct (RHA / POPIA /
    etc.). Consumers may pass " RHA s7 " or "rha s7" — we want both to
    match the canonical entry.
    """
    if not citation:
        return ""
    return " ".join(citation.split()).strip()


# ── Statute lookup ──────────────────────────────────────────────────── #


def query_statute(
    citation: str,
    *,
    at_date: date | None = None,
) -> LegalFact:
    """Look up a statute provision by canonical citation string.

    Returns the latest fact version effective at ``at_date`` (defaults to
    today). Raises :class:`LegalFactNotFound` if the citation is not in
    the corpus.

    Example::

        fact = query_statute("RHA s7")
        fact.plain_english_summary
        fact.citation_confidence   # "high"
        fact.legal_provisional     # False
        fact.disclaimers           # ("Not legal advice. ...",)
    """
    target = _normalise_citation(citation)
    if not target:
        raise LegalFactNotFound("citation must be a non-empty string")

    qs = LegalFactModel.objects.filter(
        is_active=True,
        citation_string__iexact=target,
    ).select_related("current_version", "corpus_version")
    fact = qs.first()
    if fact is None:
        raise LegalFactNotFound(
            f"No legal fact found for citation {citation!r}"
        )

    version = _version_effective_at(fact, at_date=at_date)
    return _to_dataclass(fact, version=version)


def query_concept(
    concept_id: str,
    *,
    at_date: date | None = None,
) -> LegalFact:
    """Look up a legal fact by stable ``concept_id`` (kebab-case slug)."""
    if not concept_id:
        raise LegalFactNotFound("concept_id must be a non-empty string")
    fact = (
        LegalFactModel.objects.filter(is_active=True, concept_id=concept_id)
        .select_related("current_version", "corpus_version")
        .first()
    )
    if fact is None:
        raise LegalFactNotFound(
            f"No legal fact found for concept_id {concept_id!r}"
        )
    version = _version_effective_at(fact, at_date=at_date)
    return _to_dataclass(fact, version=version)


def _version_effective_at(
    fact: LegalFactModel,
    *,
    at_date: date | None,
) -> LegalFactVersion | None:
    """Pick the ``LegalFactVersion`` effective at ``at_date``.

    Walks the fact's version history newest-first; returns the first
    version whose ``effective_from <= at_date``. ``at_date`` defaults to
    today. Falls back to ``fact.current_version`` if nothing matches —
    which preserves the v1 behaviour from the placeholder query API.
    """
    if at_date is None:
        return fact.current_version

    versions = list(
        fact.versions.all().order_by("-version")
    )
    for version in versions:
        eff_value = (version.content or {}).get("effective_from")
        eff_date = _parse_iso_date(eff_value)
        if eff_date is None:
            # Versions without a valid effective_from are skipped during
            # at_date resolution but still listed by current_version.
            continue
        if eff_date <= at_date:
            return version
    return fact.current_version


# ── Topic + filter retrieval ────────────────────────────────────────── #


def query_facts_by_topic(
    topic_tags: list[str],
    *,
    statute: str | None = None,
    min_confidence: Literal["high", "medium", "low"] = "medium",
    include_provisional: bool = False,
    k: int = 10,
) -> list[LegalFact]:
    """Tag-and-filter retrieval against the active corpus.

    ``topic_tags`` matches *any* of the requested tags (OR semantics). Use
    a single-element list for AND-on-one-tag retrieval.
    """
    if not topic_tags:
        return []

    if min_confidence not in _CONFIDENCE_RANK:
        raise ValueError(f"min_confidence={min_confidence!r} invalid")
    confidence_floor = _CONFIDENCE_RANK[min_confidence]
    allowed_confidences = [
        level
        for level, rank in _CONFIDENCE_RANK.items()
        if rank >= confidence_floor
    ]

    qs = LegalFactModel.objects.filter(
        is_active=True,
        citation_confidence__in=allowed_confidences,
    )
    # JSONField doesn't support `__overlap` — emulate OR-on-any-tag with
    # one `__contains=[tag]` Q per requested tag. PostgreSQL's @> handles
    # array containment efficiently with the JSONField GIN index.
    tag_filters = reduce(
        or_, (Q(topic_tags__contains=[tag]) for tag in topic_tags)
    )
    qs = qs.filter(tag_filters)
    if not include_provisional:
        qs = qs.filter(legal_provisional=False)

    qs = qs.select_related("current_version", "corpus_version").order_by(
        "-updated_at", "concept_id"
    )

    results: list[LegalFact] = []
    seen_ids: set[str] = set()
    statute_prefix = statute.upper().strip() if statute else None
    for fact in qs.iterator():
        if statute_prefix is not None:
            prefix = _statute_prefix_from_citation(fact.citation_string)
            if prefix != statute_prefix:
                continue
        if fact.concept_id in seen_ids:
            continue
        seen_ids.add(fact.concept_id)
        results.append(_to_dataclass(fact))
        if len(results) >= k:
            break
    return results


def _statute_prefix_from_citation(citation: str) -> str:
    if not citation:
        return ""
    head = citation.split(" ", 1)[0]
    if head in {"RHA", "POPIA", "CPA", "PIE", "STSMA", "CSOS"}:
        return head
    return ""


# ── Semantic retrieval (ChromaDB) ────────────────────────────────────── #


def query_semantic(
    natural_query: str,
    *,
    fact_types: list[Literal["statute_provision", "case_law", "pitfall", "concept"]]
    | None = None,
    min_confidence: Literal["high", "medium", "low"] = "medium",
    k: int = 10,
) -> list[LegalFact]:
    """Embedding-similarity retrieval via the ``klikk_legal_v1`` collection.

    Returns up to ``k`` LegalFact dataclasses ordered by descending
    similarity. Returns an empty list if the ChromaDB collection has not
    yet been built or if the import fails (e.g. running tests without
    ChromaDB installed).
    """
    if not natural_query or not natural_query.strip():
        return []

    if min_confidence not in _CONFIDENCE_RANK:
        raise ValueError(f"min_confidence={min_confidence!r} invalid")
    confidence_floor = _CONFIDENCE_RANK[min_confidence]
    allowed_confidences = [
        level
        for level, rank in _CONFIDENCE_RANK.items()
        if rank >= confidence_floor
    ]

    try:
        import chromadb  # type: ignore[import-not-found]
        from django.conf import settings
    except Exception:  # noqa: BLE001 — ChromaDB unavailable -> empty result
        return []

    try:
        from apps.legal_rag.management.commands.reindex_legal_corpus import (
            COLLECTION_NAME,
        )
    except Exception:  # noqa: BLE001
        COLLECTION_NAME = "klikk_legal_v1"  # noqa: N806

    try:
        persist_path = str(settings.LEGAL_RAG_CHROMA_PATH)
        client = chromadb.PersistentClient(path=persist_path)
        col = client.get_or_create_collection(
            name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )
    except Exception:  # noqa: BLE001
        return []

    where_clauses: list[dict[str, Any]] = [
        {"citation_confidence": {"$in": allowed_confidences}},
    ]
    if fact_types:
        where_clauses.append({"type": {"$in": list(fact_types)}})
    where = where_clauses[0] if len(where_clauses) == 1 else {"$and": where_clauses}

    try:
        result = col.query(
            query_texts=[natural_query],
            n_results=max(1, int(k)),
            where=where,
        )
    except Exception:  # noqa: BLE001 — ChromaDB error -> empty result
        return []

    matches = (result.get("ids") or [[]])[0]
    if not matches:
        return []

    # Preserve ChromaDB's similarity-ordered concept_ids.
    fact_map = {
        f.concept_id: f
        for f in LegalFactModel.objects.filter(
            is_active=True, concept_id__in=matches
        ).select_related("current_version", "corpus_version")
    }
    ordered: list[LegalFact] = []
    for cid in matches:
        fact = fact_map.get(cid)
        if fact is None:
            continue
        ordered.append(_to_dataclass(fact))
    return ordered


# ── Case-law retrieval ─────────────────────────────────────────────── #


def query_case_law(
    topic_tags: list[str] | None = None,
    jurisdiction: str | None = None,
    since_year: int | None = None,
    natural_query: str | None = None,
    k: int = 10,
) -> list[LegalFact]:
    """Filter the corpus to ``type='case_law'`` rows.

    Day 3 scope: no case_law facts exist in the seeded corpus yet — this
    function returns an empty list cleanly until they land. The
    ``jurisdiction`` / ``since_year`` / ``natural_query`` parameters are
    accepted for signature stability; their filter semantics activate
    when case_law facts are seeded.
    """
    qs = LegalFactModel.objects.filter(
        is_active=True, type="case_law"
    ).select_related("current_version", "corpus_version").order_by(
        "-updated_at", "concept_id"
    )
    if topic_tags:
        tag_filters = reduce(
            or_, (Q(topic_tags__contains=[tag]) for tag in topic_tags)
        )
        qs = qs.filter(tag_filters)

    results: list[LegalFact] = []
    for fact in qs.iterator():
        payload = (fact.current_version.content if fact.current_version else {}) or {}
        if jurisdiction is not None:
            applicability = payload.get("applicability") or {}
            jurisdictions = applicability.get("jurisdictions") or []
            if jurisdiction not in jurisdictions:
                continue
        if since_year is not None:
            eff = _parse_iso_date(payload.get("effective_from"))
            if eff is None or eff.year < since_year:
                continue
        results.append(_to_dataclass(fact))
        if len(results) >= k:
            break
    return results


# ── Pitfall patterns ───────────────────────────────────────────────── #


def list_pitfall_patterns(
    topic_tags: list[str] | None = None,
) -> list[LegalFact]:
    """List ``type='pitfall'`` facts, optionally filtered by topic tag.

    Day 3 scope: no pitfall facts seeded yet — returns an empty list.
    Adding pitfall YAMLs to ``content/legal/pitfalls/`` and re-running
    ``sync_legal_facts`` enables this without code changes.
    """
    qs = LegalFactModel.objects.filter(
        is_active=True, type="pitfall"
    ).select_related("current_version", "corpus_version").order_by(
        "-updated_at", "concept_id"
    )
    if topic_tags:
        tag_filters = reduce(
            or_, (Q(topic_tags__contains=[tag]) for tag in topic_tags)
        )
        qs = qs.filter(tag_filters)
    return [_to_dataclass(fact) for fact in qs.iterator()]


# ── Snapshot view ──────────────────────────────────────────────────── #


def list_facts_at_version(corpus_version: str) -> list[LegalFact]:
    """Return every fact's content as it stood at the given corpus version.

    Used by the audit log to reconstruct what the corpus said when a
    given lease was generated (per the lease-AI architecture decision 6).
    """
    if not corpus_version:
        return []
    cv = LegalCorpusVersion.objects.filter(version=corpus_version).first()
    if cv is None:
        return []

    facts = list(
        LegalFactModel.objects.filter(
            corpus_version=cv,
        ).select_related("current_version", "corpus_version").order_by("concept_id")
    )
    return [_to_dataclass(fact) for fact in facts]


__all__ = [
    "LegalFact",
    "LegalFactNotFound",
    "query_statute",
    "query_concept",
    "query_facts_by_topic",
    "query_semantic",
    "query_case_law",
    "list_pitfall_patterns",
    "list_facts_at_version",
]
