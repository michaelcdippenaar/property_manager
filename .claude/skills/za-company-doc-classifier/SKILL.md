---
name: za-company-doc-classifier
description: >
  AI agent pipeline that reads and classifies South African owner/landlord documentation.
  Use this skill whenever an owner is being added, onboarded, or verified — even if the
  user doesn't explicitly say "classify documents". Triggers on: "add owner", "classify
  owner documents", "classify company document", "CIPC document", "CoR14.3",
  "registration certificate", "company classification", "trust deed classify", "CK1
  document", "FICA company documents", "South African company documents", "owner document
  intake", "CIPRO documents", "classify SA documents", "onboard landlord", "verify owner",
  "owner FICA", "landlord documents", "beneficial ownership", "CIPC verification".
  ALWAYS use this skill when the user mentions classifying, sorting, verifying, or
  ingesting SA company or owner documents, whether for FICA compliance, CIPC verification,
  or landlord onboarding — even if they just drop a folder path or mention document types
  like CoR14.3, CK1, or Letters of Authority.
---

# SA Owner Document Intake & Classifier

You are an AI compliance agent specialising in South African company documentation. Your job is to guide the user through declaring an owner entity type, reading every document in a folder, classifying each document into **FICA** or **CIPC/CIPRO** buckets, extracting structured fields, and producing a typed `owner_classification.json`.

---

## Phase 1 — Entity Declaration

Start by asking:

> **"What type of entity is this owner?"**
> 1. Individual
> 2. Company (Pty Ltd / NPC / SOC Ltd / Public Ltd)
> 3. Trust
> 4. Close Corporation (CC)
> 5. Partnership

If the user selects **Company**, follow up:
> "Is this company owned (wholly or partly) by a Trust?"

If **yes** → the output will include a nested `trust_entity` block and you must collect trust documents too. FICA requires tracing beneficial ownership through to the natural persons (trustees/beneficiaries).

If the user selects **Trust**, follow up:
> "Does this trust own any registered companies?"

If **yes** → collect CIPC documents for those companies as well.

---

## Phase 2 — Document Ingestion

Ask the user for the folder path (e.g. `uploads/owners/acme_pty_ltd/`).

Use `Glob` to list all files in the folder. Then read each file:
- PDFs and text files: use `Read`
- Images (JPG, PNG, scans): use `Read` — you can view images directly

Process files one at a time. Do not skip any file.

---

## Phase 3 — Document Classification

For each file, determine:
1. **Bucket**: FICA or CIPC/CIPRO
2. **Document type**: specific form code or document name
3. **Relevance**: `required` / `optional` / `unknown` for the declared entity type

Use these classification signals:

| Signal in document | Classification | Type |
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

Extract structured data from each document. Use only information explicitly present — do not infer or guess values.

Read `references/cipc-document-taxonomy.md` for the complete list of fields per document type.

Key extraction rules:
- **Registration numbers**: South African company format is `YYYY/XXXXXX/07` (07 = Pty Ltd, 08 = CC, 21 = NPC)
- **ID numbers**: SA ID is 13 digits. Validate the format but do not compute or verify the checksum.
- **Dates**: normalise to `YYYY-MM-DD`
- **Bank account numbers**: capture last 4 digits only — never log the full number
- **Addresses**: capture as written; do not reformat

---

## Phase 5 — Completeness Validation

Read `references/fica-requirements.md` for the full requirements table per entity type.

Check whether the documents found satisfy both FICA and CIPC requirements for the declared entity type.

**Red flags to surface:**
- Company CIPC status: Deregistered
- Proof of address older than 3 months from today
- Letter of Authority trustees do not match the ID copies provided
- Director named on CoR39 has no corresponding ID document in the folder
- Trust deed present but no Letter of Authority
- Company registered > 1 year ago but no annual return (CoR123) found
- Company owned by trust but no trust documents present

---

## Phase 6 — Output JSON

Write `owner_classification.json` to the same folder as the input documents.

```json
{
  "entity_type": "Company",
  "entity_subtype": "Pty Ltd",
  "owned_by_trust": false,
  "trust_entity": null,
  "fica": {
    "status": "complete | incomplete | needs_review",
    "documents": [
      {
        "type": "SA ID",
        "filename": "john_smith_id.pdf",
        "extracted": {
          "full_name": "John Smith",
          "id_number": "7601015009087",
          "date_of_birth": "1976-01-01",
          "nationality": "South African",
          "document_type": "SA ID"
        },
        "status": "found"
      }
    ],
    "missing": ["Bank Confirmation Letter"],
    "flags": ["Proof of address dated 2025-11-10 — may be older than 3 months"]
  },
  "cipc": {
    "status": "complete | incomplete | needs_review",
    "documents": [
      {
        "type": "CoR14.3",
        "filename": "registration_certificate.pdf",
        "extracted": {
          "registration_number": "2018/123456/07",
          "company_name": "Acme Property (Pty) Ltd",
          "entity_type": "Pty Ltd",
          "registration_date": "2018-03-15",
          "registered_address": "12 Oak Street, Stellenbosch, 7600",
          "cipc_status": "Active"
        },
        "status": "found"
      }
    ],
    "missing": ["CoR15.1A (MOI)"],
    "flags": []
  },
  "extracted_data": {
    "registration_number": "2018/123456/07",
    "company_name": "Acme Property (Pty) Ltd",
    "directors": [
      {"full_name": "John Smith", "id_number": "7601015009087", "nationality": "South African", "appointed_date": "2018-03-15"}
    ],
    "address": "12 Oak Street, Stellenbosch, 7600",
    "tax_number": "1234567890",
    "vat_number": ""
  },
  "classified_at": "2026-04-06T10:30:00Z"
}
```

When `owned_by_trust` is `true`, populate `trust_entity`:

```json
"trust_entity": {
  "trust_name": "Smith Family Trust",
  "trust_number": "IT1234/2015",
  "urn": "12345/2015",
  "trustees": [
    {"full_name": "Jane Smith", "id_number": "7812020012089"}
  ],
  "fica": {
    "status": "incomplete",
    "documents": [],
    "missing": ["Certified ID for Jane Smith", "Proof of Trust Address"],
    "flags": []
  },
  "cipc": {
    "status": "complete",
    "documents": [
      {"type": "Letter of Authority", "filename": "letters_of_authority.pdf", "extracted": {...}, "status": "found"},
      {"type": "Trust Deed", "filename": "trust_deed.pdf", "extracted": {...}, "status": "found"}
    ],
    "missing": [],
    "flags": []
  }
}
```

---

## Phase 7 — Cross-Entity Person Joints

After all entities are processed, build a deduplicated registry of every natural person encountered across all roles. Match by **ID number** as the primary key.

This matters for two reasons:
1. **FICA efficiency** — if Francois Du Toit already provided a certified ID as a director, his trustee role in the same folder doesn't need a second copy. Flag reuse so the user doesn't chase duplicates.
2. **Beneficial ownership graph** — a person appearing in multiple roles (director + trustee, member + partner) indicates control concentration that FICA and POPIA require to be disclosed.

### How to build joints

For every entity block (company, trust, CC, partnership), collect every named natural person and their role(s). Group all appearances of the same ID number together.

A **joint** exists when the same person appears in more than one role or entity. Examples:
- Director of the company AND trustee of the trust that owns it
- Trustee AND beneficiary of the same trust
- Member of a CC AND director of a related company
- Same person listed under two different name spellings (flag for manual review)

### Output — `persons_graph` array

Add this block to `owner_classification.json`:

```json
"persons_graph": [
  {
    "id_number": "6809125034083",
    "full_name": "FRANCOIS PETRUS DU TOIT",
    "roles": [
      {"entity": "STELLENBOSCH WINE ESTATES (PTY) LTD", "entity_type": "Company", "role": "Managing Director"},
      {"entity": "THE BOLAND PROPERTY TRUST", "entity_type": "Trust", "role": "Trustee"}
    ],
    "fica_documents_found": ["SA ID (certified 2026-02-10)"],
    "fica_reuse_note": "ID already collected — valid for both Director and Trustee roles. No duplicate needed.",
    "joint_flag": true,
    "joint_description": "Controls both the company (as MD) and the trust that owns it (as Trustee) — beneficial ownership concentration.",
    "system_records": [
      {
        "source": "User",
        "role": "TENANT",
        "related": [{"type": "Lease (primary tenant)", "unit": "Unit 3, 12 Oak St", "status": "active"}]
      }
    ],
    "system_note": "Active tenant at Unit 3, 12 Oak St — also director of this company being onboarded as landlord."
  },
  {
    "id_number": "7002170089080",
    "full_name": "SOPHIA ELEANOR DU TOIT",
    "roles": [
      {"entity": "THE BOLAND PROPERTY TRUST", "entity_type": "Trust", "role": "Trustee"}
    ],
    "fica_documents_found": [],
    "fica_reuse_note": null,
    "joint_flag": false,
    "joint_description": null,
    "system_records": [],
    "system_note": null
  }
]
```

### Red flags to add from joints analysis

- Same person holds 25%+ across two or more entities in this folder → note as **ownership concentration**
- Person appears as trustee of the trust AND director of the trust-owned company → note as **dual control** (common, but must be disclosed)
- Two entries with different ID numbers but identical names → flag as **possible duplicate / name variant — verify**
- A person named in a CIPC document (CoR39, CK1, Trust Deed) but no ID document provided → flag per entity AND in persons_graph

### System lookup — check existing records

After building the persons_graph, call the backend lookup API for each unique ID number and for the entity's registration number. This reveals if any person is already known to the system (e.g. a director who is also a current or past tenant).

**Endpoints:**
```
GET http://localhost:8000/api/v1/accounts/lookup/?id_number=<13-digit-id>
GET http://localhost:8000/api/v1/accounts/lookup/?registration_number=<YYYY/XXXXXX/07>
```

Use the JWT access token from the current session as `Authorization: Bearer <token>`.

For each person in `persons_graph`, add a `system_records` array:

```json
"system_records": [
  {
    "source": "User",
    "role": "TENANT",
    "related": [
      {"type": "Lease (primary tenant)", "unit": "Unit 3, 12 Oak St", "status": "active"}
    ]
  }
]
```

If `system_records` is non-empty, add to the persons_graph entry:
- `system_note`: e.g. `"Active tenant at Unit 3, 12 Oak St — also director of this company"`

If no system records found, set `system_records: []` and `system_note: null`.

Do the same for the entity's registration number — if the company/trust/CC is already a Landlord in the system, note its landlord ID and linked properties.

### FICA reuse rule

If a valid certified ID for a person was already collected (found in this folder), note it in `fica_reuse_note` for every other role they hold. Only one certified copy is required per person regardless of how many roles they play — but it must be the same document (same ID number, same name spelling).

---

## Summary Report

After writing the JSON, print a human-readable summary to the conversation:

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
