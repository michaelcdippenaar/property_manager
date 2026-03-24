# Rental Agreement Skill — System Documentation

**Created:** 2026-03-24
**Author:** Claude Opus 4.6 + Michael Dippenaar
**Branch:** claude/lucid-ishizaka
**Status:** Draft — pending test cases and iteration

---

## 1. Overview

A Claude Code skill that generates legally compliant South African residential rental/lease agreements. The skill automates agreement drafting while enforcing compliance with three primary statutes:

- **Rental Housing Act 50 of 1999** (as amended) — governs residential leases
- **Consumer Protection Act 68 of 2008** — applies to commercial landlords
- **Protection of Personal Information Act 4 of 2013 (POPIA)** — data privacy

The skill also includes a **web search tool** that checks for recent legislative changes before each generation, ensuring agreements reflect current law.

---

## 2. Architecture

### File Structure

```
.claude/skills/rental-agreement/
├── SKILL.md                          # Main skill definition (245 lines)
└── references/
    └── sa-rental-law.md              # Legal reference file (159 lines)
```

### How It Integrates with Tremly

The skill is a **Claude Code skill** — it runs inside Claude Code sessions, not inside the Tremly Django app. It complements the existing app features:

| Feature | Tremly App (Django) | Claude Code Skill |
|---------|--------------------|--------------------|
| Lease data model | `backend/apps/leases/models.py` | N/A — generates text, not DB records |
| AI lease builder | `builder_views.py` — conversational API | Standalone prompt-based generation |
| DOCX template | `sa_residential_lease.docx` (docxtpl) | Generates markdown text for conversion |
| RHA compliance | Validates in builder chat turns | Validates before generating full text |
| Legislation updates | Static rules in code | **Live web search before each generation** |
| E-signing | DocuSeal integration | N/A — outputs text for downstream tools |

### Workflow

```
Step 0: Search web for legislative updates (3 parallel WebSearch queries)
    ↓
Step 1: Gather information from user (required + optional fields)
    ↓
Step 2: Validate RHA compliance (block on errors, warn on issues)
    ↓
Step 3: Generate complete agreement text (15 sections)
    ↓
Output: Markdown text + compliance summary + legal disclaimer
```

---

## 3. Skill Definition (SKILL.md)

### Trigger Description

The skill triggers on phrases like:
- "Generate a rental agreement"
- "I need a lease"
- "Draw up a contract for my tenant"
- "RHA compliant lease"
- "Check SA rental law changes"
- "Is the deposit cap still 2x rent?"

### Required Fields

| Field | Example |
|-------|---------|
| Landlord name | Klikk (Pty) Ltd |
| Landlord ID/reg number | 2016/113758/07 |
| Landlord contact | address, phone, email |
| Primary tenant name | Sarah Jones |
| Tenant ID/passport | 9203045100089 |
| Tenant contact | phone, email |
| Property address | 42 Main Road, Cape Town, Western Cape |
| Unit/erf number | Unit 5 |
| Lease start date | 2026-04-01 |
| Lease end date | 2027-03-31 |
| Monthly rent (ZAR) | R8,500.00 |
| Deposit (ZAR) | R12,000.00 |
| Notice period (days) | 30 |

### Optional Fields (with defaults)

| Field | Default |
|-------|---------|
| Co-tenants | None |
| Payment due date | 1st of each month |
| Escalation % | Not specified |
| Water | Tenant's account |
| Electricity | Prepaid |
| Maximum occupants | Not specified |
| Pets | No |
| Early termination penalty | 2 months' rent |
| Special conditions | None |

### Compliance Validation Rules

| Rule | Check | Severity |
|------|-------|----------|
| Deposit cap | deposit <= 2 * monthly_rent | Error — blocks generation |
| Notice period | >= 20 business days (~1 calendar month) | Error — blocks generation |
| Lease dates | end_date > start_date | Error — blocks generation |
| Interest on deposit | Must be in interest-bearing account | Auto-included |
| Deposit refund | Within 14 days of lease end | Auto-included |
| Habitability | Landlord must deliver habitable premises | Auto-included |
| CPA cooling-off | 5 business days for unsolicited agreements | Auto-included |
| POPIA consent | Data processing consent clause | Auto-included |

### Generated Agreement Sections

1. **PARTIES** — Landlord, tenant(s), managing agent
2. **PREMISES** — Address, unit, description
3. **LEASE PERIOD** — Dates, fixed-term, month-to-month continuation
4. **RENTAL AND DEPOSIT** — Amounts, payment terms, interest, escalation
5. **UTILITIES** — Water, electricity, other services
6. **OCCUPANCY** — Max occupants, pets, sub-letting
7. **MAINTENANCE AND REPAIRS** — Landlord and tenant obligations
8. **INSPECTIONS** — Joint inspections, landlord access rights
9. **NOTICE AND TERMINATION** — Notice period, early termination, breach
10. **HOUSE RULES** — Special conditions, body corporate
11. **CONSUMER PROTECTION ACT** — CPA s14, cooling-off, cancellation
12. **POPIA** — Data consent, purpose limitation, sharing
13. **DISPUTE RESOLUTION** — Rental Housing Tribunal, mediation
14. **GENERAL PROVISIONS** — Whole agreement, severability, domicilium
15. **SIGNATURES** — Landlord, tenant(s), guarantor, witnesses

### Edge Cases Handled

- Company landlords/tenants (registration + VAT numbers)
- Multiple tenants (joint and several liability)
- Guarantors (surety as co-principal debtor)
- Month-to-month leases (no fixed end date)
- Lease renewals (reference previous agreement)
- Furnished properties (inventory schedule)

---

## 4. Legislative Search Tool

### Purpose

South African rental law changes periodically. The skill searches the web before every agreement generation to catch amendments that post-date the reference file.

### Search Queries (run in parallel)

1. `"Rental Housing Act" amendment South Africa {year}`
2. `"Consumer Protection Act" rental lease South Africa {year}`
3. `South Africa residential lease regulation changes {year}`

### Decision Logic

| Finding | Action |
|---------|--------|
| Legislative change contradicts reference | Apply newer rule, notify user |
| New requirement not in reference | Add to agreement, explain to user |
| Proposed bill (not enacted) | Mention as watch item, use current law |
| No relevant results / search unavailable | Proceed with reference, recommend legal review |

### Standalone Mode

The legislation search also works independently — users can check for law changes without generating an agreement. Useful triggers:
- "Have there been any changes to SA rental law recently?"
- "Is the deposit cap still 2x rent?"
- "Any new POPIA requirements for landlords?"

---

## 5. Legal Reference File (sa-rental-law.md)

### Coverage

| Statute | Sections Covered |
|---------|-----------------|
| Rental Housing Act | s4A (unfair practices), s5 (lease requirements), s5A/5B (obligations), s13 (tribunal) |
| Consumer Protection Act | s14 (fixed-term), s16 (cooling-off), s22 (plain language), s48 (unfair terms), s54 (quality) |
| POPIA | Applicability, required disclosures, consent clause requirements |

### Top 10 Compliance Pitfalls Documented

1. Deposit exceeds 2x rent
2. No interest-bearing account clause
3. Notice period < one calendar month
4. Penalty equal to remaining rent
5. No joint inspection clause
6. Waiver of Tribunal rights
7. No escalation clause
8. Missing POPIA consent
9. Sub-letting without clarity
10. No domicilium clause

### Province-Specific Data

Tribunal contact references for all 9 provinces (Gauteng, Western Cape, KZN, Eastern Cape, Free State, Mpumalanga, Limpopo, North West, Northern Cape).

---

## 6. Relationship to Existing Tremly Code

### Backend Components Referenced

| File | What It Does | Relationship to Skill |
|------|-------------|----------------------|
| `backend/apps/leases/models.py` | Lease, LeaseTemplate, LeaseBuilderSession models | Skill generates text; app stores structured data |
| `backend/apps/leases/builder_views.py` | Conversational AI lease builder (Claude API) | Similar logic, different interface (API vs. skill) |
| `backend/apps/leases/template_views.py` | DOCX generation via docxtpl | Skill output can feed into this pipeline |
| `backend/lease_templates/build_sa_template.py` | Builds SA lease DOCX template | Skill's agreement structure mirrors this template |
| `backend/apps/leases/parse_view.py` | Parse lease PDFs with Claude | Complementary — parse existing vs. generate new |
| `backend/apps/esigning/` | DocuSeal e-signing integration | Downstream of skill — sign after generating |

### Business Rules from Klikk

- Up to 4 tenants per unit (skill supports primary + 3 co-tenants)
- Deposit = 1 month rent (standard for Klikk, but skill allows up to 2x per RHA)
- Water included up to 4,000 litres/month per occupant
- Electricity via prepaid meter
- Early termination: 20 business days notice, up to 3 months penalty
- Payment reference format: `"<Property> - <Surname>"`
- Landlord: Klikk (Pty) Ltd, reg 2016/113758/07

---

## 7. Test Cases (Planned)

### Test 1: Basic Fixed-Term Lease
**Prompt:** Generate a rental agreement for apartment at 42 Main Road, Cape Town. Landlord John Smith (ID 8501015800083). Tenant Sarah Jones (ID 9203045100089). R8,500/month, R12,000 deposit, 12 months from 1 April 2026, 30-day notice.
**Expected:** Complete 15-section agreement, all compliance checks pass, deposit within 2x cap.

### Test 2: Company Landlord with Co-Tenants
**Prompt:** Lease for Acme Properties (Pty) Ltd (reg 2015/123456/07, VAT 4150123456). Unit 5, Sunrise Villas, 15 Elm Street, Sandton. Two tenants — Thabo Mokoena (primary), Lerato Mokoena (co-tenant). R15,000 rent, R30,000 deposit, May 2026-April 2027. Pet clause for one small dog.
**Expected:** Company landlord format, co-tenant section, joint liability clause, pet policy, deposit at exactly 2x (passes).

### Test 3: Compliance Violation Detection
**Prompt:** Lease for 10 Beach Road, Durban. Landlord Mike van der Merwe. Tenant James Naidoo. R6,000 rent, R18,000 deposit, 14-day notice, June 2026-May 2027.
**Expected:** Two errors flagged — deposit 3x rent (exceeds 2x cap), notice period 14 days (below minimum). Generation blocked until corrected.

### Test 4: Standalone Legislation Check
**Prompt:** Have there been any changes to SA rental law this year?
**Expected:** Web search results summarised, comparison against reference file, current/changed/proposed breakdown.

---

## 8. Future Enhancements

- [ ] Run test cases and iterate on skill based on results
- [ ] Optimize skill description for better triggering accuracy
- [ ] Add DOCX output support (bundle a generation script)
- [ ] Province-specific clause variations (e.g., Western Cape water restrictions)
- [ ] Integration with Tremly API — generate agreement and push to LeaseBuilderSession
- [ ] Lease renewal mode — diff against previous agreement
- [ ] Multi-language support (Afrikaans, Zulu translations of key clauses)
- [ ] Audit trail — log which legislative searches influenced each agreement

---

## 9. Disclaimer

This skill generates rental agreements as a starting point. It does not constitute legal advice. All generated agreements should be reviewed by a qualified South African legal professional before execution. The legislative search feature provides awareness of changes but does not guarantee completeness or accuracy of legal interpretation.
