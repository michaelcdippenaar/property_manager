# Owner Document Pipeline — Phases 1–9

---

## Phase 1 — Entity Declaration

Ask:
> **"What type of entity is this owner?"**
> 1. Individual
> 2. Company (Pty Ltd / NPC / SOC Ltd / Public Ltd)
> 3. Trust
> 4. Close Corporation (CC)
> 5. Partnership

If **Company** → "Is this company owned (wholly or partly) by a Trust?"
- Yes → output includes `trust_entity` block; collect trust docs too (trace to natural persons)

If **Trust** → "Does this trust own any registered companies?"
- Yes → collect CIPC documents for those companies as well

---

## Phase 2 — Document Ingestion

Ask the user for the folder path (e.g. `uploads/owners/acme_pty_ltd/`).

Use `Glob` to list all files. Then read each file:
- PDFs and text files: `Read`
- Images (JPG, PNG, scans): `Read` — view directly

Process files one at a time. Do not skip any file.

---

## Phase 3 — Document Classification

For each file, determine:
1. **Bucket**: FICA or CIPC/CIPRO
2. **Document type**: specific form code or document name
3. **Relevance**: `required` / `optional` / `unknown` for the declared entity type

Classification signals:

| Signal in document | Bucket | Type |
|---|---|---|
| "CoR14.3", "Registration Certificate" | CIPC | Registration Certificate |
| "CoR14.1", "Application for Registration" | CIPC | Application for Registration |
| "CoR15.1", "Memorandum of Incorporation", "MOI" | CIPC | MOI |
| "CoR39", "Director", "Notice of directors" | CIPC | Director Notice |
| "CoR21", "Registered Office" | CIPC | Office Change Notice |
| "CoR123", "Annual Return" | CIPC | Annual Return |
| "CoR40", "Winding-up", "Liquidation" | CIPC | Winding-up Notice |
| "CK1", "Founding Statement" | CIPC | CC Founding Statement |
| "CK2", "Amended Founding Statement" | CIPC | CC Amendment |
| "Master of the High Court", "Letters of Authority", "URN" | CIPC | Trust Letter of Authority |
| "Trust Deed", "Deed of Trust" | CIPC | Trust Deed |
| "Partnership Agreement", "Joint Venture Agreement" | CIPC | Partnership Agreement |
| "Identity Document", "Smart ID", green ID book, "Passport" | FICA | ID / Passport |
| Bank letterhead, "Bank Confirmation", "Account Confirmation" | FICA | Bank Confirmation Letter |
| "Proof of Residence", "Proof of Address", utility bill, municipal account | FICA | Proof of Address |
| "SARS", "Income Tax", "Tax Clearance", "Tax Number" | FICA | Tax Certificate |
| "VAT Registration", "VAT Number" | FICA | VAT Certificate |

---

## Phase 4 — Field Extraction

Extract structured data from each document. Use only information explicitly present — do not infer or guess.

Read `references/cipc-document-taxonomy.md` for complete fields per document type.

Key extraction rules:
- **Registration numbers**: SA format `YYYY/XXXXXX/07` (07 = Pty Ltd, 08 = CC, 21 = NPC)
- **ID numbers**: SA ID is 13 digits. Validate format; do not compute checksum.
- **Dates**: normalise to `YYYY-MM-DD`
- **Bank account numbers**: capture last 4 digits only — never log the full number
- **Addresses**: capture as written; do not reformat

---

## Phase 5 — Completeness Validation

Read `references/fica-requirements.md` for the full requirements table per entity type.

**Red flags to surface:**
- Company CIPC status: Deregistered
- Proof of address older than 3 months from today
- Letter of Authority trustees do not match the ID copies provided
- Director named on CoR39 has no corresponding ID document
- Trust deed present but no Letter of Authority
- Company registered > 1 year ago but no annual return (CoR123) found
- Company owned by trust but no trust documents present

---

## Phase 6 — Output JSON

Write `owner_classification.json` to the same folder as the input documents.

See `references/output-schema.md` for the full JSON structure.

---

## Phase 7 — Cross-Entity Person Joints

After all entities are processed, build a deduplicated registry of every natural person across all roles. Match by **ID number** as primary key.

**Why it matters:**
1. **FICA efficiency** — one certified ID is sufficient across all roles for the same person
2. **Beneficial ownership graph** — FICA and POPIA require disclosure of control concentration

### Building joints

For every entity block, collect all named natural persons and their roles. Group all appearances of the same ID number.

A **joint** exists when the same person appears in more than one role or entity:
- Director of the company AND trustee of the owning trust
- Trustee AND beneficiary of the same trust
- Member of a CC AND director of a related company
- Two entries with different ID numbers but identical names → flag for manual review

### System lookup

After building the persons_graph, call the backend for each unique ID number and entity registration number:

```
GET http://localhost:8000/api/v1/accounts/lookup/?id_number=<13-digit-id>
GET http://localhost:8000/api/v1/accounts/lookup/?registration_number=<YYYY/XXXXXX/07>
```

Use `Authorization: Bearer <token>` from the current session.

### Red flags from joints analysis

- Same person holds 25%+ across two or more entities → **ownership concentration**
- Person is trustee of trust AND director of trust-owned company → **dual control** (must be disclosed)
- Two entries with different ID numbers but identical names → **possible duplicate — verify**
- Person named in CIPC doc but no ID document provided → flag per entity AND in persons_graph

### FICA reuse rule

If a valid certified ID is already in the folder for a person, note it in `fica_reuse_note` for every other role they hold. Only one certified copy needed regardless of role count.

---

## Phase 8 — RAG Ingestion *(server-side)*

After Phase 6 writes the JSON, a post-classify Django signal enqueues a Celery task that:

1. Extracts text from each `LandlordDocument` file (`backend/apps/properties/extraction_utils.py → extract_pdf_text`)
2. Chunks each page (500-token sliding window within long pages; one chunk per page for short structured docs)
3. Embeds with `nomic-embed-text-v1.5` (matches `backend/core/contract_rag.py` convention)
4. Upserts into the ChromaDB `owner_documents` collection with full metadata

**The skill's job here is to make Phase 6's output Phase-8-friendly.** That means:
- Every document in `fica.documents[]` and `cipc.documents[]` must carry a stable `filename` that matches `LandlordDocument.file.name`, so the ingestion task can reconcile
- Extracted `person_ids` should be present on each document so the embedder can tag chunks for later cross-entity search

See [rag-ingestion.md](rag-ingestion.md) for the chunking strategy, metadata schema, and collection spec.

---

## Phase 9 — Gap Analysis *(server-side, scenario-aware)*

Once the JSON is written and RAG is populated, the backend computes scenario-specific readiness:

```python
compute_gap_analysis(landlord, scenario="rental_mandate") -> MandateReadiness
```

For `scenario="rental_mandate"`:
- Load [mandate-requirements.md](mandate-requirements.md) to know what's required per entity type
- Walk `classification_data` → identify missing required docs, missing fields, blocking issues, warnings
- Populate the `mandate_readiness` block on the output JSON

Blocking issues (not warnings) prevent the mandate signature request from being sent. The UI must surface these before offering an "Invite to sign" CTA.

**Why this phase is separate from Phase 5 (completeness validation):** Phase 5 checks FICA/CIPC *compliance* (is the FICA pack legally complete?). Phase 9 checks *fit-for-purpose* against a specific downstream action (can this owner sign *this mandate* right now?). A FICA-complete owner can still be mandate-blocked — e.g., directors exist but no board resolution, or trustees are listed but Letters of Authority are stale.

---

## Summary Report

After writing JSON, print a human-readable summary:

```
## Owner Classification Summary

Entity:     Acme Property (Pty) Ltd (Pty Ltd)
Owned by Trust: No

FICA Status:   INCOMPLETE
  ✓ Found:    SA ID (John Smith)
  ✓ Found:    Proof of Address
  ✗ Missing:  Bank Confirmation Letter
  ⚠ Flag:    Proof of address may be older than 3 months

CIPC Status:   NEEDS REVIEW
  ✓ Found:    CoR14.3 — Registration Certificate (Active)
  ✓ Found:    CoR39 — Director Notice (John Smith)
  ✗ Missing:  CoR15.1A / CoR15.1B (MOI)
  ⚠ Flag:    No annual return found — company registered in 2018

owner_classification.json written to: uploads/owners/acme_pty_ltd/

─────────────────────────────────────
PERSONS GRAPH (Cross-Entity Joints)
─────────────────────────────────────
  John Smith (7601015009087)
    → Director — Acme Property (Pty) Ltd
    ID: ✓ found  |  Joint: No

  Jane Smith (7812020012089)
    → Trustee — Smith Family Trust
    ID: ✗ missing  |  Joint: No
```
