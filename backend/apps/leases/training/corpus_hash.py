"""Compute the combined corpus_version hash for the lease-AI training harness.

The lease-AI pipeline reads from TWO corpora:

1. ``apps.leases.lease_law_corpus`` — clause chunks. Its
   ``manage.py reindex_lease_corpus`` writes
   ``backend/lease_ai_chroma/.last_index.json`` with the current corpus
   hash + indexed-fact-count + timestamp.
2. ``apps.legal_rag`` — statute facts, case-law, pitfalls. Its
   ``manage.py reindex_legal_corpus`` writes
   ``backend/legal_rag_chroma/.last_index.json`` with the same shape.

A generated lease cites material from BOTH corpora. The single
``AILeaseAgentRun.corpus_version`` we stamp must therefore reflect
both. This module reads the two index files and produces one combined
fingerprint:

    combined_hash = sha256(f"{lease_law:{HASH}}|{legal_rag:{HASH}}").hexdigest()[:12]

If either index file is missing (fresh checkout, test environment, or
the indexer hasn't been run), the helper returns ``None``. Callers
fall back to whatever default they prefer — for the harness today
that's ``DAY_1_2_CORPUS_HASH`` from :mod:`apps.leases.training.cassette`.

This is the lightweight wire-up for B.3 (the "corpus_hash stamping"
follow-up from Phase 1 Day 1-2's ChromaDB indexer workstream). Phase 2
of the architecture (`LeaseTemplateAIChatV2View`) will use the same
helper to stamp every real ``AILeaseAgentRun`` row.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────── #


@dataclass(frozen=True)
class IndexedCorpus:
    """One side of the combined fingerprint — either the clauses or the
    legal-fact corpus."""

    name: str           # "lease_law" or "legal_rag"
    corpus_hash: str    # the hex digest written by the indexer
    fact_count: int     # number of indexed records (sanity / debug)
    indexed_at: str     # ISO8601 timestamp of last index run


def _read_last_index(path: Path, name: str) -> IndexedCorpus | None:
    """Read a ``.last_index.json`` file. Returns None on any read/parse
    failure — never raises (callers fall back to a stub hash).
    """
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(
            "corpus_hash: failed to read %s (%s): %s",
            path,
            name,
            exc,
        )
        return None

    # Both indexers write slightly different keys. Tolerate both shapes
    # so a key rename on one side doesn't break the combined fingerprint.
    corpus_hash = (
        raw.get("corpus_hash")
        or raw.get("corpus_version")
        or raw.get("merkle_root")
    )
    fact_count = int(
        raw.get("fact_count")
        or raw.get("chunk_count")
        or raw.get("indexed_count")
        or 0
    )
    indexed_at = str(
        raw.get("indexed_at")
        or raw.get("run_at")
        or raw.get("created_at")
        or ""
    )
    if not corpus_hash:
        logger.warning(
            "corpus_hash: %s lacks a usable hash field (looked for "
            "corpus_hash, corpus_version, merkle_root).",
            path,
        )
        return None
    return IndexedCorpus(
        name=name,
        corpus_hash=str(corpus_hash),
        fact_count=fact_count,
        indexed_at=indexed_at,
    )


def _lease_law_index_path() -> Path:
    """Return the path to the lease_law clauses indexer's .last_index.json."""
    base = Path(getattr(settings, "LEASE_AI_CHROMA_PATH", "")) or (
        Path(settings.BASE_DIR) / "lease_ai_chroma"
    )
    return base / ".last_index.json"


def _legal_rag_index_path() -> Path:
    """Return the path to the legal_rag indexer's .last_index.json."""
    base = Path(getattr(settings, "LEGAL_RAG_CHROMA_PATH", "")) or (
        Path(settings.BASE_DIR) / "legal_rag_chroma"
    )
    return base / ".last_index.json"


# ── Public API ────────────────────────────────────────────────────────── #


def compute_combined_corpus_hash() -> str | None:
    """Return the combined fingerprint of both indexers, or None if either
    side has never run.

    Shape: ``"klikk-corpus-<12-hex>"``.

    Deterministic: same two side-hashes produce the same combined hash.
    Order-stable: lease_law always comes first in the input, even if the
    file mtimes differ.
    """
    lease_law = _read_last_index(_lease_law_index_path(), "lease_law")
    legal_rag = _read_last_index(_legal_rag_index_path(), "legal_rag")
    if lease_law is None or legal_rag is None:
        # One or both indexers haven't run. Caller falls back to a stub.
        return None
    payload = (
        f"lease_law:{lease_law.corpus_hash}|legal_rag:{legal_rag.corpus_hash}"
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return f"klikk-corpus-{digest}"


def describe_corpus_state() -> dict[str, IndexedCorpus | None]:
    """Diagnostic helper. Returns the parsed per-side state plus the
    combined hash. Used by ``train_lease_agent --verbose`` to log
    which corpus version the harness is running against.
    """
    return {
        "lease_law": _read_last_index(_lease_law_index_path(), "lease_law"),
        "legal_rag": _read_last_index(_legal_rag_index_path(), "legal_rag"),
    }


__all__ = [
    "IndexedCorpus",
    "compute_combined_corpus_hash",
    "describe_corpus_state",
]
