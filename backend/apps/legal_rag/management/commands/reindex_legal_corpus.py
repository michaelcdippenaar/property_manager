"""Reindex the centralised legal-fact corpus into ChromaDB.

Reads :class:`apps.legal_rag.models.LegalFact` rows tied to the currently
active :class:`LegalCorpusVersion`, and upserts a semantic index into the
``klikk_legal_v1`` collection at ``settings.LEGAL_RAG_CHROMA_PATH``.

Behaviour locked by ``content/cto/centralised-legal-rag-store-plan.md`` §3
and §11 (mirrors ``manage.py reindex_lease_corpus`` for consistency):

  - One ChromaDB document per LegalFact. ``id = concept_id``.
  - Embedded text composed of citation_string + plain_english_summary +
    topic tags — what a semantic query is most likely to match against.
  - Embedder: ``text-embedding-3-small`` via OpenAI when ``OPENAI_API_KEY``
    is set; deterministic hash-based mock otherwise (matches lease corpus).
  - Idempotent: a fact is skipped if its ``content_hash`` already lives in
    the ChromaDB record's metadata.
  - Concurrency: ``pg_advisory_lock(hashtext('reindex_legal_corpus'))``.
  - Persists ``.last_index.json`` for observability.

Usage::

    python manage.py reindex_legal_corpus
    python manage.py reindex_legal_corpus --dry-run --verbose
    python manage.py reindex_legal_corpus --full-rebuild
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.legal_rag.models import LegalCorpusVersion, LegalFact

logger = logging.getLogger(__name__)


# ── Constants ────────────────────────────────────────────────────────── #


COLLECTION_NAME = "klikk_legal_v1"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
MOCK_EMBEDDING_MODEL = "klikk-mock-deterministic-v1"
MOCK_EMBED_DIM = 1536  # match text-embedding-3-small so swap is dimension-stable
ADVISORY_LOCK_KEY = "reindex_legal_corpus"


# ── Parsed dataclass ─────────────────────────────────────────────────── #


@dataclass
class IndexedFact:
    """A LegalFact row prepared for indexing."""

    concept_id: str
    type: str
    citation_string: str
    plain_english_summary: str
    topic_tags: list[str]
    citation_confidence: str
    verification_status: str
    legal_provisional: bool
    content_hash: str
    corpus_version: str


class Command(BaseCommand):
    """Reindex ``LegalFact`` rows into the ``klikk_legal_v1`` ChromaDB collection."""

    help = (
        f"Reindex apps.legal_rag.LegalFact rows into the {COLLECTION_NAME!r} "
        "ChromaDB collection. Idempotent unless --full-rebuild is set."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Compute what would be indexed; do NOT touch ChromaDB or write "
                "the .last_index.json record."
            ),
        )
        parser.add_argument(
            "--full-rebuild",
            action="store_true",
            help=(
                "Wipe the ChromaDB collection before re-indexing every fact "
                "from PostgreSQL. Used after an embedding-model swap."
            ),
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Print one line per fact processed (indexed / skipped).",
        )

    # ── Entry point ──────────────────────────────────────────────── #

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        full_rebuild: bool = options["full_rebuild"]
        verbose: bool = options["verbose"]

        active_version = LegalCorpusVersion.objects.filter(is_active=True).first()
        if active_version is None:
            self.stdout.write(
                self.style.WARNING(
                    "No active LegalCorpusVersion. Run `manage.py "
                    "sync_legal_facts` first."
                )
            )
            return

        facts = list(
            LegalFact.objects.filter(
                is_active=True,
                corpus_version=active_version,
            ).order_by("concept_id")
        )
        if not facts:
            self.stdout.write(
                self.style.WARNING(
                    f"No active LegalFact rows for corpus_version="
                    f"{active_version.version!r}. Nothing to index."
                )
            )
            return

        indexed_facts = [
            IndexedFact(
                concept_id=f.concept_id,
                type=f.type,
                citation_string=f.citation_string,
                plain_english_summary=f.plain_english_summary,
                topic_tags=list(f.topic_tags or []),
                citation_confidence=f.citation_confidence,
                verification_status=f.verification_status,
                legal_provisional=bool(f.legal_provisional),
                content_hash=f.content_hash,
                corpus_version=active_version.version,
            )
            for f in facts
        ]

        if dry_run:
            self._print_dry_run(indexed_facts, full_rebuild=full_rebuild)
            return

        try:
            self._acquire_advisory_lock()
        except Exception as exc:  # noqa: BLE001
            raise CommandError(
                f"Could not acquire pg_advisory_lock for reindex: {exc}"
            ) from exc

        try:
            persist_path = Path(settings.LEGAL_RAG_CHROMA_PATH)
            indexer = _ChromaIndexer(
                persist_path=persist_path,
                collection_name=COLLECTION_NAME,
                stdout=self.stdout,
                style=self.style,
            )
            if full_rebuild:
                indexer.wipe_collection()

            embedder, model_name = _build_embedder(stdout=self.stdout, style=self.style)
            indexed, skipped = indexer.upsert_facts(
                indexed_facts, embedder=embedder, verbose=verbose
            )
        finally:
            self._release_advisory_lock()

        self._write_last_index_record(
            facts=indexed_facts,
            embedding_model=model_name,
            indexed=indexed,
            skipped=skipped,
            corpus_version=active_version.version,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"reindex_legal_corpus complete — "
                f"indexed={indexed} skipped={skipped} "
                f"corpus_version={active_version.version} "
                f"collection={COLLECTION_NAME} embedder={model_name}"
            )
        )

    # ── Advisory lock ────────────────────────────────────────────── #

    def _acquire_advisory_lock(self) -> None:
        if connection.vendor != "postgresql":
            logger.warning(
                "reindex_legal_corpus: not running on PostgreSQL "
                "(vendor=%r) — skipping advisory lock. Tests / SQLite envs only.",
                connection.vendor,
            )
            return
        with connection.cursor() as cur:
            cur.execute(
                "SELECT pg_advisory_lock(hashtext(%s))", [ADVISORY_LOCK_KEY]
            )

    def _release_advisory_lock(self) -> None:
        if connection.vendor != "postgresql":
            return
        with connection.cursor() as cur:
            cur.execute(
                "SELECT pg_advisory_unlock(hashtext(%s))", [ADVISORY_LOCK_KEY]
            )

    # ── Dry-run output ───────────────────────────────────────────── #

    def _print_dry_run(
        self, facts: list[IndexedFact], *, full_rebuild: bool
    ) -> None:
        for fact in facts:
            self.stdout.write(
                f"  [dry-run] {fact.concept_id:<55} "
                f"{fact.content_hash[:12]}  {fact.citation_string}"
            )
        flag = " (full-rebuild)" if full_rebuild else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"Dry-run complete — would index {len(facts)} fact(s){flag} "
                f"into collection {COLLECTION_NAME}."
            )
        )

    # ── .last_index.json ─────────────────────────────────────────── #

    def _write_last_index_record(
        self,
        *,
        facts: list[IndexedFact],
        embedding_model: str,
        indexed: int,
        skipped: int,
        corpus_version: str,
    ) -> None:
        persist_path = Path(settings.LEGAL_RAG_CHROMA_PATH)
        persist_path.mkdir(parents=True, exist_ok=True)
        record = {
            "run_at": datetime.now(tz=timezone.utc).isoformat(),
            "fact_count": len(facts),
            "corpus_version": corpus_version,
            "embedding_model": embedding_model,
            "indexed": indexed,
            "skipped": skipped,
            "collection_name": COLLECTION_NAME,
        }
        (persist_path / ".last_index.json").write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


# ── Embedder (mirrors reindex_lease_corpus) ─────────────────────────── #


def _build_embedder(*, stdout, style) -> tuple[Any, str]:
    """Return ``(embed_callable, model_name)``.

    Uses OpenAI ``text-embedding-3-small`` when ``OPENAI_API_KEY`` is set;
    otherwise a deterministic hash-based mock (same shape as the lease
    corpus). The mock keeps tests + CI green without network access.
    """
    api_key = os.environ.get("OPENAI_API_KEY") or getattr(
        settings, "OPENAI_API_KEY", ""
    )
    if not api_key:
        stdout.write(
            style.WARNING(
                "OPENAI_API_KEY not set — using deterministic mock embedder. "
                "ChromaDB will hold real chunks, but vector similarity is "
                "hash-based, not semantic. Set OPENAI_API_KEY for production."
            )
        )
        return _mock_embed, MOCK_EMBEDDING_MODEL

    try:
        from openai import OpenAI  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        stdout.write(
            style.WARNING(
                f"openai SDK import failed ({exc}); falling back to mock embedder."
            )
        )
        return _mock_embed, MOCK_EMBEDDING_MODEL

    client = OpenAI(api_key=api_key)

    def _openai_embed(texts: list[str]) -> list[list[float]]:
        resp = client.embeddings.create(model=DEFAULT_EMBEDDING_MODEL, input=texts)
        return [item.embedding for item in resp.data]

    return _openai_embed, DEFAULT_EMBEDDING_MODEL


def _mock_embed(texts: list[str]) -> list[list[float]]:
    """Deterministic hash-based mock embedder. Same shape as the lease corpus."""
    vectors: list[list[float]] = []
    for text in texts:
        seed = hashlib.sha256(text.encode("utf-8")).digest()
        repeats = (MOCK_EMBED_DIM + len(seed) - 1) // len(seed)
        tiled = (seed * repeats)[:MOCK_EMBED_DIM]
        vec = [(b / 127.5) - 1.0 for b in tiled]
        vectors.append(vec)
    return vectors


# ── ChromaDB indexer ─────────────────────────────────────────────────── #


class _ChromaIndexer:
    """Thin wrapper around chromadb.PersistentClient for the legal corpus."""

    def __init__(
        self,
        *,
        persist_path: Path,
        collection_name: str,
        stdout,
        style,
    ):
        self.persist_path = persist_path
        self.collection_name = collection_name
        self.stdout = stdout
        self.style = style
        self._client = None
        self._col = None

    def _ensure_collection(self):
        if self._col is not None:
            return self._col
        import chromadb  # type: ignore[import-not-found]

        self.persist_path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self.persist_path))
        self._col = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        return self._col

    def wipe_collection(self) -> None:
        """Drop and recreate the ChromaDB collection.

        Used by ``--full-rebuild`` after an embedder swap (the existing
        vectors live in the model's old embedding space and are no longer
        comparable to fresh ones).
        """
        import chromadb  # type: ignore[import-not-found]

        self.persist_path.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(self.persist_path))
        try:
            client.delete_collection(name=self.collection_name)
        except Exception as exc:  # noqa: BLE001 — collection may not exist
            logger.info(
                "reindex_legal_corpus: delete_collection(%r) — %s. "
                "Continuing with create.",
                self.collection_name,
                exc,
            )
        self._client = client
        self._col = client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_facts(
        self,
        facts: list[IndexedFact],
        *,
        embedder,
        verbose: bool,
    ) -> tuple[int, int]:
        """Upsert facts whose content_hash does not already match in ChromaDB.

        Returns ``(indexed, skipped)``.
        """
        col = self._ensure_collection()

        ids = [f.concept_id for f in facts]
        try:
            existing = col.get(ids=ids, include=["metadatas"])
        except Exception as exc:  # noqa: BLE001 — empty collection edge case
            logger.warning(
                "ChromaDB get(ids=…) failed: %s; treating all as new.", exc
            )
            existing = {"ids": [], "metadatas": []}

        existing_hash_by_id: dict[str, str] = {}
        for cid, meta in zip(
            existing.get("ids") or [], existing.get("metadatas") or []
        ):
            if meta:
                existing_hash_by_id[cid] = str(meta.get("content_hash") or "")

        to_index: list[IndexedFact] = []
        for fact in facts:
            if existing_hash_by_id.get(fact.concept_id) == fact.content_hash:
                if verbose:
                    self.stdout.write(
                        f"  skipped  {fact.concept_id:<55} {fact.content_hash[:12]}"
                    )
                continue
            to_index.append(fact)
            if verbose:
                self.stdout.write(
                    f"  indexed  {fact.concept_id:<55} {fact.content_hash[:12]}"
                )

        skipped = len(facts) - len(to_index)
        if not to_index:
            return 0, skipped

        documents = [_embedded_text_for(fact) for fact in to_index]
        embeddings = embedder(documents)

        col.upsert(
            ids=[f.concept_id for f in to_index],
            documents=documents,
            embeddings=embeddings,
            metadatas=[_metadata_for(f) for f in to_index],
        )
        return len(to_index), skipped


def _embedded_text_for(fact: IndexedFact) -> str:
    """Build the text we embed for semantic search.

    Plan §3 says the embedding payload is citation + summary + topic tags.
    Keep this stable — changes to this string invalidate every cached vector.
    """
    topic = " ".join(fact.topic_tags) if fact.topic_tags else ""
    return (
        f"{fact.citation_string}. "
        f"{fact.plain_english_summary.strip()}. "
        f"Topic: {topic}."
    ).strip()


def _metadata_for(fact: IndexedFact) -> dict[str, Any]:
    """Flatten an IndexedFact into ChromaDB-safe scalar metadata.

    ChromaDB metadata values must be scalar (str / int / float / bool / None),
    so the topic-tag list is serialised as a CSV string and ``statute`` is
    extracted from the citation_string prefix.
    """
    statute = _statute_prefix_from_citation(fact.citation_string)
    return {
        "concept_id": fact.concept_id,
        "type": fact.type,
        "citation_string": fact.citation_string,
        "citation_confidence": fact.citation_confidence,
        "verification_status": fact.verification_status,
        "legal_provisional": bool(fact.legal_provisional),
        "corpus_version": fact.corpus_version,
        "content_hash": fact.content_hash,
        "topic_tags": ",".join(fact.topic_tags) if fact.topic_tags else "",
        "statute": statute,
    }


def _statute_prefix_from_citation(citation: str) -> str:
    """Extract the statute key from a canonical citation string.

    ``"RHA s5(3)(a)"`` → ``"RHA"``. Falls back to the empty string for
    non-conforming inputs (case_law / pitfall facts may relax this).
    """
    if not citation:
        return ""
    head = citation.split(" ", 1)[0]
    if head in {"RHA", "POPIA", "CPA", "PIE", "STSMA", "CSOS"}:
        return head
    return ""


__all__ = [
    "Command",
    "IndexedFact",
    "COLLECTION_NAME",
    "DEFAULT_EMBEDDING_MODEL",
    "_metadata_for",
    "_embedded_text_for",
    "_statute_prefix_from_citation",
]
