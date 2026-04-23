# Vault33 — System Document

> **Version:** 1.0 · **Date:** 2026-04-17 · **Author:** MC Dippenaar / Claude  
> **Status:** Draft — scoping  
> **Codebase:** `backend/apps/the_volt/`

---

## 1. Executive Summary

Vault33 is Klikk's **personal-data vault** — a single-tenant, encrypted, auditable store for every person, company, trust, and asset that touches the Klikk ecosystem. It exists because South African property management sits at the intersection of three demanding regulatory regimes:

| Regime | What it demands |
|--------|----------------|
| **POPIA** (Protection of Personal Information Act 4/2013) | Lawful basis per data item, data-subject rights (access/correct/delete), processing records (§17), breach notification |
| **FICA** (Financial Intelligence Centre Act 38/2001) | KYC/CDD on property transactions, 5-year record retention, beneficial ownership identification |
| **RHA** (Rental Housing Act 50/1999) | Deposit trust accounting, inspection records, tenant communication logs |

Vault33 is the **data layer** that makes compliance automatic rather than aspirational. Every entity has a type-aware schema, every document is encrypted at rest, every mutation is audit-logged, and every external data share requires owner consent via OTP.

### Where Vault33 fits in the Klikk stack

```
┌─────────────────────────────────────────────────────────────┐
│                    Klikk Platform                            │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │  Admin    │  │  Tenant  │  │  Tenant  │  │  Marketing │  │
│  │  SPA      │  │  Mobile  │  │  Web App │  │  Website   │  │
│  │  (Vue 3)  │  │ (Flutter)│  │  (Vue 3) │  │  (Astro)   │  │
│  └─────┬─────┘  └────┬─────┘  └────┬─────┘  └────────────┘  │
│        │              │             │                         │
│        └──────────┬───┘─────────────┘                        │
│                   ▼                                          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Django 5 + DRF API                         │ │
│  │  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌─────────────┐  │ │
│  │  │ Leases  │ │Propertys│ │ Tenants  │ │  E-Signing   │  │ │
│  │  └────┬────┘ └────┬────┘ └────┬─────┘ └──────┬──────┘  │ │
│  │       │           │           │               │         │ │
│  │       └───────────┴───────────┴───────────────┘         │ │
│  │                         │                               │ │
│  │                         ▼                               │ │
│  │  ┌──────────────────────────────────────────────────┐   │ │
│  │  │                  VAULT33                         │   │ │
│  │  │  ┌────────────────────────────────────────────┐  │   │ │
│  │  │  │ Entities · Documents · Relationships       │  │   │ │
│  │  │  │ Classification · Encryption · Audit        │  │   │ │
│  │  │  │ Gateway (external data sharing)            │  │   │ │
│  │  │  │ MCP Server (Claude / AI access)            │  │   │ │
│  │  │  │ ChromaDB (vector search)                   │  │   │ │
│  │  │  └────────────────────────────────────────────┘  │   │ │
│  │  └──────────────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

Vault33 is the **compliance engine beneath the product**. Leases, properties, tenants, and e-signing all produce data that flows into Vault33 for long-term storage, FICA record-keeping, and data-subject rights fulfilment.

---

## 2. Architecture

### 2.1 Design principles

1. **Single-tenant isolation** — Each user (vault owner) has a `VaultOwner` record. All entities, documents, relationships, and audit logs are scoped to that owner. No cross-owner queries are possible.

2. **Encryption at rest** — Every document file is Fernet-encrypted with a per-owner symmetric key derived via PBKDF2-HMAC-SHA256 (100,000 iterations) from Django's `SECRET_KEY` + owner ID salt. Plaintext never touches disk.

3. **Append-only audit** — Every mutation (create, update, deactivate, link, unlink, attach) produces a `VaultWriteAudit` row with before/after snapshots. This satisfies POPIA §17 processing records and FICA audit trail requirements. The model has no `change` or `delete` admin permissions.

4. **Schema-driven evolution** — Entity structures, document types, and relationship types are all catalogue-driven (database rows, not code). New entity fields, document types, or relationship kinds can be added without migrations.

5. **MCP-first interface** — The primary consumer of Vault33 is Claude (via MCP). The REST API exists for the admin SPA and gateway subscribers, but the MCP server is the richest interface — it exposes upsert semantics, graph queries, and document upload/download.

6. **Consent-gated sharing** — External parties (conveyancers, banks, agents) access data via the Gateway, which requires an OTP-verified consent flow. Every checkout is signed (HMAC-SHA256) and produces an immutable audit record.

### 2.2 Technology stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| ORM / API | Django 5.x + DRF | PostgreSQL backend |
| Encryption | `cryptography.fernet` | Per-owner key derivation |
| Vector store | ChromaDB | Local SQLite instance (`rag_chroma/chroma.sqlite3`) |
| MCP transport | FastMCP (Python) | Stdio (Claude Desktop/Code) + Streamable HTTP |
| File storage | Django `FileField` | `.enc` encrypted blobs on local filesystem (`backend/media/vault/`) |
| Auth | JWT (simplejwt) for REST; API key (SHA-256 hash) for MCP + Gateway | Owner keys prefixed `volt_owner_`, subscriber keys separate |

### 2.3 Module map

```
backend/apps/the_volt/
├── owners/              # VaultOwner, VaultOwnerAPIKey
│   ├── models.py
│   ├── views.py
│   └── serializers.py
├── entities/            # VaultEntity, EntityRelationship, EntityDataField
│   ├── models.py        # EntityType enum, DATA_SCHEMAS, RelationshipTypeCatalogue
│   ├── views.py         # CRUD ViewSets + hybrid graph/vector query
│   ├── serializers.py
│   └── query_service.py # Graph traversal + ChromaDB vector search
├── documents/           # VaultDocument, DocumentVersion, DocumentVerification
│   ├── models.py        # DocumentTypeCatalogue (~85 SA doc types)
│   ├── views.py         # Upload, version, download (decrypt+stream)
│   ├── serializers.py
│   └── signals.py       # Auto-index to ChromaDB on version create
├── schemas/             # EntitySchema (versioned, per-country)
│   ├── models.py        # ZA_DEFAULT_SCHEMAS
│   ├── views.py
│   └── serializers.py
├── gateway/             # External data sharing (subscribers, consent, checkout)
│   ├── models.py        # DataSubscriber, DataRequest, DataCheckout, VaultWriteAudit
│   ├── views.py         # Request/approve/deny/checkout flow
│   ├── serializers.py
│   ├── auth.py          # X-Volt-API-Key authentication
│   └── checkout.py      # CheckoutService — package, hash, sign, deliver
├── encryption/
│   └── utils.py         # Fernet encrypt/decrypt, HMAC sign/verify, OTP, API key gen
├── classification/      # Document classification + entity engine (35 Python files)
│   ├── entity_engine/   # attributes, slot_engine, filename_signals, lazy_extraction_pipeline, required_docs, vectorisation_rules
│   ├── document_provenance/  # fingerprint, entity_anagram, classification_number (VCN), pipeline_hook, duplicate_broker, stamp, submitter
│   │   └── schemas/     # JSON schemas (e.g. beneficial_ownership_register.json — 577 lines)
│   ├── extractors/      # sa_id_layouts
│   ├── skills/          # 5 extraction skills: sa_smart_id_card, sa_passport, sa_drivers_licence, sa_green_id_book, sa_unabridged_birth_certificate
│   │   └── _shared/     # vision_ocr, sa_id, provenance
│   ├── router/          # identity_router
│   ├── prompts/         # Per-doc-type Claude prompts
│   ├── consensus_extract.py   # Multi-model consensus extraction
│   ├── phase1_group.py        # Initial grouping
│   └── run_haiku_reindex.py   # Batch re-extraction + ChromaDB reindex
├── mcp/                 # MCP server
│   ├── server.py        # Stdio transport (Claude Desktop/Code)
│   ├── http_server.py   # Streamable HTTP transport
│   ├── tools/
│   │   ├── read.py      # 10 read tools
│   │   └── write.py     # 13 write tools
│   ├── auth.py          # API key resolution (env var or HTTP header)
│   ├── audit.py         # Write audit logging
│   ├── upload_from_manifest.py  # 3-stage bulk ingestion script
│   ├── UPLOAD_PIPELINE.md       # Ingestion pipeline documentation
│   └── manifests/       # JSONL ingestion manifests (16 raw + 15 enriched batches; 1,082 entries)
├── docs/                # Architecture diagrams
├── management/commands/
│   └── volt_mcp_http.py # Django management command for HTTP MCP server
├── admin.py             # All models registered
├── urls.py              # REST endpoint routing
└── migrations/          # 10 migrations (initial → seed catalogues; 0005+ currently uncommitted)
```

---

## 3. Data Model

### 3.1 Entity types

Vault33 supports six entity types, each with a type-specific data schema:

| Type | Identity key | Data fields |
|------|-------------|-------------|
| `personal` | `id_number` | id_number, date_of_birth, nationality, tax_number, address, phone, email, marital_status, spouse_name |
| `trust` | `trust_number` | trust_name, trust_number, trust_type, master_reference, trustees, beneficiaries, deed_date, tax_number |
| `company` | `reg_number` | reg_number, vat_number, company_type, registration_date, registered_address, directors, shareholders, financial_year_end, tax_number |
| `close_corporation` | `reg_number` | reg_number, vat_number, members, member_interest_pct, registered_address, financial_year_end |
| `sole_proprietary` | `id_number` | owner_name, trade_name, id_number, tax_number, vat_number, business_address, fic_registered |
| `asset` | `registration_number` | asset_type, description, registration_number, acquisition_date, acquisition_value, current_value, insured, insurer, address |

**Identity matching**: When upserting, the system matches on identity key first (e.g. `id_number` for personal, `reg_number` for company). If no identity key is provided, it falls back to exact name match within the same entity type.

### 3.2 Relationship graph

Entities connect via directed edges (`EntityRelationship`), each typed by a `RelationshipTypeCatalogue` entry:

| Code | Label | From → To | Example |
|------|-------|-----------|---------|
| `director_of` | Director of | personal → company | MC Dippenaar → LucaNaude (Pty) Ltd |
| `trustee_of` | Trustee of | personal → trust | MC Dippenaar → Naude Dippenaar Trust |
| `beneficial_owner_of` | Beneficial owner of | personal → company/trust | MC → LucaNaude (via Trust) |
| `shareholder_of` | Shareholder of | personal/trust/company → company | Naude Dippenaar Trust → LucaNaude (Pty) Ltd |
| `member_of` | Member of | personal → close_corporation | — |
| `holds_asset` | Holds asset | personal/company/trust → asset | LucaNaude (Pty) Ltd → ERF 17869(7) |
| `operates_as` | Operates as | personal → sole_proprietary | — |
| `guarantor_for` | Guarantor for | personal → company/trust | — |
| `leases_from` | Leases from | personal → asset | Tenant → Property |
| `parent_of` | Parent of | personal → personal | MC Dippenaar → Lia Dippenaar |

**Metadata on edges**: Each relationship carries optional JSON metadata: `share_pct`, `effective_date`, `end_date`, `notes`. This enables queries like "who held >25% of shares on 2025-10-21?"

**BO chain resolution**: The graph supports multi-hop traversal. Example:

```
MC Dippenaar (personal)
  ├── trustee_of → Naude Dippenaar Trust (trust)
  │     └── shareholder_of → LucaNaude (Pty) Ltd (company) [share_pct: 100]
  │           └── holds_asset → ERF 17869(7) Voliere (asset)
  └── director_of → LucaNaude (Pty) Ltd (company)
```

### 3.3 Document management

Documents are versioned and encrypted:

```
VaultDocument (logical container)
  ├── entity (FK → VaultEntity)
  ├── document_type (e.g. "cipc_certificate")
  ├── label (e.g. "CoR14.3 Registration Certificate")
  └── current_version → DocumentVersion
       ├── version_number (auto-incremented)
       ├── file (.enc encrypted blob)
       ├── original_filename
       ├── sha256_hash (of plaintext, for tamper detection)
       ├── extracted_data (JSON — client-supplied OCR output)
       └── chroma_id (ChromaDB vector ID)
```

**~85 document types** are seeded via `DocumentTypeCatalogue`, covering:
- Identity: SA Smart ID Card, Passport, Driver's Licence, Green ID Book, Unabridged Birth Certificate
- FICA: Proof of Address, Bank Confirmation, SARS Notice of Registration
- CIPC: CoR14.3, CoR14.1, CoR14.1A, CoR15.1A, Share Certificate, Resolutions
- Trust: Letters of Authority, Trust Deed
- Asset: Title Deed, Insurance Policy, Rates Clearance
- Financial: Audited financials, Tax clearance, VAT registration

Each catalogue entry defines:
- `extraction_schema` — expected OCR fields (e.g. for a Smart ID: id_number, surname, names, date_of_birth, gender, citizenship, country_of_birth)
- `issuing_authority` — e.g. "CIPC", "DHA", "SARS", "Master of High Court"
- `default_validity_days` — auto-expiry (e.g. Proof of Address = 90 days)
- `email_sender_patterns` / `email_subject_patterns` — for inbound document classification
- `classification_signals` — free-text AI hints for routing

### 3.4 Field-level provenance

Every data field on an entity can be tracked individually via `EntityDataField`:

| Attribute | Purpose |
|-----------|---------|
| `field_key` | Which field (e.g. "id_number", "tax_number") |
| `value` | The actual value (JSON) |
| `verification_status` | UNVERIFIED → SELF_ATTESTED → DOCUMENT_BACKED → OFFICIAL_SOURCE → REJECTED |
| `source_document_version` | FK to the document that backs this field |
| `extraction_source` | CLIENT_OCR, MANUAL_ENTRY, API_LOOKUP, AI_EXTRACTION |
| `expiry_date` | When the backing document expires (e.g. Proof of Address after 90 days) |

This enables **readiness assessment**: "Is this entity FICA-compliant?" = "Are all required fields at DOCUMENT_BACKED or higher, with non-expired backing documents?"

### 3.5 Entity-Relationship Diagram

```
VaultOwner ─1:N──▶ VaultEntity
     │                  │
     │                  ├──1:N──▶ VaultDocument ─1:N──▶ DocumentVersion
     │                  │                                      │
     │                  ├──1:N──▶ EntityDataField ◀────────────┘
     │                  │              (source_document_version FK)
     │                  │
     │                  └──M:N──▶ EntityRelationship
     │                                │
     │                                └──FK──▶ RelationshipTypeCatalogue
     │
     ├──1:N──▶ VaultOwnerAPIKey
     │
     ├──1:N──▶ VaultWriteAudit (append-only)
     │
     └──1:N──▶ DataRequest ──1:N──▶ DataCheckout
                    │
                    └──FK──▶ DataSubscriber

Catalogues (independent):
  - DocumentTypeCatalogue (~85 SA doc types)
  - RelationshipTypeCatalogue (10 system types)
  - EntitySchema (versioned field definitions per entity_type + country)
```

---

## 4. MCP Server

### 4.1 Transports

| Transport | Entry point | Auth | Use case |
|-----------|------------|------|----------|
| **Stdio** | `python -m apps.the_volt.mcp.server` | `VOLT_OWNER_API_KEY` env var | Claude Desktop, Claude Code |
| **HTTP (Streamable)** | `python manage.py volt_mcp_http --port 8765` | `Authorization: Bearer volt_owner_xxx` | claude.ai custom connectors, remote agents |

### 4.2 Tool inventory

**Read tools** (10):

| Tool | Purpose |
|------|---------|
| `ensure_vault` | Confirm vault exists, return vault_id + user_email |
| `list_entities` | List entities with optional type filter |
| `find_entity` | Name substring search |
| `get_entity` | Full record + all relationships (in/out) |
| `list_documents` | Document metadata by entity or type |
| `list_document_types` | DocumentTypeCatalogue with extraction schemas |
| `get_document_type` | Full detail for one document type |
| `list_relationship_types` | Filtered relationship catalogue |
| `download_document` | Decrypt + return base64 |
| `get_api_schema` | Complete API schema (tools, endpoints, types) |

**Write tools** (13):

| Tool | Purpose |
|------|---------|
| `ensure_vault` | Create vault if absent |
| `upsert_entity` | Generic create/merge for any entity type |
| `upsert_owner` | Convenience for personal entities |
| `upsert_property` | Convenience for asset entities |
| `upsert_tenant` | Convenience for personal + optional leases_from link |
| `upsert_company` | Convenience for company entities |
| `upsert_trust` | Convenience for trust entities |
| `upsert_close_corporation` | Convenience for CC entities |
| `upsert_sole_proprietor` | Convenience for sole prop entities |
| `update_entity` | Update by ID (name, data, is_active) |
| `deactivate_entity` | Soft-delete (set is_active=False) |
| `link_entities` | Create/update directed relationship edge (idempotent) |
| `unlink_entities` | Remove relationship edge |
| `attach_document` | Upload file + encrypt + store |

### 4.3 Prompts

The MCP server exposes two workflow prompts:
- **`document_upload_workflow`** — Step-by-step procedure for uploading and classifying documents
- **`entity_setup_workflow`** — Entity graph bootstrapping (create entities, link relationships, attach documents)

---

## 5. Gateway (External Data Sharing)

### 5.1 Flow

```
External party (e.g. STBB conveyancers)
  │
  ├── 1. Register as DataSubscriber (admin provisions API key)
  │
  ├── 2. POST /gateway/request/ with X-Volt-API-Key
  │      { requested_entity_types, requested_document_types,
  │        requested_fields, purpose, vault_owner_email }
  │
  │      → System generates OTP, sends SMS to vault owner
  │      → Returns access_token for polling
  │
  ├── 3. Vault owner approves via:
  │      - Admin SPA: POST /gateway/requests/{token}/approve/
  │      - Public link: POST /gateway/requests/{token}/approve-public/ + OTP
  │
  └── 4. POST /gateway/checkout/ with access_token
         → CheckoutService collects entities + decrypted docs
         → Packages as JSON, hashes (SHA-256), signs (HMAC-SHA256)
         → Returns signed package
         → Creates immutable DataCheckout audit record
```

### 5.2 Security controls

- OTP is 6-digit, SHA-256 hashed, 3 attempts before lockout
- Request expires after 48 hours
- Package signature verifiable by vault owner
- Every checkout logged to `DataCheckout` with `entities_shared`, `documents_shared`, `data_hash`, `ip_address`
- Delivery methods: REST, MCP, GraphQL, INTERNAL

---

## 6. Classification Engine

### 6.1 Entity engine (`classification/entity_engine/`)

The entity engine bridges raw document extractions to structured entity data:

- **`attributes.py`** — Canonical attribute registry per entity type. Each attribute defines: data_type, is_identity, is_root, validators, sourceable_from (which document types can provide this field), autofill_priority
- **`slot_engine.py`** — Readiness assessment. For each entity, evaluates every required field as FILLED, EMPTY, EXPIRED, or MISMATCHED. Generates autofill proposals with full provenance chain.
- **`required_docs.py`** — Resource packages per entity type: which documents are mandatory, optional, or conditional
- **`vectorisation_rules.py`** — Cross-document frequency indexing for hybrid search

Also in `entity_engine/`: **`filename_signals.py`** (inbound classification cues from paths/filenames) and **`lazy_extraction_pipeline.py`** (staged processing of uploads, defers heavy OCR until needed).

### 6.2 Document provenance (`classification/document_provenance/`)

- **`fingerprint.py`** — Content-based deduplication (prevents re-uploading the same document)
- **`entity_anagram.py`** — Fuzzy name matching for entity resolution across documents
- **`classification_number.py`** — VCN (Vault Classification Number) generator for unique document identification
- **`pipeline_hook.py`** — Ingestion hook for processing new uploads through the classification pipeline
- **`duplicate_broker.py`** — Merge handling when duplicate submissions are detected
- **`stamp.py`** — Marks documents with Volt classification stamps
- **`submitter.py`** — Tracks who uploaded what and when
- **`schemas/beneficial_ownership_register.json`** — JSON Schema Draft 7 for BO Register (577 lines, `$schema_version: volt.bo_register@v1`)

### 6.3 Extraction skills (`classification/skills/`)

Per-document-type extraction specialisations (all **built and on disk**, uncommitted):
- `sa_smart_id_card/` — SA Smart ID Card 2013+ (front + back layout parsing)
- `sa_passport/` — SA Machine-Readable Passport
- `sa_drivers_licence/` — SA Driver's Licence card
- `sa_green_id_book/` — Legacy green bar-coded ID book
- `sa_unabridged_birth_certificate/` — DHA-5/19 Unabridged Birth Certificate

Shared infrastructure (`_shared/`):
- `vision_ocr.py` — Vision model integration for document image extraction
- `sa_id.py` — SA ID number validation, date-of-birth derivation, gender/citizenship parsing
- `provenance.py` — Field-level source tracking through extraction pipeline

### 6.4 Router & consensus extraction

- **`router/identity_router.py`** — Routes identity documents to the correct extraction skill based on filename signals + content inspection
- **`consensus_extract.py`** — Multi-model consensus extraction (runs multiple LLM passes and reconciles output)
- **`phase1_group.py`** — Initial document grouping / classification before deep extraction
- **`run_haiku_reindex.py`** — Batch re-extraction and ChromaDB reindexing

### 6.5 Ingestion pipeline (manifest → enrich → upload)

Bulk-import workflow documented in `mcp/UPLOAD_PIPELINE.md`, implemented in `mcp/upload_from_manifest.py`:

```
Source folders (PDFs, DOCX, XLSX)
       │
       ▼
  1. MANIFEST — scan folders, classify each file (filename signals + AI)
       │
       ▼
  mcp/manifests/<entity>_manifest.jsonl        (raw, no extracted_data)
       │
       ▼
  2. ENRICH — OCR/read each PDF, extract structured fields via Claude
       │
       ▼
  mcp/manifests/enriched/<batch>.jsonl         (with extracted_data)
       │
       ▼
  3. UPLOAD — create entities, attach documents, build relationships
       │
       ▼
  The Volt (PostgreSQL + encrypted files + ChromaDB vectors)
```

Each manifest line describes one source document:

```json
{
  "source_path": "/absolute/path/to/doc.pdf",
  "entity_name": "2 Otterkuil Street",
  "entity_type": "asset",
  "document_type_code": "otp",
  "confidence": "high",
  "label": "2 Otterkuil OTP (Klikk Purchase)",
  "extracted_data": { "registration_number": "ERF 3581", "purchase_price": 8500000, ... }
}
```

After enrichment, each row carries a full `extracted_data` payload (e.g. an OTP row carries seller, buyer, purchase_price, deposit, bond amount, title deed, ERF size, conveyancers, etc.) ready to be stored on `DocumentVersion.extracted_data` and to populate `EntityDataField` rows.

**Current queue:** 1,082 manifest entries across 16 entity clusters, 15 enriched batches.

---

## 7. Compliance Mapping

### 7.1 POPIA

| POPIA requirement | Vault33 implementation |
|-------------------|----------------------|
| §8 — Lawful processing conditions | Each PI item has a lawful basis tag in the data flow inventory |
| §14 — Collection directly from data subject | Document upload tracks submitter identity |
| §17 — Processing records | `VaultWriteAudit` — append-only log of every mutation |
| §19 — Security safeguards | Fernet encryption at rest, per-owner key derivation, HMAC package signing |
| §20–21 — Operator agreements | Gateway `DataSubscriber` + consent flow |
| §22 — Breach notification | Audit trail enables forensic analysis of what was exposed |
| §23 — Data subject access | `get_entity` + `list_documents` + `download_document` |
| §24 — Correction/deletion | `update_entity` + `deactivate_entity` (soft delete; hard delete blocked by FICA retention) |
| §72 — Cross-border transfer | Gateway checkout logs delivery destination |

### 7.2 FICA

| FICA requirement | Vault33 implementation |
|------------------|----------------------|
| §21 — CDD (Know Your Customer) | Entity schemas enforce collection of ID, address, source of funds |
| §21A — Enhanced CDD | BO chain resolution via multi-hop relationship traversal |
| §56(7) Companies Act — BO Register | `beneficial_ownership_register.json` schema; graph models indirect ownership |
| 5-year retention | Document retention tracked via `DocumentVerification.expiry_date` |
| Audit trail | `VaultWriteAudit` + `DataCheckout` immutable records |

### 7.3 RHA

| RHA requirement | Vault33 implementation |
|-----------------|----------------------|
| §5(3) — Deposit records | Asset entity + financial documents attached |
| Inspection reports | Document versions with photo attachments |
| Communication logs | Relationship metadata + document trail |

---

## 8. Current State

### 8.1 What exists today

| Component | Status | Notes |
|-----------|--------|-------|
| Django models (all 15+) | ✅ Built | Fully migrated, 10 migrations |
| REST API (all endpoints) | ✅ Built | CRUD for entities, documents, schemas, gateway |
| MCP server (stdio + HTTP) | ✅ Built | 23 tools (10 read + 13 write) |
| Encryption (Fernet per-owner) | ✅ Built | Encrypt/decrypt/sign/verify |
| Audit logging | ✅ Built | Append-only VaultWriteAudit |
| Document type catalogue | ✅ Seeded | ~85 SA document types |
| Relationship type catalogue | ✅ Seeded | 10 system relationship types |
| Entity schemas (ZA defaults) | ✅ Seeded | All 6 entity types |
| Gateway consent flow | ✅ Built | OTP, approval, checkout, signing |
| Classification engine | ✅ Built | Full pipeline: entity_engine (attributes, slot engine, filename_signals, lazy_extraction_pipeline, vectorisation_rules, required_docs), document_provenance (fingerprint, dedup, entity_anagram, VCN, stamp, submitter), router, and 5 extraction skills (Smart ID, Passport, Driver's Licence, Green ID Book, Unabridged Birth Certificate) |
| Ingestion pipeline | ✅ Built | 3-stage manifest → enrich → upload via `mcp/upload_from_manifest.py`; see §4A |
| ChromaDB indexing | ⚠️ Partial | Auto-indexes on doc upload; query integration basic |
| Test coverage | ❌ None | Zero `test_*.py` files in `apps/the_volt/` — 17,974 LoC with no automated verification |
| Admin SPA (Vue) | ❌ Not started | No frontend for vault management |
| Tenant-facing data rights | ❌ Not started | POPIA §23/§24 self-service |
| Production deployment | ❌ Not started | Local-only, no cloud infra |
| Per-recipient document watermarking | ❌ Not designed | Checkout package hash exists; per-recipient payload fingerprint planned for Phase 5 |
| Container-based delivery | ❌ Not designed | Encrypted PDF / `.klikk` container / streaming viewer planned for Phase 5 |

### 8.2 Data in vault (current)

As of 2026-04-17 (audited from on-disk evidence; live DB counts pending MCP reconnect):

**Persisted encrypted data:**
- **741 MB** of encrypted vault media in `backend/media/vault/`
- **496 `.enc` files** on disk (ciphertext blobs, one per DocumentVersion)

**Entities (last MCP snapshot, 2026-04-16)**:
- **1 vault owner** (mc@tremly.com)
- **90 active entities**: 78 personal, 12 assets, 0 trusts, 0 companies, 0 CCs, 0 sole props

**Ingestion queue:**
- **1,082 manifest entries** across **16 entity clusters** awaiting / partially-completed ingestion
- **15 enriched batches** with structured OCR data extracted (ready for upload stage)

Top entity manifests by size:

| Entity | Manifest entries |
|---|---|
| Tremly (Pty) Ltd | 704 |
| Klikk (Pty) Ltd | 130 |
| MC Dippenaar Jnr (personal) | 78 |
| LucaNaude (Pty) Ltd | 49 |
| MLD Trust | 49 |
| MC Testamentere Trust | 25 |
| Michael Dippenaar Snr | 12 |
| Koniba Beleggings | 10 |
| Stefanie Dippenaar | 10 |
| MC Dippenaar Boerderye | 7 |
| Lia Dippenaar | 5 |
| Naude Dippenaar Trust | 2 |
| Joyle, Luca, Tanja (individuals) | 1–0 each |

**Known reconciliation gap:** the count of `DocumentVersion` rows in the DB has not been verified against the 496 on-disk `.enc` files. Any orphaned ciphertext (files without DB pointers, typically from interrupted ingestions) must be garbage-collected before production. This is a Phase 0 action item.

**Known uncommitted state:** major Volt work is staged but not committed (9 files, +1,247 lines, mostly MCP tool expansion) and a further substantial body of code is untracked (full `classification/` module — 35 files — plus 6 unrun migrations, the ingestion script, and all manifests). The "installed" state differs materially from the "committed" state.

---

## 9. Integration Points

### 9.1 Inbound data flows (into Vault33)

| Source | Data | Mechanism |
|--------|------|-----------|
| Admin SPA (agent/owner portal) | Entity CRUD, document uploads | REST API |
| Claude (via MCP) | Entity upserts, doc classification, BO analysis | MCP stdio/HTTP |
| Tenant mobile app | Tenant profile, ID uploads, FICA docs | REST API (future) |
| Email ingestion | Inbound documents (invoices, statements) | Classification pipeline (future) |
| CIPC API | Company registration data | API lookup (future) |
| TransUnion | Credit checks | Operator API (future) |

### 9.2 Outbound data flows (from Vault33)

| Destination | Data | Mechanism |
|-------------|------|-----------|
| STBB / conveyancers | FICA pack (entities + documents) | Gateway checkout |
| Banks (bond applications) | KYC data package | Gateway checkout |
| SARS | Tax compliance data | Manual export (future) |
| Information Regulator | DSAR responses | Data subject rights flow (future) |
| Klikk admin SPA | Entity display, document viewer | REST API |

### 9.3 The Klikk data flow connection

From the Klikk data flow page (`localhost:8006/data`), Vault33 is the storage + compliance layer for:

1. **Application & screening** — ID, credit, criminal, financials → stored as encrypted documents on entities
2. **Lease execution** — Signed lease PDF, signature audit trail → document versions
3. **Deposit** — Trust account numbers, interest ledger → financial documents on asset entities
4. **Onboarding** — Phone, email, emergency contacts → personal entity data fields
5. **Active tenancy** — Payment history, communication logs → document attachments
6. **Maintenance** — Damage photos, supplier contacts → document versions + relationship metadata
7. **Move-out** — Inspection reports, damage lists → document versions
8. **Refund** — Banking details, deduction statements → encrypted documents

Vault33 answers the question the data flow page asks: **"Where does this PI physically live, who can access it, and how long do we keep it?"**

---

## 10. Security Model

### 10.1 Authentication

| Context | Method | Details |
|---------|--------|---------|
| REST API | JWT (simplejwt) | Access + refresh tokens |
| MCP (stdio) | Environment variable | `VOLT_OWNER_API_KEY=volt_owner_xxx` |
| MCP (HTTP) | Bearer token | `Authorization: Bearer volt_owner_xxx` |
| Gateway (subscriber) | API key header | `X-Volt-API-Key: volt_sub_xxx` |
| Gateway (public approval) | OTP | 6-digit, SMS, SHA-256 hashed, 3 attempts max |

### 10.2 Key management

- Owner API keys: `volt_owner_` prefix, SHA-256 hash stored, raw shown once at creation
- Subscriber API keys: separate namespace, same hash scheme
- Encryption keys: derived from `SECRET_KEY` + owner_id via PBKDF2 (100k iterations)
- No key rotation mechanism yet (identified gap)

### 10.3 Threat model

| Threat | Mitigation | Gap |
|--------|-----------|-----|
| Unauthorized DB access | Fernet encryption at rest | Key derivation from SECRET_KEY = single point of failure |
| Data exfiltration via API | JWT auth + owner scoping | No rate limiting on MCP tools |
| Package tampering (gateway) | HMAC-SHA256 signature | No end-to-end encryption of checkout packages |
| Insider threat | Append-only audit log | No alerting on anomalous access patterns |
| Key compromise | — | No key rotation, no HSM, no envelope encryption |

---

## Appendix A: REST API Endpoints

```
/vault/me/                                    GET    — Owner vault info
/entities/                                    CRUD   — Entity management
/entities/{id}/relationships/                 GET/POST — Entity relationships
/entities/query/                              POST   — Hybrid graph + vector query
/entities/schemas/                            GET    — DATA_SCHEMAS
/documents/                                   CRUD   — Document management
/documents/{id}/versions/                     GET/POST — Version list / upload
/documents/{id}/versions/{vid}/download/      GET    — Decrypt + stream
/relationship-types/                          CRUD   — Relationship catalogue
/schemas/                                     CRUD   — Entity schemas
/schemas/active/                              GET    — Active schemas
/schemas/seed-defaults/                       POST   — Seed ZA defaults
/gateway/request/                             POST   — Subscriber requests access
/gateway/checkout/                            POST   — Retrieve approved data
/gateway/requests/                            GET    — Owner lists requests
/gateway/requests/{token}/approve/            POST   — Owner approves
/gateway/requests/{token}/deny/               POST   — Owner denies
/gateway/requests/{token}/status/             GET    — Poll status
/gateway/requests/{token}/approval-info/      GET    — Public view
/gateway/requests/{token}/approve-public/     POST   — OTP + decision
```

## Appendix B: Migration History

| # | Migration | What it does |
|---|-----------|-------------|
| 1 | `0001_initial` | Core schema: all models |
| 2 | `0002_*` | DocumentVersion.extracted_data + DocumentVerification |
| 3 | `0003_*` | DocumentTypeCatalogue model |
| 4 | `0004_*` | MCP server scaffolding + enhanced gateway |
| 5 | `0005_*` | Seed ~85 SA document types |
| 6a | `0006_relationship_type_catalogue` | RelationshipTypeCatalogue model |
| 6b | `0006_seed_asset_documents` | Asset document types |
| 7 | `0007_seed_relationship_types` | System relationship types |
| 8 | `0008_merge_*` | Merge migration |
| 9 | `0009_seed_company_trust_cc_soleprop` | Entity-specific doc types |
