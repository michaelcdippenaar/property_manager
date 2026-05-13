"""
Query API for the lease-AI clauses corpus.

Module-level Python functions intended to be called from the Drafter's
Front Door push pattern (architecture decision 9). The shape is stable so
that in v2 (MCP product) the same signatures can wrap MCP tools.

Statutes / case law / pitfalls are NOT in this module — they live in
``apps.legal_rag.queries`` per ``content/cto/centralised-legal-rag-store-plan.md``
§8 step 6.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "klikk_lease_clauses_v1"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
MOCK_EMBED_DIM = 1536


# ── Public dataclass ─────────────────────────────────────────────── #


@dataclass(frozen=True, slots=True)
class ClauseChunk:
    """Returned by ``query_clauses``. Frozen so the runner can hash it
    cheaply and inline it into a cached system block.
    """

    id: str
    version: int
    content_hash: str
    clause_title: str
    clause_body: str
    topic_tags: tuple[str, ...]
    related_citations: tuple[str, ...]
    property_types: tuple[str, ...]
    tenant_counts: tuple[str, ...]
    lease_types: tuple[str, ...]
    merge_fields_used: tuple[str, ...]
    citation_confidence: str
    legal_provisional: bool
    confidence_level: str
    source_path: str
    score: float | None = None  # cosine distance when semantic_query is used
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_chroma(
        cls, *, _id: str, document: str | None, metadata: dict[str, Any], distance: float | None
    ) -> "ClauseChunk":
        return cls(
            id=str(metadata.get("id") or _id),
            version=int(metadata.get("version") or 1),
            content_hash=str(metadata.get("content_hash") or ""),
            clause_title=str(metadata.get("clause_title") or ""),
            clause_body=(document or "").split(
                str(metadata.get("clause_title") or ""), 1
            )[-1].lstrip(" "),
            topic_tags=_split_csv(metadata.get("topic_tags")),
            related_citations=_split_csv(metadata.get("related_citations")),
            property_types=_split_csv(metadata.get("property_types")),
            tenant_counts=_split_csv(metadata.get("tenant_counts")),
            lease_types=_split_csv(metadata.get("lease_types")),
            merge_fields_used=_split_csv(metadata.get("merge_fields_used")),
            citation_confidence=str(metadata.get("citation_confidence") or ""),
            legal_provisional=bool(metadata.get("legal_provisional") or False),
            confidence_level=str(metadata.get("confidence_level") or ""),
            source_path=str(metadata.get("source_path") or ""),
            score=distance,
        )


# ── Public functions ─────────────────────────────────────────────── #


def query_clauses(
    *,
    topic_tags: list[str] | None = None,
    property_type: str | None = None,
    tenant_count: int | str | None = None,
    lease_type: str | None = None,
    semantic_query: str | None = None,
    k: int = 10,
) -> list[ClauseChunk]:
    """Pull matching clause chunks from ChromaDB.

    Used by the Drafter's Front Door push pattern: the Front Door
    inlines retrieved clauses into the Drafter's system block.

    ``topic_tags`` and the ``applicability`` fields work as metadata
    filters in ChromaDB; matching is *substring on CSV* because Chroma
    metadata can only hold scalar values.

    ``semantic_query`` triggers embedding-similarity ranking when set.
    Without it, returns up to ``k`` chunks matching the filters with no
    particular order (Chroma ``get`` is not ordered).
    """
    col = _get_collection()
    if col is None:
        return []

    where = _build_where(
        topic_tags=topic_tags,
        property_type=property_type,
        tenant_count=tenant_count,
        lease_type=lease_type,
    )

    if semantic_query:
        embedder, _ = _build_embedder()
        try:
            qvec = embedder([semantic_query])[0]
        except Exception:  # noqa: BLE001
            logger.exception(
                "query_clauses: embedding semantic_query failed; "
                "falling back to filter-only search."
            )
            return _filter_only_query(col, where=where, k=k)

        try:
            res = col.query(
                query_embeddings=[qvec],
                n_results=k,
                where=where or None,
                include=["documents", "metadatas", "distances"],
            )
        except Exception:  # noqa: BLE001
            logger.exception("ChromaDB query_clauses semantic_query failed.")
            return []
        return _hydrate_query_result(res)

    return _filter_only_query(col, where=where, k=k)


def get_corpus_hash() -> str | None:
    """Return the corpus hash recorded by the last ``reindex_lease_corpus`` run.

    Read from ``backend/apps/leases/lease_law_corpus/.last_index.json``.
    Returns ``None`` if the file is missing or unreadable; the runner
    treats that as "corpus not yet indexed" and surfaces a sev-1.
    """
    record_path = (
        Path(settings.BASE_DIR) / "apps" / "leases" / "lease_law_corpus" / ".last_index.json"
    )
    if not record_path.is_file():
        return None
    try:
        data = json.loads(record_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        logger.exception("get_corpus_hash: could not parse %s", record_path)
        return None
    return data.get("corpus_hash") if isinstance(data, dict) else None


# ── Internals ────────────────────────────────────────────────────── #


def _get_collection():
    """Return the ChromaDB collection or ``None`` if Chroma cannot be reached."""
    try:
        import chromadb  # type: ignore[import-not-found]
    except Exception:  # noqa: BLE001
        logger.exception("chromadb not installed; query_clauses will return [].")
        return None

    persist_path = Path(
        getattr(settings, "LEASE_AI_CHROMA_PATH", Path(settings.BASE_DIR) / "lease_ai_chroma")
    )
    persist_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_path))
    return client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )


def _build_where(
    *,
    topic_tags: list[str] | None,
    property_type: str | None,
    tenant_count: int | str | None,
    lease_type: str | None,
) -> dict[str, Any]:
    """Build a Chroma ``where`` clause using ``$contains`` on the CSV strings."""
    clauses: list[dict[str, Any]] = []

    if topic_tags:
        for tag in topic_tags:
            clauses.append({"topic_tags": {"$contains": tag}})
    if property_type:
        clauses.append({"property_types": {"$contains": property_type}})
    if tenant_count is not None:
        clauses.append({"tenant_counts": {"$contains": str(tenant_count)}})
    if lease_type:
        clauses.append({"lease_types": {"$contains": lease_type}})

    if not clauses:
        return {}
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _filter_only_query(col, *, where: dict[str, Any], k: int) -> list[ClauseChunk]:
    try:
        res = col.get(
            where=where or None,
            limit=k,
            include=["documents", "metadatas"],
        )
    except Exception:  # noqa: BLE001
        logger.exception("ChromaDB get(where=…) failed for query_clauses filter path.")
        return []

    ids: list[str] = res.get("ids") or []
    metadatas: list[dict[str, Any]] = res.get("metadatas") or []
    documents: list[str | None] = res.get("documents") or [None] * len(ids)

    out: list[ClauseChunk] = []
    for cid, doc, meta in zip(ids, documents, metadatas):
        out.append(
            ClauseChunk.from_chroma(
                _id=cid, document=doc, metadata=meta or {}, distance=None
            )
        )
    return out


def _hydrate_query_result(res: dict[str, Any]) -> list[ClauseChunk]:
    # ChromaDB query() returns lists nested one level deep, keyed by the
    # query batch index. We only ever issue one query.
    ids = (res.get("ids") or [[]])[0]
    metadatas = (res.get("metadatas") or [[]])[0]
    documents = (res.get("documents") or [[]])[0]
    distances = (res.get("distances") or [[]])[0]

    out: list[ClauseChunk] = []
    for cid, doc, meta, dist in zip(ids, documents, metadatas, distances):
        out.append(
            ClauseChunk.from_chroma(
                _id=cid,
                document=doc,
                metadata=meta or {},
                distance=float(dist) if dist is not None else None,
            )
        )
    return out


def _build_embedder() -> tuple[Any, str]:
    """Mirror of the indexer's embedder selection so semantic_query at
    runtime uses the same model the corpus was indexed against."""
    api_key = os.environ.get("OPENAI_API_KEY") or getattr(
        settings, "OPENAI_API_KEY", ""
    )
    if not api_key:
        return _mock_embed, "klikk-mock-deterministic-v1"

    try:
        from openai import OpenAI  # type: ignore[import-not-found]
    except Exception:  # noqa: BLE001
        return _mock_embed, "klikk-mock-deterministic-v1"

    client = OpenAI(api_key=api_key)

    def _openai_embed(texts: list[str]) -> list[list[float]]:
        resp = client.embeddings.create(model=DEFAULT_EMBEDDING_MODEL, input=texts)
        return [item.embedding for item in resp.data]

    return _openai_embed, DEFAULT_EMBEDDING_MODEL


def _mock_embed(texts: list[str]) -> list[list[float]]:
    """Same deterministic mock as the indexer — keep the two in sync."""
    vectors: list[list[float]] = []
    for text in texts:
        seed = hashlib.sha256(text.encode("utf-8")).digest()
        repeats = (MOCK_EMBED_DIM + len(seed) - 1) // len(seed)
        tiled = (seed * repeats)[:MOCK_EMBED_DIM]
        vectors.append([(b / 127.5) - 1.0 for b in tiled])
    return vectors


def _split_csv(value: Any) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(str(v) for v in value)
    return tuple(part for part in str(value).split(",") if part)


__all__ = [
    "ClauseChunk",
    "COLLECTION_NAME",
    "get_corpus_hash",
    "query_clauses",
]
