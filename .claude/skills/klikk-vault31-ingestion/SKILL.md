---
name: klikk-vault31-ingestion
description: >
  The Volt document ingestion pipeline: scan source folders, classify documents,
  enrich with OCR-extracted structured data, and bulk-upload into the Vault with
  entity creation, relationship building, and counterparty extraction.
  Use this skill whenever the user wants to ingest documents into The Volt/Vault,
  upload PDFs or folders to the vault, create JSONL manifests from document folders,
  enrich manifests with extracted data, run the upload pipeline, or process any
  batch of owner/property/legal/financial documents for vault storage. Also use
  when the user mentions "manifest", "enrichment", "vault upload", "bulk import",
  "document ingestion", "JSONL batch", or asks to process a folder of documents
  for a vault owner. Triggers on any mention of ingesting, uploading, or
  importing documents into The Volt, even if the user just drops a folder path.
---

# Vault Document Ingestion Pipeline

Three-stage pipeline for getting documents from filesystem folders into The Volt:
**Manifest** (classify) -> **Enrich** (extract) -> **Upload** (persist + graph).

The Volt is a POPIA-compliant data sovereignty vault. Every document is encrypted
at rest (Fernet, per-owner key), hashed (SHA-256), indexed in ChromaDB for vector
search, and audited in `VaultWriteAudit`.

---

## When to use this skill

- User drops a folder path and wants it ingested into the vault
- User has existing JSONL manifests that need enrichment or upload
- User wants to process a batch of PDFs (property docs, legal docs, financial docs)
- User asks about the manifest format or enrichment conventions
- User wants to understand how documents flow into The Volt

---

## Quick Start

If you already have enriched JSONL manifests, skip to [Stage 3: Upload](#stage-3-upload).

If you have raw folders of documents, start at [Stage 1: Manifest](#stage-1-manifest).

---

## Stage 1: Manifest — Classify Source Documents

Scan a folder tree and produce a JSONL manifest where each line classifies one file.

### Manifest entry format

```json
{
  "source_path": "/absolute/path/to/document.pdf",
  "entity_name": "2 Otterkuil Street",
  "entity_type": "asset",
  "document_type_code": "otp",
  "confidence": "high",
  "label": "2 Otterkuil OTP (Klikk Purchase from Otto Business Trust)",
  "mime_type": "application/pdf"
}
```

### Fields

| Field | Required | Description |
|---|---|---|
| `source_path` | Yes | Absolute path to source file on disk |
| `entity_name` | Yes | Display name of the primary entity this doc belongs to |
| `entity_type` | Yes | `personal`, `company`, `trust`, `close_corporation`, `sole_proprietary`, `asset` |
| `document_type_code` | Yes | Classification code from `DocumentTypeCatalogue` |
| `confidence` | No | `high`, `medium`, `low` — affects processing order |
| `label` | No | Human-readable label (descriptive, unique within entity) |
| `mime_type` | No | Auto-detected if omitted |

### How to classify

1. **Use folder structure as context.** Parent folder names usually indicate the entity
   (e.g., `Karindal/2 Otterkuil/Certificates/` -> entity = "2 Otterkuil Street", type = asset).

2. **Use filenames.** SA document names follow conventions:
   - "COC" / "Compliance Certificate" -> `electrical_coc`, `gas_coc`, `beetle_certificate`
   - "OTP" / "Koopkontrak" -> `otp`
   - "Lease" / "Huurkontrak" -> `rental_agreement`
   - "CoR14" -> `cipc_cor14_3`
   - "Trust Deed" / "Trustakte" -> `trust_deed`

3. **Read first page if unsure.** Use `Read` tool with `pages: "1"` for PDFs.

4. **Set confidence:**
   - `high` — filename + folder make classification obvious
   - `medium` — had to read content to classify
   - `low` — uncertain, possible misfiling (add a `note` in extracted_data)

### Entity type decision tree

| Indicator | Entity type |
|---|---|
| Property address, ERF number, unit | `asset` |
| SA ID number, person name | `personal` |
| CIPC reg number, "(Pty) Ltd", "Bpk" | `company` |
| "CC", "BK", CK1/CK2 | `close_corporation` |
| Trust deed, IT number, "Trust" | `trust` |
| Trade name, sole owner | `sole_proprietary` |

### Document type reference

Load `references/document-types.md` for the complete catalogue of 90+ document
type codes. The most common ones:

| Code | When to use |
|---|---|
| `otp` | Offer to Purchase / Koopkontrak |
| `rental_agreement` | Lease / Huurkontrak (any version) |
| `title_deed` | Title deed, registration letter |
| `transfer_statement` | Transfer recon / final statement of account |
| `electrical_coc` | Electrical Certificate of Compliance |
| `gas_coc` | Gas installation certificate |
| `beetle_certificate` | Beetle/pest clearance |
| `building_plans` | Approved building plans |
| `bond_statement` | Bond facility letter, advice of grant |
| `cipc_cor14_3` | CIPC registration certificate |
| `trust_deed` | Trust instrument |
| `letters_of_authority` | Master's certificate / Letters of Authority |
| `sa_id_document` | SA ID / Smart ID card |
| `marriage_certificate` | Marriage certificate |
| `financial_statements` | Annual financial statements |
| `property_insurance` | Property insurance policy |
| `share_certificate` | Share certificate |

### Batching strategy

For large folder sets (50+ documents), split into batches by category:

```
manifests/enriched/
  <owner>_batch1_cipc_legal.jsonl        # CIPC, trust, legal docs
  <owner>_batch2_property_<area>.jsonl   # Property docs by area
  <owner>_batch3_leases.jsonl            # All rental agreements
  <owner>_batch4_finance.jsonl           # Financial, banking, insurance
```

Keep each batch under 20MB of source PDFs if using agents for enrichment
(large PDFs can exceed agent context windows).

### Output location

Save manifests to:
```
backend/apps/the_volt/mcp/manifests/<owner>_manifest.jsonl         # raw
backend/apps/the_volt/mcp/manifests/enriched/<batch>.jsonl         # enriched
```

---

## Stage 2: Enrich — Extract Structured Data

Read each source document and extract structured fields into `extracted_data`.
This is the OCR/parsing step that transforms a classification-only manifest
into a data-rich manifest ready for upload.

### Enriched entry format

The enriched entry keeps all manifest fields and adds `extracted_data`:

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
    "erf_size_m2": 766,
    "title_deed": "T52028/2019",
    "seller": "Otto Business Trust",
    "seller_reg": "160/2008",
    "seller_contact": "sdotto@sdotto.co.za",
    "buyer": "Klikk (Pty) Ltd",
    "buyer_reg": "2016/113758/07",
    "purchase_price": 8500000,
    "deposit": 860000,
    "agent": "Lizanne Fourie",
    "agent_company": "Pam Golding Properties",
    "offer_date": "2022-09-09",
    "conveyancers": "Strauss Daly, Bellville",
    "municipality": "Stellenbosch",
    "province": "Western Cape"
  }
}
```

### Critical enrichment rules

These rules are non-negotiable — they prevent data loss and duplicates:

1. **ERF numbers are mandatory for property documents.** A property is uniquely
   identified by location + ERF number from the title deed. Always extract as
   `registration_number` (e.g., `"ERF 3581"`). Without this, properties cannot
   be deduplicated. Check title deeds, OTPs, transfer statements, building plans.

2. **Identity keys must be extracted when present.** Each entity type has ONE
   identity key that the upload pipeline uses for deduplication:

   | Entity type | Identity key | Example |
   |---|---|---|
   | `personal` | `id_number` | `"8205315092087"` |
   | `company` | `reg_number` | `"2016/113758/07"` |
   | `trust` | `trust_number` | `"IT1102/96"` |
   | `close_corporation` | `reg_number` | `"2010/032506/23"` |
   | `asset` | `registration_number` | `"ERF 3581"` |

3. **Extract counterparty data.** Sellers, buyers, tenants, agents, managing
   agents are extracted as fields in `extracted_data`. The upload pipeline
   creates them as separate entities automatically — you don't need separate
   manifest entries for counterparties.

4. **Dates as ISO strings.** Use `"2022-09-09"` format, not `"9 September 2022"`.

5. **Money as integers (ZAR cents not needed).** `"purchase_price": 8500000` not
   `"purchase_price": "R8,500,000.00"`.

6. **Lists for multi-person fields.** `"tenant_names": ["Cornelis Schriek"]` not
   `"tenant_name": "Cornelis Schriek"`.

### Extraction conventions by document type

Load `references/extraction-fields.md` for the complete field reference.

**Property transactions:**

| Document type | Key fields |
|---|---|
| `otp` | `registration_number`, `property_address`, `seller`, `seller_reg`, `buyer`, `buyer_reg`, `purchase_price`, `deposit`, `agent`, `agent_company`, `offer_date`, `conveyancers` |
| `transfer_statement` | `registration_number`, `transfer_from`, `transfer_to`, `purchase_price`, `registration_date`, `attorneys`, `attorney_ref` |
| `title_deed` | `registration_number`, `transfer_from`, `transfer_to`, `registration_date` |
| `rental_agreement` | `registration_number`, `tenant_names[]`, `tenant_entity`, `tenant_reg`, `tenant_id`, `monthly_rent_zar`, `deposit_zar`, `lease_start`, `lease_end`, `managing_agent`, `landlord` |

**Certificates of compliance:**

| Document type | Key fields |
|---|---|
| `electrical_coc` | `registration_number`, `property_address`, `certificate_number`, `inspector_name`, `inspection_date` |
| `gas_coc` | `registration_number`, `property_address`, `certificate_number`, `practitioner_name`, `inspection_date`, `owner_at_time` |
| `beetle_certificate` | `registration_number`, `property_address`, `inspection_company`, `inspection_date`, `result` |

**Legal/identity:**

| Document type | Key fields |
|---|---|
| `cipc_cor14_3` | `reg_number`, `company_name`, `directors[]`, `registration_date` |
| `trust_deed` | `trust_number`, `trust_name`, `trustees[]`, `beneficiaries[]`, `deed_date` |
| `sa_id_document` | `id_number`, `full_name`, `date_of_birth`, `nationality` |
| `marriage_certificate` | `spouse_names[]`, `date_of_marriage`, `regime` |
| `share_certificate` | `reg_number`, `shareholder_name`, `shares`, `share_class` |

**Financial:**

| Document type | Key fields |
|---|---|
| `bond_statement` | `bank_name`, `account_number`, `facility_amount`, `registration_number` |
| `financial_statements` | `entity_name`, `financial_year_end`, `net_income`, `auditor` |
| `property_insurance` | `registration_number`, `insurer`, `policy_number`, `sum_insured` |

### Handling large PDFs

PDFs over 10 pages must be read with the `pages` parameter:
```
Read(file_path="/path/to/large.pdf", pages="1-5")
```

Read pages 1-3 first (usually contains the key data), then read further only
if needed. OTPs typically have key terms on pages 1-5. Rental agreements have
tenant details on page 1, terms on pages 2-8, signatures on the last page.

### Handling non-readable formats

Mark `.xlsx`, `.docx`, `.doc` files that can't be read by the Read tool:
```json
{
  "source_path": "/path/to/spreadsheet.xlsx",
  "entity_name": "Klikk (Pty) Ltd",
  "entity_type": "company",
  "document_type_code": "financial_statements",
  "confidence": "low",
  "label": "Deposit Recon 2025 (Excel - needs manual review)",
  "extracted_data": {
    "note": "XLSX file - could not be read for extraction. Needs manual review."
  }
}
```

### Handling Afrikaans documents

Many SA legal documents are in Afrikaans. Common translations:

| Afrikaans | English | Document type |
|---|---|---|
| Koopkontrak / Finale Koopkontrak | Purchase Agreement / OTP | `otp` |
| Huurkontrak | Rental Agreement | `rental_agreement` |
| Trustakte | Trust Deed | `trust_deed` |
| Aanhangsel | Addendum | same as parent type |
| Beperk / Bpk | Limited / (Pty) Ltd | company indicator |
| Eiendom / Eiendomme | Property / Properties | asset indicator |
| Huweliksertifikaat | Marriage Certificate | `marriage_certificate` |
| Direkteursresolusie | Directors' Resolution | `directors_resolution` |

### Parallel enrichment with agents

For large batches (50+ documents), spawn parallel agents:

```
Agent 1: CIPC + legal docs (trust deeds, share certs, resolutions)
Agent 2: Property docs by area (OTPs, COCs, transfers)
Agent 3: Leases (rental agreements, extensions)
Agent 4: Finance (bank statements, bonds, insurance, investments)
```

Each agent reads the source PDFs using the Read tool, extracts structured
fields, and writes an enriched JSONL batch file. Keep each agent's batch
under 20MB of source PDFs.

### Misfiled documents

If a document is clearly in the wrong folder (e.g., a Klapmuts building plan
in a Karindal property folder), still include it but:
- Set `confidence: "low"`
- Add a `note` in `extracted_data` explaining the misfiling
- Set `entity_name` to the CORRECT entity from the document content

### Coverage audit

After enrichment, verify all source documents are covered:

```python
python3 -c "
import json, glob

enriched_paths = set()
for f in glob.glob('manifests/enriched/*.jsonl'):
    with open(f) as fh:
        for line in fh:
            if line.strip():
                enriched_paths.add(json.loads(line)['source_path'])

original_paths = set()
with open('manifests/original_manifest.jsonl') as fh:
    for line in fh:
        if line.strip():
            original_paths.add(json.loads(line)['source_path'])

missing = original_paths - enriched_paths
print(f'Original: {len(original_paths)}, Enriched: {len(enriched_paths)}')
if missing:
    print(f'MISSING ({len(missing)}):')
    for p in sorted(missing):
        print(f'  {p}')
else:
    print('All covered')
"
```

---

## Stage 3: Upload — Persist to The Vault

`upload_from_manifest.py` reads enriched JSONL and creates everything in
The Vault via Django ORM — no HTTP, no MCP transport, no API keys needed.

### Commands

```bash
cd backend

# Single manifest
PYTHONPATH=. .venv/bin/python apps/the_volt/mcp/upload_from_manifest.py \
  --manifest apps/the_volt/mcp/manifests/enriched/batch.jsonl \
  --vault-owner-email user@example.com

# All manifests in a directory
PYTHONPATH=. .venv/bin/python apps/the_volt/mcp/upload_from_manifest.py \
  --manifest-dir apps/the_volt/mcp/manifests/enriched/ \
  --vault-owner-email user@example.com

# Dry run first (always recommended)
PYTHONPATH=. .venv/bin/python apps/the_volt/mcp/upload_from_manifest.py \
  --manifest apps/the_volt/mcp/manifests/enriched/batch.jsonl \
  --vault-owner-email user@example.com \
  --dry-run

# Skip unclassified 'other' documents
  --skip-other

# Verbose logging
  --verbose
```

**Always dry-run first** to catch errors before writing to the database.

### What the upload does (per entry)

1. **Upsert primary entity** — finds or creates by identity key, falls back
   to name matching. Merges `data` dict on match (existing keys preserved
   unless overwritten). Name updated to latest (longer/more formal) version.

2. **Encrypt + attach document** — reads source bytes, encrypts with Fernet
   (per-owner key), stores as `DocumentVersion`. Computes SHA-256. Ingests
   text into ChromaDB for vector search.

3. **Build relationships** (legal documents only) — trust deeds, CIPC
   registrations, share certificates, marriage certificates create
   person -> entity edges. Non-legal docs (bank statements, IDs) are
   skipped even if they mention directors/trustees, because only the
   legal instrument is the authoritative source for a relationship.

4. **Build counterparty entities** (transaction documents) — OTPs, transfer
   statements, rental agreements create seller/buyer/tenant/agent entities
   and ownership/tenancy edges automatically:

   | extracted_data field | Entity created | Relationship |
   |---|---|---|
   | `seller` / `transfer_from` | trust/company/personal | `sold_to` -> asset |
   | `buyer` / `transfer_to` | (skipped if Klikk) | `purchased_from` -> asset |
   | `tenant_names[]` | personal | `tenant_of` -> asset |
   | `tenant_entity` | close_corporation/company | `tenant_of` -> asset |
   | `managing_agent` | company | asset `managed_by` -> agent |
   | `agent_company` | company | asset `brokered_by` -> agency |
   | `owner_at_time` | trust/company/personal | `sold_to` -> asset |

5. **Audit trail** — every write creates a `VaultWriteAudit` row (POPIA S17).

### Processing order

Identity documents are processed first regardless of file position:
1. SA IDs, passports
2. CIPC registrations (CoR14.3)
3. Trust deeds, letters of authority
4. Everything else, ordered by confidence (high -> medium -> low)

This ensures identity keys exist before relationship documents reference them.

### Entity type inference for counterparties

The pipeline infers entity types from counterparty names:

| Pattern | Inferred type |
|---|---|
| Contains "Trust" / "Familietrust" | `trust` |
| Ends with " CC" / " BK" | `close_corporation` |
| Contains "(Pty)" / "Bpk" / "Ltd" | `company` |
| Registration starts with "IT" | `trust` |
| Everything else | `personal` |

### Deduplication

The upload pipeline prevents duplicates via identity-key matching:

1. If `fields` has an identity key (e.g. `id_number`), search by that first
2. Fall back to `(entity_type, name)` matching
3. On match, merge data — existing keys preserved, name updated

Fuzzy name matching handles South African name variations:
- "MC Dippenaar" matches "Michaelis Christoffel Dippenaar" (initials)
- "Michael Dippenaar Snr" matches "Michaelis Dippenaar" (suffix stripped)
- Parenthetical suffixes cleaned: "Name (ID 1234)" -> "Name"

### Post-upload verification

```bash
cd backend
PYTHONPATH=. DJANGO_SETTINGS_MODULE=config.settings.local .venv/bin/python -c "
import django; django.setup()
from apps.the_volt.entities.models import VaultEntity, EntityRelationship
from apps.the_volt.documents.models import VaultDocument, DocumentVersion
from django.db.models import Count

v = 2  # vault_id — check VaultOwner table for correct ID
e = VaultEntity.objects.filter(vault_id=v)
print(f'Entities:      {e.count()}')
print(f'Documents:     {VaultDocument.objects.filter(entity__vault_id=v).count()}')
print(f'Versions:      {DocumentVersion.objects.filter(document__entity__vault_id=v).count()}')
print(f'Relationships: {EntityRelationship.objects.filter(vault_id=v).count()}')
print()
for row in e.values('entity_type').annotate(c=Count('id')).order_by('entity_type'):
    print(f'  {row[\"entity_type\"]:25s}  {row[\"c\"]}')
print()
# Check for duplicates
dupes = e.values('name','entity_type').annotate(c=Count('id')).filter(c__gt=1)
if dupes:
    print('DUPLICATES:')
    for d in dupes:
        print(f'  {d[\"name\"]}  ({d[\"entity_type\"]})  x{d[\"c\"]}')
"
```

Or via MCP tools: `list_entities`, `get_entity`, `list_documents`.

### Fixing duplicates

If duplicates are found after upload, merge them:

```python
# Keep the older entity (lower PK), move docs + rels from the newer one
keep = entities[0]
for dup in entities[1:]:
    # Move non-conflicting documents
    for doc in VaultDocument.objects.filter(entity=dup):
        existing = VaultDocument.objects.filter(
            entity=keep, document_type=doc.document_type, label=doc.label
        ).first()
        if existing:
            DocumentVersion.objects.filter(document=doc).delete()
            doc.delete()
        else:
            doc.entity = keep
            doc.save(update_fields=['entity'])
    # Move relationships (skip conflicts)
    # Merge data dicts
    # Delete duplicate
```

---

## Relationship Types Reference

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
| `conveyanced_by` | Conveyanced by | Transfer documents |
| `leases_from` | Leases from | Lease setup |
| `operates_as` | Operates as | Business structure |
| `guarantor_for` | Guarantor for | Guarantee documents |
| `parent_of` | Parent of | Family documents |

---

## Legal Document Guard

Only legal instruments create entity relationships (trustee_of, director_of, etc.).
This is a critical business rule — a bank statement might mention a director's name,
but it's not the authoritative source. Only the CIPC registration is.

**Legal document types** (create relationships):
`trust_deed`, `letters_of_authority`, `trust_resolution`, `cipc_cor14_3`,
`cipc_cor39`, `ck1_registration`, `cc_founding_statement`, `moi`,
`share_certificate`, `directors_resolution`, `shareholder_resolution`,
`marriage_certificate`, `antenuptial_contract`, `divorce_order`, `court_order`,
`title_deed`, `power_of_attorney`, `will`, `estate_liquidation_account`

**Transaction document types** (create counterparty entities):
`otp`, `transfer_statement`, `title_deed`, `rental_agreement`, `bond_facility_letter`

---

## Key Files

| File | Purpose |
|---|---|
| `backend/apps/the_volt/mcp/upload_from_manifest.py` | Upload pipeline script |
| `backend/apps/the_volt/mcp/manifests/` | Raw manifest storage |
| `backend/apps/the_volt/mcp/manifests/enriched/` | Enriched JSONL batches |
| `backend/apps/the_volt/mcp/UPLOAD_PIPELINE.md` | Detailed pipeline documentation |
| `backend/apps/the_volt/mcp/README.md` | MCP server documentation |
| `backend/apps/the_volt/mcp/tools/write.py` | `_upsert_entity` logic |
| `backend/apps/the_volt/entities/models.py` | `VaultEntity`, `EntityRelationship` |
| `backend/apps/the_volt/documents/models.py` | `VaultDocument`, `DocumentVersion` |
| `backend/apps/the_volt/encryption/utils.py` | Fernet encrypt/decrypt |

---

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: config` | Wrong working directory | `cd backend` before running |
| `No user found with email` | Wrong vault owner email | Check `User.objects.all()` for correct email |
| `get() returned more than one VaultEntity` | Duplicate entities exist | Run deduplication merge (see above) |
| `source_path not found` | File moved or path wrong | Check the absolute path exists |
| PDF too large to read | PDF exceeds Read tool limit | Use `pages: "1-5"` parameter |
| `UniqueViolation` on upload | Re-running upload on same data | Documents are idempotent by (entity, type, label) |
| Relationship not created | Document type not in legal guard | Check `_LEGAL_DOCUMENT_TYPES` set |
| Counterparty not created | Document type not in transaction set | Check `_TRANSACTION_DOCUMENT_TYPES` set |
| Entity type wrong for counterparty | Name doesn't match inference rules | Override in extracted_data or fix entity_type manually |
