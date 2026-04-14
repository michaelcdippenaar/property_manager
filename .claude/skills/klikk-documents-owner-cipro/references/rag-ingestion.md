# RAG Ingestion Spec — `owner_documents` Collection

This file specs the server-side Phase 8 ingestion: turning `LandlordDocument` files into retrievable, metadata-tagged chunks in ChromaDB so the owner chat can cite specific clauses mid-conversation.

The existing pattern to mirror is `backend/core/contract_rag.py` (used for lease contracts, municipal bylaws, etc.) — same ChromaDB client, same embedding model, same chunking philosophy. Don't reinvent; copy.

---

## Collection

| Property | Value |
|----------|-------|
| Collection name | `owner_documents` |
| Embedding model | `nomic-embed-text-v1.5` (via sentence-transformers) |
| Distance metric | Cosine (ChromaDB default) |
| Manager module | `backend/core/owner_rag.py` (new, mirrors `contract_rag.py`) |

**Never query without filtering by `landlord_id`.** The collection is shared across all landlords in the system — unfiltered queries would leak POPIA-protected personal data across tenants of the platform. Enforce the filter in the collection manager, not at the call site.

---

## Chunking Strategy

South African CIPC/FICA documents vary wildly in length:
- **Short structured docs** (CoR14.3, CoR39, CK1, SA ID, bank letter): typically 1–3 pages, often visually dense
- **Long narrative docs** (Trust Deed, MOI, Partnership Agreement): 10–50+ pages with numbered clauses

Use a two-tier strategy:

### Tier 1 — Short structured docs (default)
One chunk per page. Preserves the visual-block semantics that Claude Vision already captured during classification.

### Tier 2 — Long narrative docs (> 3 pages OR > 4000 chars)
Sliding window within each page: 500-token chunks with 100-token overlap. Preserves clause boundaries where possible (try to split on `\n\n`, double line breaks, numbered headings like `7.` or `(a)`).

### Chunk text content

Each chunk's text payload includes:
1. A prepended context header: `[doc_type=trust_deed | page=2/15 | entity=Smith Family Trust]`
2. The raw extracted text from that chunk
3. For structured docs, append the classified fields as natural language: `Extracted fields: registration_number=2018/123456/07; director=John Smith.`

The prepended header means an embedding query for "who are the trustees of Smith Family Trust" has something concrete to match against even if the page content uses different phrasing.

---

## Metadata Schema (per chunk)

ChromaDB metadata is a flat dict of primitives. Keep it predictable:

```python
{
    "landlord_id": int,                    # LandlordDocument.landlord_id — always filter on this
    "document_id": int,                    # LandlordDocument.pk
    "filename": str,                       # LandlordDocument.filename
    "doc_type": str,                       # Classified doc type — snake_case
                                           # "cor14_3" | "cor39" | "cor15_1a" | "ck1" | "ck2"
                                           # | "trust_deed" | "letters_of_authority"
                                           # | "id_sa" | "passport" | "bank_confirmation"
                                           # | "proof_of_address" | "sars_tax" | "vat_registration"
                                           # | "moi" | "partnership_agreement" | "title_deed"
                                           # | "marriage_certificate" | "antenuptial_contract"
                                           # | "other"
    "entity_type": str,                    # "company" | "trust" | "cc" | "individual" | "partnership"
    "entity_subtype": str | None,          # "pty_ltd" | "npc" | "public_ltd" | "soc_ltd" | None
    "person_ids": str,                     # Comma-separated SA ID numbers mentioned in this chunk
                                           # (ChromaDB doesn't support list metadata — flatten to CSV)
    "expiry_date": str | None,             # ISO date for time-sensitive docs (proof of address,
                                           # Letters of Authority, tax clearance)
    "page_number": int,                    # 1-indexed
    "total_pages": int,
    "chunk_index": int,                    # 0-indexed within the document
    "ingested_at": str,                    # ISO timestamp
    "classification_version": str,         # e.g. "2026-04" — bump when extraction rules change
                                           # so stale chunks can be detected and re-ingested
}
```

### Why `person_ids` is a CSV not a list

ChromaDB metadata values must be scalars (`str`, `int`, `float`, `bool`). To filter "find chunks that mention ID 7601015009087" across all landlords, store IDs as `",7601015009087,"` (with sentinel commas) and use ChromaDB's `$contains` on the string. The sentinel commas prevent substring false positives (`"560101..." $contains "01015"` without sentinels matches; with sentinels it doesn't).

---

## Ingestion Triggers

### Primary: post-classify signal

Attach a `post_save` signal to `Landlord` that fires when `classification_data` changes. The handler enqueues a Celery task so the web request doesn't block on embedding.

```python
# backend/apps/properties/signals.py
@receiver(post_save, sender=Landlord)
def enqueue_owner_rag_ingestion(sender, instance, **kwargs):
    update_fields = kwargs.get("update_fields") or set()
    if "classification_data" in update_fields or kwargs.get("created"):
        ingest_owner_documents.delay(instance.pk)
```

### Celery task

```python
# backend/apps/properties/tasks.py
@shared_task
def ingest_owner_documents(landlord_id: int):
    landlord = Landlord.objects.get(pk=landlord_id)
    # 1. Delete existing chunks for this landlord (idempotent re-ingest)
    owner_rag.delete_by_landlord(landlord_id)
    # 2. For each LandlordDocument:
    #    a. Extract text (extraction_utils.extract_pdf_text)
    #    b. Chunk per strategy above
    #    c. Embed + upsert with metadata
    # 3. Same for landlord.registration_document if present
```

### Backfill command

```python
# backend/apps/properties/management/commands/backfill_owner_rag.py
# Iterate all Landlord records with non-null classification_data,
# enqueue ingest_owner_documents for each. Safe to re-run.
```

---

## Query Patterns

### Semantic search within a landlord

```python
owner_rag.query(
    text="who are the current trustees",
    landlord_id=42,
    top_k=5,
)
```

The collection manager *always* injects `landlord_id` into the `where` filter. There is no `query_all()` method.

### Filter by doc type (e.g. "find the Letters of Authority")

```python
owner_rag.query(
    text="letters of authority",
    landlord_id=42,
    where={"doc_type": "letters_of_authority"},
    top_k=3,
)
```

### Find documents mentioning a specific person (cross-entity)

For system-wide beneficial ownership lookups (an *admin-only* flow, out of v1 UI scope), filter by `person_ids` CSV substring. This is NOT exposed to agents or landlords — only platform admins investigating control concentration.

---

## What NOT to embed

- Full bank account numbers — redact to last 4 before the text hits ChromaDB
- Passport MRZ lines — same treatment; the extracted structured fields are enough
- Signatures and biometric markers — images only, no text equivalent needed

Redaction happens in the chunking step, before embedding. See `extraction_utils.py` — add a `redact_sensitive(text)` helper if one doesn't exist yet.

---

## Versioning & Re-ingestion

When the extraction prompt or classification taxonomy changes:
1. Bump `CLASSIFICATION_VERSION` constant in `owner_rag.py`
2. Run the backfill command
3. The `classification_version` metadata lets you query "all chunks from v2026-03 or earlier" and selectively re-ingest

This matters because chat responses quote document clauses verbatim — if the extraction prompt changed significantly, old chunks may have different field boundaries than new ones, and mixing them produces incoherent answers.
