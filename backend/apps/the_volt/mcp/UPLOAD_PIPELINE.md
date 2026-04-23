# Vault Upload Pipeline

Bulk-import documents into The Volt from local filesystem folders. The pipeline
has three stages: **manifest** -> **enrich** -> **upload**.

## Overview

```
Source folders (PDFs, DOCX, XLSX)
       |
       v
  1. MANIFEST — scan folders, classify each file
       |
       v
  manifests/<entity>_manifest.jsonl   (raw, no extracted_data)
       |
       v
  2. ENRICH — OCR/read each PDF, extract structured fields
       |
       v
  manifests/enriched/<batch>.jsonl    (with extracted_data)
       |
       v
  3. UPLOAD — create entities, attach documents, build relationships
       |
       v
  The Volt (PostgreSQL + encrypted files + ChromaDB vectors)
```

---

## Stage 1: Manifest

A manifest is a JSONL file where each line describes one source document:

```json
{
  "source_path": "/absolute/path/to/document.pdf",
  "entity_name": "2 Otterkuil Street",
  "entity_type": "asset",
  "document_type_code": "otp",
  "confidence": "high",
  "label": "2 Otterkuil OTP (Klikk Purchase)",
  "mime_type": "application/pdf"
}
```

### Fields

| Field | Required | Description |
|---|---|---|
| `source_path` | Yes | Absolute path to the source file on disk |
| `entity_name` | Yes | Display name of the primary entity this doc belongs to |
| `entity_type` | Yes | One of: `personal`, `company`, `trust`, `close_corporation`, `sole_proprietary`, `asset` |
| `document_type_code` | Yes | Document classification code (see `DocumentTypeCatalogue`) |
| `confidence` | No | `high`, `medium`, or `low` — affects processing order |
| `label` | No | Human-readable label for the document |
| `mime_type` | No | MIME type (auto-detected if omitted) |

### Creating manifests

Manifests can be created manually or by scanning a folder structure. The
convention is to name them `<entity>_manifest.jsonl` in the `manifests/`
directory.

---

## Stage 2: Enrich

Enrichment reads each source file (PDF, DOCX) and extracts structured data
fields into an `extracted_data` dict. This is the OCR/parsing step.

### Enriched entry format

```json
{
  "source_path": "/path/to/Final OTP 2 Otterkuil.pdf",
  "entity_name": "2 Otterkuil Street",
  "entity_type": "asset",
  "document_type_code": "otp",
  "confidence": "high",
  "label": "2 Otterkuil OTP (Klikk Purchase from Otto Business Trust)",
  "extracted_data": {
    "registration_number": "ERF 3581",
    "property_address": "2 Otterkuil Street, Karindal, Stellenbosch, 7600",
    "seller": "Otto Business Trust",
    "seller_reg": "160/2008",
    "buyer": "Klikk (Pty) Ltd",
    "purchase_price": 8500000,
    "offer_date": "2022-09-09"
  }
}
```

### Critical rules for enrichment

1. **ERF numbers are mandatory for property documents.** A property is uniquely
   identified by its location + ERF number on the title deed. Extract as
   `registration_number` (e.g. `"ERF 3581"`).

2. **Identity keys prevent duplicates.** Each entity type has an identity key:
   - `personal` -> `id_number` (SA ID)
   - `company` / `close_corporation` -> `reg_number` (CIPC)
   - `trust` -> `trust_number` (IT number from Master)
   - `asset` -> `registration_number` (ERF number)

3. **Counterparty data belongs in extracted_data.** Sellers, tenants, agents,
   managing agents are extracted as fields — the upload pipeline creates them
   as separate entities automatically.

### Enrichment conventions

| Document type | Key fields to extract |
|---|---|
| `otp` | `seller`, `seller_reg`, `buyer`, `purchase_price`, `registration_number`, `agent`, `agent_company` |
| `transfer_statement` | `transfer_from`, `transfer_to`, `purchase_price`, `registration_date`, `attorneys` |
| `rental_agreement` | `tenant_names[]`, `tenant_entity`, `tenant_reg`, `monthly_rent_zar`, `lease_start`, `lease_end`, `managing_agent` |
| `title_deed` | `registration_number`, `transfer_from`, `transfer_to`, `registration_date` |
| `cipc_cor14_3` | `reg_number`, `company_name`, `directors[]` |
| `trust_deed` | `trust_number`, `trust_name`, `trustees[]`, `beneficiaries[]` |
| `sa_id_document` | `id_number`, `full_name`, `date_of_birth` |
| `marriage_certificate` | `spouse_names[]`, `date_of_marriage`, `regime` |
| `bond_statement` | `bank_name`, `account_number`, `facility_amount` |
| `building_plan` | `registration_number`, `architect`, `date`, `description` |

### Running enrichment

Enrichment is typically done by Claude agents reading each PDF and writing
the enriched JSONL. Batch files are placed in `manifests/enriched/`.

Naming convention: `<owner>_batch<N>_<category>.jsonl`

Example batches:
```
manifests/enriched/
  klikk_batch1_cipc_legal.jsonl       # 28 entries
  klikk_batch2_property_lacolline.jsonl  # 30 entries
  klikk_batch3a_karindal_property.jsonl  # 15 entries
  klikk_batch3b_leases_theone.jsonl     # 16 entries
  klikk_batch4_finance.jsonl            # 65 entries
```

---

## Stage 3: Upload

`upload_from_manifest.py` reads enriched JSONL and creates everything in
The Volt via Django ORM (no HTTP, no MCP transport).

### Usage

```bash
cd backend

# Single manifest
PYTHONPATH=. .venv/bin/python apps/the_volt/mcp/upload_from_manifest.py \
  --manifest apps/the_volt/mcp/manifests/enriched/klikk_batch1_cipc_legal.jsonl \
  --vault-owner-email mc.dippenaar.pr@gmail.com

# All manifests in directory
PYTHONPATH=. .venv/bin/python apps/the_volt/mcp/upload_from_manifest.py \
  --manifest-dir apps/the_volt/mcp/manifests/enriched/ \
  --vault-owner-email mc.dippenaar.pr@gmail.com

# Dry run (validate without writing)
PYTHONPATH=. .venv/bin/python apps/the_volt/mcp/upload_from_manifest.py \
  --manifest-dir apps/the_volt/mcp/manifests/enriched/ \
  --vault-owner-email mc.dippenaar.pr@gmail.com \
  --dry-run

# Skip unclassified documents
PYTHONPATH=. .venv/bin/python apps/the_volt/mcp/upload_from_manifest.py \
  --manifest apps/the_volt/mcp/manifests/enriched/batch.jsonl \
  --vault-owner-email mc.dippenaar.pr@gmail.com \
  --skip-other
```

### What the upload does

For each JSONL entry, in order:

1. **Upsert primary entity** — finds or creates the entity by identity key,
   then falls back to name matching. Merges `data` fields on match.

2. **Encrypt + attach document** — reads source file bytes, encrypts with
   Fernet (per-owner key), stores as `DocumentVersion`. Computes SHA-256 hash.
   Ingests text into ChromaDB for vector search.

3. **Build relationships** (legal documents only) — `trust_deed`, `cipc_cor14_3`,
   `share_certificate`, `marriage_certificate`, etc. create person -> entity
   edges (trustee_of, director_of, shareholder_of, married_to, etc.).

4. **Build counterparty entities** (transaction documents) — `otp`,
   `transfer_statement`, `rental_agreement`, `title_deed` create seller, buyer,
   tenant, managing agent entities and relationship edges:
   - Sellers -> `sold_to` -> asset
   - Tenants -> `tenant_of` -> asset
   - Managing agents -> asset `managed_by` -> agent
   - Estate agents -> asset `brokered_by` -> agency

5. **Audit trail** — every write creates a `VaultWriteAudit` row (POPIA §17).

### Processing order

Identity-establishing documents (SA IDs, CIPC registrations, trust deeds) are
processed first regardless of their position in the file. This ensures
identity keys exist before relationship-building documents reference them.

Within the same priority level, `high` confidence entries are processed before
`medium` and `low`.

### Entity type inference for counterparties

The pipeline infers entity types from names:
- Contains "Trust" / "Familietrust" -> `trust`
- Ends with " CC" / " BK" -> `close_corporation`
- Contains "(Pty)" / "Bpk" / "Ltd" / "Proprietary" -> `company`
- Registration hint starts with "IT" -> `trust`
- Everything else -> `personal`

### Relationship types

| Code | Label | Created by |
|---|---|---|
| `director_of` | Director of | CIPC registrations, MOIs |
| `trustee_of` | Trustee of | Trust deeds, letters of authority |
| `shareholder_of` | Shareholder of | Share certificates |
| `beneficial_owner_of` | Beneficial Owner of | Trust deeds |
| `member_of` | Member of | CC founding statements |
| `married_to` | Married to | Marriage certs, ANCs |
| `divorced_from` | Divorced from | Divorce orders |
| `holds_asset` | Holds Asset | Title deeds (registered_owner) |
| `sold_to` | Sold to | OTPs, transfer statements |
| `purchased_from` | Purchased from | OTPs (buyer side) |
| `tenant_of` | Tenant of | Rental agreements |
| `managed_by` | Managed by | Rental agreements (managing agent) |
| `brokered_by` | Brokered by | OTPs (estate agent) |
| `leases_from` | Leases from | Lease setup |
| `operates_as` | Operates as | Business structure |
| `guarantor_for` | Guarantor for | Guarantee documents |
| `parent_of` | Parent of | Family documents |
| `conveyanced_by` | Conveyanced by | Transfer documents |

### Legal document guard

**Only legal instruments create entity relationships.** Bank statements, ID
copies, proof-of-address documents may mention directors or trustees in their
extracted data, but those mentions are informational — not authoritative.

Legal document types: `trust_deed`, `letters_of_authority`, `cipc_cor14_3`,
`moi`, `share_certificate`, `marriage_certificate`, `antenuptial_contract`,
`title_deed`, `power_of_attorney`, and others.

Transaction document types (for counterparty creation): `otp`,
`transfer_statement`, `rental_agreement`, `title_deed`, `bond_facility_letter`.

---

## Deduplication

The upload pipeline prevents duplicates via identity-key matching:

1. If `fields` contains an identity key (e.g. `id_number` for personal),
   search existing entities by that key first.
2. Fall back to `(entity_type, name)` matching.
3. On match, **merge** data — existing keys are preserved unless overwritten.
   Name is updated to the latest (longer/more formal) version.

Name matching is fuzzy for South African names:
- "MC Dippenaar" matches "Michaelis Christoffel Dippenaar" (initials)
- "Michael Dippenaar Snr" matches "Michaelis Dippenaar" (suffix stripped)
- Parenthetical suffixes are cleaned: "Name (ID 1234)" -> "Name"

---

## Verification

After upload, verify via Django shell:

```bash
cd backend
PYTHONPATH=. DJANGO_SETTINGS_MODULE=config.settings.local .venv/bin/python -c "
import django; django.setup()
from apps.the_volt.entities.models import VaultEntity, EntityRelationship
from apps.the_volt.documents.models import VaultDocument, DocumentVersion

v = 2  # vault_id
print('Entities:', VaultEntity.objects.filter(vault_id=v).count())
print('Documents:', VaultDocument.objects.filter(entity__vault_id=v).count())
print('Versions:', DocumentVersion.objects.filter(document__entity__vault_id=v).count())
print('Relationships:', EntityRelationship.objects.filter(vault_id=v).count())
"
```

Or via the MCP tools: `list_entities`, `get_entity`, `list_documents`.
