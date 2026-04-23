"""
The Volt — Weaviate Cloud RAG backend.

Drop-in replacement for `core.volt_rag`. Same public interface:
    ingest_document_version(...)
    ingest_entity_data(...)
    query_vault(...)
    delete_document_chunks(...)
    delete_entity_chunks(...)

Why Weaviate over ChromaDB for The Volt:
  1. Native graph edges via cross-references — one system does both graph
     traversal AND vector search, killing the ORM+ChromaDB+Neo4j split.
  2. Multi-tenancy per VaultOwner — physical isolation, not just metadata
     filters. A tenant cannot read another tenant's vectors by construction.
  3. Hybrid BM25 + vector scoring in one query — precise for exact names
     (MC Dippenaar), fuzzy for semantic questions (who's a trustee?).
  4. Managed cloud (WCS) — no infra.

Schema (created lazily on first call):
    Collection: VoltEntity
        Properties: owner_id (int), entity_id (int), entity_type (text),
                    name (text), summary (text), data_json (text)
        References: hasDocument -> VoltDocumentChunk
                    relatesTo   -> VoltEntity  (typed via metadata.type)
        Multi-tenancy: tenant = f"owner-{owner_id}"
        Vectorizer: text2vec-weaviate (default, free on WCS sandbox)

    Collection: VoltDocumentChunk
        Properties: owner_id, entity_id, document_id, version_id,
                    document_type, filename, chunk_index, text
        References: aboutEntity -> VoltEntity
        Multi-tenancy: tenant = f"owner-{owner_id}"
        Vectorizer: text2vec-weaviate

Env required:
    WEAVIATE_URL=https://<cluster>.weaviate.cloud
    WEAVIATE_API_KEY=<admin key>
    VOLT_VECTOR_BACKEND=weaviate   # to route ingest_*/query_vault here
"""
from __future__ import annotations

import io
import json
import logging
from functools import lru_cache
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)

ENTITY_COLLECTION = "VoltEntity"
CHUNK_COLLECTION = "VoltDocumentChunk"


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_client():
    """Return a cached Weaviate v4 client connected to WCS.

    Raises RuntimeError if the env isn't configured so callers fail loud
    rather than silently fall back to a wrong backend.
    """
    import weaviate
    from weaviate.classes.init import Auth

    url = getattr(settings, "WEAVIATE_URL", "") or ""
    key = getattr(settings, "WEAVIATE_API_KEY", "") or ""
    if not url or not key:
        raise RuntimeError(
            "Weaviate backend is selected but WEAVIATE_URL / WEAVIATE_API_KEY "
            "are not set. Add them to backend/.env.secrets."
        )

    return weaviate.connect_to_weaviate_cloud(
        cluster_url=url,
        auth_credentials=Auth.api_key(key),
    )


def close_client() -> None:
    """Explicitly close the cached client (call from management commands)."""
    if get_client.cache_info().currsize:
        try:
            get_client().close()
        except Exception:  # noqa: BLE001
            pass
        get_client.cache_clear()


# ---------------------------------------------------------------------------
# Schema bootstrap
# ---------------------------------------------------------------------------

def ensure_schema() -> None:
    """Create VoltEntity + VoltDocumentChunk collections with cross-refs.

    Idempotent. Safe to call on every startup or from a migration.
    """
    import weaviate.classes.config as wc

    client = get_client()

    if not client.collections.exists(ENTITY_COLLECTION):
        client.collections.create(
            name=ENTITY_COLLECTION,
            multi_tenancy_config=wc.Configure.multi_tenancy(enabled=True),
            vectorizer_config=wc.Configure.Vectorizer.text2vec_weaviate(),
            properties=[
                wc.Property(name="owner_id", data_type=wc.DataType.INT),
                wc.Property(name="entity_id", data_type=wc.DataType.INT),
                wc.Property(name="entity_type", data_type=wc.DataType.TEXT),
                wc.Property(name="name", data_type=wc.DataType.TEXT),
                wc.Property(name="summary", data_type=wc.DataType.TEXT),
                wc.Property(name="data_json", data_type=wc.DataType.TEXT),
            ],
        )
        logger.info("Weaviate: created collection %s", ENTITY_COLLECTION)

    if not client.collections.exists(CHUNK_COLLECTION):
        client.collections.create(
            name=CHUNK_COLLECTION,
            multi_tenancy_config=wc.Configure.multi_tenancy(enabled=True),
            vectorizer_config=wc.Configure.Vectorizer.text2vec_weaviate(),
            properties=[
                wc.Property(name="owner_id", data_type=wc.DataType.INT),
                wc.Property(name="entity_id", data_type=wc.DataType.INT),
                wc.Property(name="document_id", data_type=wc.DataType.INT),
                wc.Property(name="version_id", data_type=wc.DataType.INT),
                wc.Property(name="document_type", data_type=wc.DataType.TEXT),
                wc.Property(name="filename", data_type=wc.DataType.TEXT),
                wc.Property(name="chunk_index", data_type=wc.DataType.INT),
                wc.Property(name="text", data_type=wc.DataType.TEXT),
            ],
            references=[
                wc.ReferenceProperty(
                    name="aboutEntity",
                    target_collection=ENTITY_COLLECTION,
                ),
            ],
        )
        logger.info("Weaviate: created collection %s", CHUNK_COLLECTION)

    # Add entity-to-entity + entity-to-chunk refs after both collections exist
    # (Weaviate requires the target collection to exist first.)
    entity = client.collections.get(ENTITY_COLLECTION)
    existing_refs = {r.name for r in entity.config.get().references}
    if "hasDocument" not in existing_refs:
        entity.config.add_reference(
            wc.ReferenceProperty(name="hasDocument", target_collection=CHUNK_COLLECTION)
        )
    if "relatesTo" not in existing_refs:
        entity.config.add_reference(
            wc.ReferenceProperty(name="relatesTo", target_collection=ENTITY_COLLECTION)
        )


def _ensure_tenant(collection_name: str, owner_id: int) -> None:
    """Ensure a per-owner tenant exists on the given collection."""
    from weaviate.classes.tenants import Tenant

    client = get_client()
    col = client.collections.get(collection_name)
    tenant_name = f"owner-{owner_id}"
    existing = {t.name for t in col.tenants.get().values()}
    if tenant_name not in existing:
        col.tenants.create(tenants=[Tenant(name=tenant_name)])


# ---------------------------------------------------------------------------
# Text extraction (mirrors volt_rag.py)
# ---------------------------------------------------------------------------

def _extract_text_from_bytes(filename: str, plaintext_bytes: bytes) -> str:
    name_lower = filename.lower()
    try:
        if name_lower.endswith(".pdf"):
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(plaintext_bytes))
            max_pages = getattr(settings, "RAG_PDF_MAX_PAGES", 120)
            parts = [p.extract_text() or "" for p in reader.pages[:max_pages]]
            return "\n".join(parts)
        if name_lower.endswith(".docx"):
            import docx
            doc = docx.Document(io.BytesIO(plaintext_bytes))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        return plaintext_bytes.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        logger.exception("Failed to extract text from %s", filename)
        return ""


def _render_extracted_data(document_type: str, extracted_data: dict) -> str:
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


def _chunk(text: str, size: int = 1200, overlap: int = 150) -> list[str]:
    """Lightweight chunker, same contract as core.contract_rag.chunk_text."""
    from core.contract_rag import chunk_text
    return chunk_text(text, size=size, overlap=overlap)


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------

def ingest_entity_data(
    *,
    owner_id: int,
    entity_id: int,
    entity_type: str,
    entity_name: str,
    data: dict,
    **_ignored,
) -> Optional[str]:
    """Upsert one VoltEntity object (one object per entity, not chunked).

    Weaviate's text2vec produces a single vector per object by default — we
    give it a rich 'summary' property containing flattened key-value lines
    so the whole entity is retrievable by any of its fields.
    """
    ensure_schema()
    _ensure_tenant(ENTITY_COLLECTION, owner_id)

    lines = [f"entity_type: {entity_type}", f"name: {entity_name}"]
    for key, value in (data or {}).items():
        if value in (None, "", [], {}):
            continue
        if isinstance(value, list):
            lines.append(f"{key}: {', '.join(str(v) for v in value)}")
        elif isinstance(value, dict):
            for k, v in value.items():
                lines.append(f"{key}.{k}: {v}")
        else:
            lines.append(f"{key}: {value}")

    summary = "\n".join(lines)
    uuid = _deterministic_uuid(f"entity:{owner_id}:{entity_id}")

    client = get_client()
    col = client.collections.get(ENTITY_COLLECTION).with_tenant(f"owner-{owner_id}")
    properties = {
        "owner_id": int(owner_id),
        "entity_id": int(entity_id),
        "entity_type": entity_type,
        "name": entity_name,
        "summary": summary,
        "data_json": json.dumps(data or {}, default=str),
    }
    if col.data.exists(uuid):
        col.data.update(uuid=uuid, properties=properties)
    else:
        col.data.insert(uuid=uuid, properties=properties)
    return str(uuid)


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
    """Upsert document chunks as VoltDocumentChunk objects, each linked to
    its parent VoltEntity via the aboutEntity cross-reference."""
    ensure_schema()
    _ensure_tenant(CHUNK_COLLECTION, owner_id)

    text = (
        _render_extracted_data(document_type, extracted_data)
        if extracted_data
        else _extract_text_from_bytes(filename, plaintext_bytes or b"")
    )
    if not text.strip():
        logger.warning(
            "Volt/Weaviate: no text for document_id=%s version_id=%s",
            document_id, version_id,
        )
        return None

    chunks = _chunk(text, size=chunk_size, overlap=overlap)
    if not chunks:
        return None

    entity_uuid = _deterministic_uuid(f"entity:{owner_id}:{entity_id}")
    client = get_client()
    col = client.collections.get(CHUNK_COLLECTION).with_tenant(f"owner-{owner_id}")

    # Idempotency: delete prior chunks for this version, then insert fresh.
    _delete_chunks_where(col, {"version_id": int(version_id)})

    with col.batch.dynamic() as batch:
        for idx, chunk in enumerate(chunks):
            batch.add_object(
                uuid=_deterministic_uuid(f"chunk:{owner_id}:{version_id}:{idx}"),
                properties={
                    "owner_id": int(owner_id),
                    "entity_id": int(entity_id),
                    "document_id": int(document_id),
                    "version_id": int(version_id),
                    "document_type": document_type,
                    "filename": filename,
                    "chunk_index": idx,
                    "text": chunk,
                },
                references={"aboutEntity": entity_uuid},
            )
    base_id = f"volt-doc-{document_id}-v{version_id}"
    logger.info(
        "Volt/Weaviate: ingested %d chunks for document_id=%s version_id=%s",
        len(chunks), document_id, version_id,
    )
    return base_id


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

def query_vault(
    *,
    owner_id: int,
    query: str,
    entity_ids: Optional[list[int]] = None,
    collection: str = "documents",
    n_results: int = 5,
    alpha: float = 0.6,
) -> list[dict]:
    """Hybrid BM25 + vector search, tenant-scoped to this owner.

    alpha=1.0 => pure vector, alpha=0.0 => pure BM25, 0.6 leans semantic.
    """
    from weaviate.classes.query import Filter

    ensure_schema()
    client = get_client()

    col_name = CHUNK_COLLECTION if collection == "documents" else ENTITY_COLLECTION
    _ensure_tenant(col_name, owner_id)
    col = client.collections.get(col_name).with_tenant(f"owner-{owner_id}")

    filters = None
    if entity_ids:
        filters = Filter.by_property("entity_id").contains_any(
            [int(e) for e in entity_ids]
        )

    try:
        res = col.query.hybrid(
            query=query,
            alpha=alpha,
            limit=n_results,
            filters=filters,
            return_metadata=["score"],
        )
    except Exception:  # noqa: BLE001
        logger.exception("Volt/Weaviate: hybrid query failed owner=%s", owner_id)
        return []

    output = []
    for obj in res.objects:
        props = dict(obj.properties or {})
        text = props.pop("text", None) or props.pop("summary", "")
        score = obj.metadata.score if obj.metadata else None
        # score is hybrid fused; convert to a distance-like field for caller parity
        output.append({
            "text": text,
            "metadata": props,
            "distance": (1.0 - score) if score is not None else None,
            "score": score,
        })
    return output


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

def delete_document_chunks(*, owner_id: int, document_id: int) -> None:
    try:
        ensure_schema()
        client = get_client()
        col = client.collections.get(CHUNK_COLLECTION).with_tenant(f"owner-{owner_id}")
        _delete_chunks_where(col, {"document_id": int(document_id)})
        logger.info("Volt/Weaviate: deleted chunks for document_id=%s", document_id)
    except Exception:  # noqa: BLE001
        logger.exception("Volt/Weaviate: delete_document_chunks failed")


def delete_entity_chunks(*, owner_id: int, entity_id: int) -> None:
    try:
        ensure_schema()
        client = get_client()
        chunks = client.collections.get(CHUNK_COLLECTION).with_tenant(f"owner-{owner_id}")
        entities = client.collections.get(ENTITY_COLLECTION).with_tenant(f"owner-{owner_id}")
        _delete_chunks_where(chunks, {"entity_id": int(entity_id)})
        _delete_chunks_where(entities, {"entity_id": int(entity_id)})
        logger.info("Volt/Weaviate: deleted all for entity_id=%s", entity_id)
    except Exception:  # noqa: BLE001
        logger.exception("Volt/Weaviate: delete_entity_chunks failed")


def _delete_chunks_where(col, eq_filter: dict) -> None:
    from weaviate.classes.query import Filter
    combined = None
    for key, value in eq_filter.items():
        f = Filter.by_property(key).equal(value)
        combined = f if combined is None else combined & f
    if combined is not None:
        col.data.delete_many(where=combined)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _deterministic_uuid(key: str) -> str:
    """Deterministic UUIDv5 so upserts are idempotent and predictable."""
    import uuid
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


# ---------------------------------------------------------------------------
# Backend router (let callers stay backend-agnostic)
# ---------------------------------------------------------------------------

def get_backend():
    """Return the active RAG backend module based on VOLT_VECTOR_BACKEND."""
    backend = getattr(settings, "VOLT_VECTOR_BACKEND", "chroma").lower()
    if backend == "weaviate":
        import sys
        return sys.modules[__name__]
    from core import volt_rag
    return volt_rag
