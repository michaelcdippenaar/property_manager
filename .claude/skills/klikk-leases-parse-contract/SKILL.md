---
name: klikk-leases-parse-contract
description: >
  Parse a PDF or DOCX lease contract, extract its structure, identify all
  variable/placeholder fields, and create a properly formatted HTML template with
  merge fields in the Tremly system. Triggers when the user asks to: parse a lease,
  import a contract, convert a lease to a template, extract fields from a contract,
  create a template from a PDF, import a DOCX lease, or turn a signed lease into a
  reusable template. Also triggers for requests like "parse this lease PDF",
  "import contract.docx as a template", "extract merge fields from this lease",
  or "convert this rental agreement to a template".
---

# Lease Contract Parser

Parses a PDF or DOCX lease contract → formatted HTML template with TipTap merge fields → saved as new `LeaseTemplate` via the API.

**Companion skill:** `klikk-leases-format-template` — use for post-import formatting/restructuring.

---

## 7-Step Workflow

1. **Read document** — use Claude's native PDF document API (vision-based) for PDFs; python-docx for DOCX. **Do NOT use pypdf/text extraction** — it garbles table structure and misses multi-tenant entries.
2. **Analyse structure** — map headings (h1/h2/h3), lists, tables, signature blocks
3. **Identify variables** — blank lines, `[placeholders]`, `<angle brackets>`, real data that should be templated
4. **Generate HTML** — wrap variables in `<span data-merge-field="X">{{ X }}</span>`; see field-mapping.md for tag rules
5. **Build fields schema** — JSON array with `{ref, label, type}` for every merge field
6. **Save to DB** — POST to `/api/v1/leases/templates/`, PATCH with HTML + fields
7. **Report** — sections mapped, fields count, compliance gaps, template ID

---

## Klikk Lease Template — Multi-Tenant Structure

Klikk leases list tenants in section **1.2 Details of the Tenant/s**, with sub-sections:

| Section | Heading | Field label |
|---------|---------|-------------|
| 1.2.1 | Tenant One | Tenant/Occupant 1 Full Legal Name |
| 1.2.2 | Tenant Two (if applicable) | Tenant/Occupant 2 Full Legal Name |
| 1.2.3 | Tenant Three (if applicable) | Tenant/Occupant 3 Full Legal Name |
| 1.2.4 | Tenant Four (if applicable) | Tenant/Occupant 4 Full Legal Name |

Each tenant block also contains a **"Tenant N Guardian/Co-Debtor Full Legal Name (If Applicable)"** row. These are **guarantors**, not additional tenants. Do not confuse Guardian/Co-Debtor entries with co-tenants.

When extracting structured data (for import wizard):
- `primary_tenant` → Tenant One
- `co_tenants[]` → Tenant Two, Three, Four (all non-empty entries)
- `guarantors[]` → Guardian/Co-Debtor rows, with `for_tenant` set to the tenant they cover

**Read the reference files for full details:**

---

## Reference Index

| Topic | File |
|-------|------|
| Allowed HTML tags, merge field syntax, SA field categories, variable tips, section structure | [field-mapping.md](references/field-mapping.md) |
| Step-by-step workflow with full code (PDF read, DOCX extraction, API save) | [workflow.md](references/workflow.md) |

---

## Auth

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "...", "password": "..."}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")
```
