"""
ChromaDB vector store for landlord (owner) FICA/CIPC documents.

Each chunk is scoped to a single landlord via the `landlord_id` metadata key.
Cross-tenant leakage is prevented by refusing to query without a landlord filter
— there is no unscoped fallback path.

Pattern mirrors backend/core/contract_rag.py (same client, same embedding model)
so the two collections can coexist in the same PersistentClient.

See `.claude/skills/klikk-documents-owner-cipro/references/rag-ingestion.md` for
the design rationale.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from core.contract_rag import get_chroma_client, get_embedding_function

logger = logging.getLogger(__name__)

OWNER_DOCUMENTS_COLLECTION = "owner_documents"

# Bump this when extraction prompts / classification taxonomy change in a way
# that makes old chunks incoherent with new ones. The `classification_version`
# metadata on each chunk lets you identify stale chunks to re-ingest.
CLASSIFICATION_VERSION = "2026-04"

# Chunking thresholds (see rag-ingestion.md §Chunking Strategy)
LONG_DOC_PAGE_THRESHOLD = 3
LONG_DOC_CHAR_THRESHOLD = 4000
LONG_CHUNK_SIZE_CHARS = 2000   # ~500 tokens
LONG_CHUNK_OVERLAP_CHARS = 400  # ~100 tokens


def get_owner_documents_collection():
    """Get-or-create the `owner_documents` ChromaDB collection.

    Always filter queries by `landlord_id` — the collection is shared across
    all landlords to amortise the embedding model load, not because cross-landlord
    retrieval is ever desired.
    """
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=OWNER_DOCUMENTS_COLLECTION,
        embedding_function=get_embedding_function(),
        metadata={
            "hnsw:space": "cosine",
            "description": "Landlord FICA/CIPC documents — filter by landlord_id",
        },
    )


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _chunk_long_page(text: str) -> list[str]:
    """Sliding-window chunking for long narrative pages (trust deeds, MOIs).

    Prefers splits on double newlines (clause boundaries) when possible.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= LONG_CHUNK_SIZE_CHARS:
        return [text]
    chunks: list[str] = []
    i = 0
    step = max(1, LONG_CHUNK_SIZE_CHARS - LONG_CHUNK_OVERLAP_CHARS)
    while i < len(text):
        end = min(i + LONG_CHUNK_SIZE_CHARS, len(text))
        window = text[i:end]
        # Try to end on a paragraph break if we're not at the very end
        if end < len(text):
            split = window.rfind("\n\n")
            if split > LONG_CHUNK_SIZE_CHARS // 2:
                window = window[:split]
                end = i + split
        chunks.append(window.strip())
        if end >= len(text):
            break
        i = max(i + step, end - LONG_CHUNK_OVERLAP_CHARS)
    return [c for c in chunks if c]


def chunk_pages(pages: list[str], is_long_doc: bool) -> list[tuple[int, str]]:
    """Return [(page_number_1_indexed, chunk_text), ...].

    Short structured docs get one chunk per page; long narrative docs get a
    sliding window within each page.
    """
    out: list[tuple[int, str]] = []
    for i, page_text in enumerate(pages, start=1):
        if not page_text or not page_text.strip():
            continue
        if is_long_doc:
            for chunk in _chunk_long_page(page_text):
                out.append((i, chunk))
        else:
            out.append((i, page_text.strip()))
    return out


def classify_doc_length(pages: list[str]) -> bool:
    """True if this should be chunked as a long narrative doc."""
    total_chars = sum(len(p or "") for p in pages)
    return len(pages) > LONG_DOC_PAGE_THRESHOLD or total_chars > LONG_DOC_CHAR_THRESHOLD


# ---------------------------------------------------------------------------
# Redaction (bank numbers, passport MRZ)
# ---------------------------------------------------------------------------

_MRZ_LINE = re.compile(r"^[A-Z0-9<]{30,}$", re.MULTILINE)
_BANK_ACCT_LONG = re.compile(r"\b\d{9,16}\b")


def redact_sensitive(text: str) -> str:
    """Redact items we don't want embedded.

    - Passport MRZ lines (long uppercase A–Z/0–9/< sequences) → `[MRZ_REDACTED]`
    - Long bare digit runs that look like bank account numbers → keep last 4.

    Conservative: false positives here mean slightly less-useful retrieval, not
    a data leak. False negatives mean PII ends up in the embedding model.
    """
    text = _MRZ_LINE.sub("[MRZ_REDACTED]", text)

    def _mask(match: re.Match) -> str:
        digits = match.group(0)
        return f"XXXX{digits[-4:]}"

    text = _BANK_ACCT_LONG.sub(_mask, text)
    return text


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

def _person_ids_csv(person_ids: list[str] | None) -> str:
    """Flatten person IDs to a comma-sentinel-wrapped CSV.

    ChromaDB metadata is flat-primitives-only. We store IDs as `,1234,5678,`
    so `$contains(",1234,")` never matches a substring of another ID.
    """
    if not person_ids:
        return ""
    clean = [p.strip() for p in person_ids if p and p.strip()]
    if not clean:
        return ""
    return "," + ",".join(clean) + ","


def delete_by_landlord(landlord_id: int) -> int:
    """Idempotent re-ingestion: drop all chunks for one landlord.

    Returns the number of chunks deleted (best-effort — ChromaDB doesn't
    return a count, so this queries first).
    """
    col = get_owner_documents_collection()
    try:
        existing = col.get(where={"landlord_id": int(landlord_id)})
        ids = existing.get("ids") or []
        if ids:
            col.delete(ids=ids)
        return len(ids)
    except Exception:
        logger.exception("owner_rag: delete_by_landlord failed for %s", landlord_id)
        return 0


def ingest_landlord_document(
    *,
    landlord_id: int,
    document_id: int,
    filename: str,
    doc_type: str,
    entity_type: str,
    entity_subtype: str | None,
    pages: list[str],
    person_ids: list[str] | None = None,
    expiry_date: str | None = None,
    extracted_fields_summary: str | None = None,
    entity_name: str | None = None,
) -> int:
    """Chunk, embed, and upsert one LandlordDocument into the collection.

    `pages` is the per-page extracted text. `extracted_fields_summary` is an
    optional natural-language rendering of classified fields that gets
    appended to each chunk so the embedding has something concrete to match
    even when page text is visually dense.

    Returns the number of chunks written.
    """
    if not pages:
        return 0

    is_long = classify_doc_length(pages)
    page_chunks = chunk_pages(pages, is_long_doc=is_long)
    if not page_chunks:
        return 0

    total_pages = len(pages)
    ingested_at = datetime.now(timezone.utc).isoformat()
    person_ids_flat = _person_ids_csv(person_ids)

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for chunk_index, (page_number, raw_chunk) in enumerate(page_chunks):
        header_parts = [
            f"doc_type={doc_type}",
            f"page={page_number}/{total_pages}",
        ]
        if entity_name:
            header_parts.append(f"entity={entity_name}")
        header = "[" + " | ".join(header_parts) + "]"

        body = redact_sensitive(raw_chunk)
        if extracted_fields_summary and chunk_index == 0:
            body = f"{body}\n\nExtracted fields: {extracted_fields_summary}"

        chunk_text = f"{header}\n{body}"

        ids.append(f"landlord-{landlord_id}-doc-{document_id}-chunk-{chunk_index}")
        documents.append(chunk_text)
        metadatas.append({
            "landlord_id": int(landlord_id),
            "document_id": int(document_id),
            "filename": filename or "",
            "doc_type": doc_type or "other",
            "entity_type": entity_type or "",
            "entity_subtype": entity_subtype or "",
            "person_ids": person_ids_flat,
            "expiry_date": expiry_date or "",
            "page_number": int(page_number),
            "total_pages": int(total_pages),
            "chunk_index": int(chunk_index),
            "ingested_at": ingested_at,
            "classification_version": CLASSIFICATION_VERSION,
        })

    col = get_owner_documents_collection()
    # Upsert in batches — SentenceTransformer is happy with larger batches, but
    # Chroma has per-call limits. 64 is safely within bounds.
    BATCH = 64
    for i in range(0, len(ids), BATCH):
        col.upsert(
            ids=ids[i:i + BATCH],
            documents=documents[i:i + BATCH],
            metadatas=metadatas[i:i + BATCH],
        )
    logger.info(
        "owner_rag: ingested landlord=%s document=%s doc_type=%s chunks=%d",
        landlord_id, document_id, doc_type, len(ids),
    )
    return len(ids)


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

def query_owner_documents(
    *,
    query: str,
    landlord_id: int,
    doc_type: str | None = None,
    n_results: int = 5,
) -> list[dict]:
    """Semantic search within a single landlord's documents.

    `landlord_id` is mandatory. There is deliberately no `query_all()` — a
    landlord-less query would leak POPIA-protected data across tenants.
    """
    if not landlord_id:
        raise ValueError("query_owner_documents requires landlord_id")
    col = get_owner_documents_collection()

    where: dict = {"landlord_id": int(landlord_id)}
    if doc_type:
        where = {"$and": [where, {"doc_type": doc_type}]}

    try:
        res = col.query(
            query_texts=[query],
            n_results=max(1, int(n_results)),
            where=where,
        )
    except Exception:
        logger.exception("owner_rag: query failed landlord=%s", landlord_id)
        return []

    out: list[dict] = []
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    for doc, meta, dist in zip(docs, metas, dists):
        out.append({
            "text": doc,
            "metadata": meta or {},
            "distance": dist,
        })
    return out
