"""
The Volt — ChromaDB RAG helpers.

Two collections:
  - volt_documents : chunks of document text extracted from uploaded files
  - volt_entities  : structured entity data rendered as natural-language text

All vectors are scoped by owner_id in metadata so one ChromaDB instance serves
all vault owners with full isolation via where-clause filtering.

Hybrid graph+vector queries are supported via query_vault() with an optional
entity_ids filter — pass the IDs returned from a graph traversal to restrict
semantic search to a specific subgraph of entities.
"""
from __future__ import annotations

import io
import logging
from typing import Optional

from django.conf import settings

from core.contract_rag import (
    chunk_text,
    get_chroma_client,
    get_embedding_function,
)

logger = logging.getLogger(__name__)

VOLT_DOCUMENTS_COLLECTION = getattr(settings, "VOLT_DOCUMENTS_COLLECTION", "volt_documents")
VOLT_ENTITIES_COLLECTION = getattr(settings, "VOLT_ENTITIES_COLLECTION", "volt_entities")


# ---------------------------------------------------------------------------
# Collection accessors
# ---------------------------------------------------------------------------

def get_volt_documents_collection():
    """Get (or create) the vault documents ChromaDB collection."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=VOLT_DOCUMENTS_COLLECTION,
        embedding_function=get_embedding_function(),
        metadata={"hnsw:space": "cosine", "description": "The Volt — encrypted document text chunks"},
    )


def get_volt_entities_collection():
    """Get (or create) the vault entities ChromaDB collection."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=VOLT_ENTITIES_COLLECTION,
        embedding_function=get_embedding_function(),
        metadata={"hnsw:space": "cosine", "description": "The Volt — entity structured data"},
    )


# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------

def _extract_text_from_bytes(filename: str, plaintext_bytes: bytes) -> str:
    """Extract text from PDF, DOCX, or plain text bytes."""
    name_lower = filename.lower()
    try:
        if name_lower.endswith(".pdf"):
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(plaintext_bytes))
            parts = []
            max_pages = getattr(settings, "RAG_PDF_MAX_PAGES", 120)
            for page in reader.pages[:max_pages]:
                text = page.extract_text()
                if text:
                    parts.append(text)
            return "\n".join(parts)

        if name_lower.endswith(".docx"):
            import docx
            doc = docx.Document(io.BytesIO(plaintext_bytes))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

        # Fallback: treat as plain text / markdown
        return plaintext_bytes.decode("utf-8", errors="replace")

    except Exception:
        logger.exception("Failed to extract text from %s", filename)
        return ""


# ---------------------------------------------------------------------------
# Ingest functions
# ---------------------------------------------------------------------------

def _render_extracted_data(document_type: str, extracted_data: dict) -> str:
    """Render a client-supplied OCR JSON dict to flat indexable text."""
    lines = [f"document_type: {document_type}"]

    def _walk(prefix: str, value):
        if value is None or value == "" or value == [] or value == {}:
            return
        if isinstance(value, dict):
            for k, v in value.items():
                _walk(f"{prefix}.{k}" if prefix else k, v)
        elif isinstance(value, list):
            if all(not isinstance(x, (dict, list)) for x in value):
                lines.append(f"{prefix}: {', '.join(str(x) for x in value)}")
            else:
                for i, item in enumerate(value):
                    _walk(f"{prefix}[{i}]", item)
        else:
            lines.append(f"{prefix}: {value}")

    for key, value in (extracted_data or {}).items():
        _walk(key, value)
    return "\n".join(lines)


def ingest_document_version(
    *,
    owner_id: int,
    entity_id: int,
    document_id: int,
    version_id: int,
    filename: str,
    document_type: str,
    entity_type: str,
    plaintext_bytes: Optional[bytes] = None,
    extracted_data: Optional[dict] = None,
    chunk_size: int = 1200,
    overlap: int = 150,
) -> Optional[str]:
    """Upsert document chunks into volt_documents.

    Indexing preference:
      1. If `extracted_data` is provided (client-side OCR), index THAT directly —
         no server-side re-extraction. This is the normal path.
      2. Otherwise, fall back to text extraction from `plaintext_bytes`
         (PDF/DOCX/text) for backwards compatibility.

    Returns:
        Base chunk ID prefix (e.g. "volt-doc-5-v3") stored as chroma_id on
        DocumentVersion, or None if nothing indexable was produced.
    """
    if extracted_data:
        text = _render_extracted_data(document_type, extracted_data)
    else:
        text = _extract_text_from_bytes(filename, plaintext_bytes or b"")

    if not text.strip():
        logger.warning(
            "No text extracted from document_id=%s version_id=%s filename=%s",
            document_id, version_id, filename,
        )
        return None

    chunks = chunk_text(text, size=chunk_size, overlap=overlap)
    if not chunks:
        return None

    base_id = f"volt-doc-{document_id}-v{version_id}"
    collection = get_volt_documents_collection()

    ids, documents, metadatas = [], [], []
    for idx, chunk in enumerate(chunks):
        ids.append(f"{base_id}-chunk-{idx}")
        documents.append(chunk)
        metadatas.append({
            "owner_id": owner_id,
            "entity_id": entity_id,
            "document_id": document_id,
            "version_id": version_id,
            "document_type": document_type,
            "entity_type": entity_type,
            "filename": filename,
            "chunk_index": idx,
        })

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    logger.info(
        "Volt: ingested %d chunks for document_id=%s version_id=%s",
        len(chunks), document_id, version_id,
    )
    return base_id


def ingest_entity_data(
    *,
    owner_id: int,
    entity_id: int,
    entity_type: str,
    entity_name: str,
    data: dict,
    chunk_size: int = 800,
    overlap: int = 100,
) -> Optional[str]:
    """Render entity structured data as natural-language text and upsert to volt_entities.

    Returns:
        Base chunk ID prefix stored as chroma_id on VaultEntity, or None on failure.
    """
    lines = [
        f"entity_type: {entity_type}",
        f"name: {entity_name}",
    ]
    for key, value in data.items():
        if value is not None and value != "" and value != [] and value != {}:
            if isinstance(value, list):
                lines.append(f"{key}: {', '.join(str(v) for v in value)}")
            elif isinstance(value, dict):
                for k, v in value.items():
                    lines.append(f"{key}.{k}: {v}")
            else:
                lines.append(f"{key}: {value}")

    text = "\n".join(lines)
    chunks = chunk_text(text, size=chunk_size, overlap=overlap)
    if not chunks:
        return None

    base_id = f"volt-entity-{entity_id}"
    collection = get_volt_entities_collection()

    ids, documents, metadatas = [], [], []
    for idx, chunk in enumerate(chunks):
        ids.append(f"{base_id}-chunk-{idx}")
        documents.append(chunk)
        metadatas.append({
            "owner_id": owner_id,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "entity_name": entity_name,
            "chunk_index": idx,
        })

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    logger.info("Volt: ingested %d chunks for entity_id=%s", len(chunks), entity_id)
    return base_id


# ---------------------------------------------------------------------------
# Delete functions
# ---------------------------------------------------------------------------

def delete_document_chunks(*, owner_id: int, document_id: int) -> None:
    """Remove all ChromaDB chunks for a document (all versions)."""
    try:
        collection = get_volt_documents_collection()
        collection.delete(where={"document_id": document_id})
        logger.info("Volt: deleted ChromaDB chunks for document_id=%s", document_id)
    except Exception:
        logger.exception("Volt: failed to delete chunks for document_id=%s", document_id)


def delete_entity_chunks(*, owner_id: int, entity_id: int) -> None:
    """Remove all ChromaDB chunks for an entity (entity data + all its documents)."""
    try:
        col_entities = get_volt_entities_collection()
        col_entities.delete(where={"entity_id": entity_id})
        col_docs = get_volt_documents_collection()
        col_docs.delete(where={"entity_id": entity_id})
        logger.info("Volt: deleted all ChromaDB chunks for entity_id=%s", entity_id)
    except Exception:
        logger.exception("Volt: failed to delete chunks for entity_id=%s", entity_id)


# ---------------------------------------------------------------------------
# Query function (supports hybrid graph+vector)
# ---------------------------------------------------------------------------

def query_vault(
    *,
    owner_id: int,
    query: str,
    entity_ids: Optional[list[int]] = None,
    collection: str = "documents",
    n_results: int = 5,
) -> list[dict]:
    """Semantic search within a vault, optionally scoped to specific entity IDs.

    This is the second step in a hybrid graph+vector query:
      1. Graph traversal (ORM) produces a list of entity_ids
      2. query_vault(..., entity_ids=[...]) restricts vector search to those entities

    Args:
        owner_id:   Vault owner — all results are filtered to this owner.
        query:      Natural-language query string.
        entity_ids: Optional list of entity IDs from a prior graph traversal.
                    If provided, only chunks from those entities are searched.
        collection: "documents" or "entities".
        n_results:  Number of results to return.

    Returns:
        List of dicts: [{text, metadata, distance}, ...]
    """
    col = get_volt_documents_collection() if collection == "documents" else get_volt_entities_collection()

    # Build ChromaDB where clause
    if entity_ids:
        where: dict = {
            "$and": [
                {"owner_id": {"$eq": owner_id}},
                {"entity_id": {"$in": [int(eid) for eid in entity_ids]}},
            ]
        }
    else:
        where = {"owner_id": {"$eq": owner_id}}

    try:
        results = col.query(
            query_texts=[query],
            n_results=min(n_results, col.count() or 1),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        logger.exception("Volt: query_vault failed for owner_id=%s", owner_id)
        return []

    output = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]
    for text, meta, dist in zip(docs, metas, dists):
        output.append({"text": text, "metadata": meta, "distance": dist})
    return output
