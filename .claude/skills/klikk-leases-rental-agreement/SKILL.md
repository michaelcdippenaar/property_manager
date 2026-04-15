---
name: klikk-leases-rental-agreement
description: >
  Generate legally compliant South African residential rental/lease agreements, and check
  for recent changes to SA rental legislation. Use this skill whenever the user wants to
  create, draft, or generate a rental agreement, lease agreement, tenancy contract, or
  residential letting agreement. Also trigger when the user mentions "RHA compliant lease",
  "rental contract", "tenant agreement", "lease document", or asks to put together any
  kind of residential rental paperwork for South African properties. This covers fixed-term
  leases, month-to-month agreements, and lease renewals. Even if the user just says
  "I need a lease" or "draw up a contract for my tenant", use this skill. Also trigger
  when the user asks about South African rental law changes, RHA amendments, deposit rules,
  tenant rights updates, or wants to check if their lease terms are still legally compliant.
  Use this skill for any question about SA rental legislation or CPA changes affecting leases.
  For general SA rental knowledge (workflow, deposit rules, eviction, tax, utilities, body corporate),
  use the sa-property-rentals skill instead.
---

# SA Residential Rental Agreement Generator

Generates legally compliant SA residential agreements under RHA 50/1999, CPA 68/2008, and POPIA 4/2013.

**Always include:** disclaimer that this is a starting point and should be reviewed by a qualified legal professional.

---

## 4-Step Workflow

### Step 0: Check for Legislative Updates
Run 3 WebSearch queries in parallel before generating:
1. `"Rental Housing Act" amendment South Africa {year}`
2. `"Consumer Protection Act" rental lease South Africa {year}`
3. `South Africa residential lease regulation changes {year}`

Compare findings against `references/sa-rental-law.md`. Apply newer rules if they contradict the reference. Summarise findings to the user.

### Step 1: Gather Information
Collect from user. Group related questions together. **Required**: landlord details, tenant details, property address, lease dates, monthly rent, deposit amount, notice period. **Optional**: co-tenants, guarantor, payment due date, escalation %, utilities, pets, special conditions. Use sensible defaults for optional fields.

### Step 2: Validate RHA Compliance
Before generating — read `references/sa-rental-law.md` for the full rules. Critical checks in `references/agreement-structure.md`.

### Step 3: Generate Agreement
Follow the 15-section structure in `references/agreement-structure.md`. Format monetary values as `R8,500.00`.

---

## Reference Index

| Topic | File |
|-------|------|
| 15-section structure, edge cases (company/multi-tenant/guarantor/m2m), RHA compliance checks | [agreement-structure.md](references/agreement-structure.md) |
| Full SA rental law reference: deposits, notice, CPA, tribunals | [sa-rental-law.md](references/sa-rental-law.md) |

---

## Standalone Legislation Check Mode

If the user isn't generating but wants to **verify compliance or check for recent changes**:
1. Run the 3 WebSearch queries from Step 0
2. Search for the user's specific concern
3. Compare against `references/sa-rental-law.md`
4. Report: what's current / what's changed (with gazette refs) / what's proposed / recommendations

---

## When to Use vs Related Skills

| Task | Skill |
|------|-------|
| Generate or draft a lease | **this skill** |
| Edit/format an existing template in TipTap | `klikk-leases-tiptap-editor` |
| Parse a PDF/DOCX lease into a template | `klikk-leases-parse-contract` |
| Generate a PDF from a signed lease | `klikk-leases-pdf-export` |
| Deep SA rental law questions (eviction, PIE, deposits) | `klikk-rental-master` |
