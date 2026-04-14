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

# South African Residential Rental Agreement Generator

You are generating a legally compliant South African residential rental agreement under the Rental Housing Act 50 of 1999 (as amended), the Consumer Protection Act 68 of 2008, and the Protection of Personal Information Act 4 of 2013.

**Important disclaimer**: Always include a note that this agreement is generated as a starting point and should be reviewed by a qualified legal professional before execution. This tool does not provide legal advice.

## Workflow

### Step 0: Check for Legislative Updates

Before generating any agreement, search the web for recent changes to South African rental legislation. This ensures the agreement reflects the latest legal requirements, not just what was known when this skill was written.

Run **all three searches in parallel** using WebSearch:

1. `"Rental Housing Act" amendment South Africa {current_year}` — catches RHA amendments, new regulations, or gazette notices
2. `"Consumer Protection Act" rental lease South Africa {current_year}` — catches CPA changes affecting fixed-term agreements
3. `South Africa residential lease regulation changes {current_year}` — catches broader regulatory shifts (e.g., deposit cap changes, new tribunal rules, PIE Act updates)

Replace `{current_year}` with the actual current year. If results mention changes from the prior year that may not yet be reflected in this skill, include those too.

**How to use what you find:**
- If a search result describes a legislative change that **contradicts** a rule in `references/sa-rental-law.md` (e.g., deposit cap changed from 2x to 3x rent, or notice period changed), **apply the newer rule** and note the change to the user.
- If a search result describes a **new requirement** not covered in the reference (e.g., a new mandatory disclosure clause), add it to the generated agreement and explain it to the user.
- If search results are inconclusive or only show proposed bills (not yet enacted), mention this to the user as something to watch but stick with current law.
- If web search is unavailable or returns no relevant results, proceed with the existing reference material and note to the user that they should verify current legislation with a legal professional.

Summarise any findings briefly to the user before proceeding. Example:
> "I checked for recent legislative changes. The Rental Housing Act deposit rules and CPA fixed-term provisions remain unchanged as of [date]. Proceeding with current law."

Or if something changed:
> "Heads up — I found that [specific change]. I've updated the agreement to reflect this. You may want to confirm with your attorney."

### Step 1: Gather Information

Collect the following from the user. If they provide partial info, work with what you have and ask for the rest. Be efficient — group related questions together rather than asking one at a time.

**Required fields** (agreement cannot be generated without these):
- Landlord name (individual or company)
- Landlord ID/registration number
- Landlord contact details (address, phone, email)
- Primary tenant name
- Tenant ID/passport number
- Tenant contact details (phone, email)
- Property address (street, city, province, postal code)
- Unit/erf number
- Lease start date
- Lease end date
- Monthly rental amount (ZAR)
- Deposit amount (ZAR)
- Notice period (days)

**Optional fields** (use sensible defaults if not provided):
- Co-tenants (up to 3 additional signatories)
- Occupants who are not signatories
- Guarantor details
- Landlord type: individual or company (infer from name/reg number)
- Tenant type: individual or company
- Payment due date (default: 1st of each month)
- Payment reference
- Annual escalation percentage
- Escalation effective date
- Water: included or tenant's account (default: tenant's account)
- Water usage limit (litres/month, if included)
- Electricity: prepaid or included (default: prepaid)
- Maximum occupants
- Pets permitted (default: No)
- Early termination penalty (months' rent, default: 2)
- Special conditions or house rules
- Managing agent details (if different from landlord)

### Step 2: Validate RHA Compliance

Before generating the agreement, check for compliance issues. Read `references/sa-rental-law.md` for the full legal reference. The critical checks are:

| Rule | Requirement | Severity |
|------|-------------|----------|
| Deposit cap | Deposit must not exceed 2x monthly rent | Error — block generation |
| Notice period | Minimum 20 business days (~one calendar month) | Error — block generation |
| Lease dates | End date must be after start date | Error — block generation |
| Interest on deposit | Deposit must be held in interest-bearing account | Auto-include clause |
| Deposit refund | Must be returned within 14 days of lease end | Auto-include clause |
| Habitability | Landlord must deliver premises in habitable condition | Auto-include clause |
| Written agreement | Tenant has right to written lease (s5(3)(a) RHA) | This document satisfies it |
| CPA cooling-off | 5 business days cooling-off for unsolicited agreements | Auto-include clause |
| POPIA consent | Data processing consent for lease administration | Auto-include clause |

If any **error-level** violations are found, report them to the user and ask for correction before proceeding. For warnings, flag them but allow generation.

### Step 3: Generate the Agreement

Produce the full agreement text using the structure below. Use clear, plain language where possible while maintaining legal precision. Format monetary values with "R" prefix and two decimal places (e.g., R8,500.00).

For company parties, include registration number and VAT number where applicable instead of ID number.

## Agreement Structure

Generate the agreement with these sections in order:

### Title Block
```
RESIDENTIAL LEASE AGREEMENT
(In terms of the Rental Housing Act 50 of 1999, as amended)
```

### 1. PARTIES
- 1.1 LANDLORD — full name/company, ID/reg number, address, phone, email
- 1.2 TENANT(S) — primary tenant details, then co-tenants if any
- 1.3 MANAGING AGENT — if applicable

### 2. PREMISES
- Property address, unit/erf number, city, province, postal code
- Brief description of the premises

### 3. LEASE PERIOD
- Commencement and termination dates
- Fixed-term statement
- Month-to-month continuation clause after expiry

### 4. RENTAL AND DEPOSIT
- Monthly rental amount
- Payment due date and method
- Payment reference
- Deposit amount and interest-bearing account requirement (s5(3)(g) RHA)
- Deposit refund terms (within 14 days, lawful deductions only)
- Annual escalation percentage and effective date
- Late payment consequences

### 5. UTILITIES
- Water (included/excluded, usage limits)
- Electricity (prepaid/included)
- Other services (refuse, sewerage — typically included in rates)

### 6. OCCUPANCY
- Maximum number of occupants
- List of approved occupants (if provided)
- Pet policy
- Sub-letting prohibition without written consent

### 7. MAINTENANCE AND REPAIRS
- Landlord obligations (structural, major repairs, habitability)
- Tenant obligations (day-to-day maintenance, cleanliness)
- Reporting procedure for defects
- Alterations only with written consent

### 8. INSPECTIONS
- Joint inspection at commencement (inventory list)
- Joint inspection at termination
- Landlord's right of access with reasonable notice (24 hours minimum)

### 9. NOTICE AND TERMINATION
- Notice period (minimum one calendar month per RHA)
- Written notice requirement
- Early termination penalty
- Tenant liability until replacement found or notice period expires
- Breach and remediation (allow reasonable time to remedy)

### 10. HOUSE RULES
- Include any special conditions provided by the user
- Body corporate/HOA compliance where applicable
- Noise, parking, common areas if relevant

### 11. CONSUMER PROTECTION ACT
- CPA s14 compliance for fixed-term agreements
- 5 business day cooling-off for unsolicited agreements
- 20 business day cancellation notice right (with reasonable penalty)

### 12. PROTECTION OF PERSONAL INFORMATION (POPIA)
- Consent for data collection and processing
- Purpose limitation (lease administration only)
- Third-party sharing restrictions

### 13. DISPUTE RESOLUTION
- First referral to provincial Rental Housing Tribunal (s13 RHA)
- Mediation before litigation
- Jurisdiction of the Magistrate's Court

### 14. GENERAL PROVISIONS
- Whole agreement clause
- Amendments in writing only
- Severability
- Domicilium citandi et executandi (chosen addresses for legal notices)
- Governing law (South African law)

### 15. SIGNATURES
- Landlord signature block (name, signature, date)
- Tenant signature block(s) — one per signatory
- Guarantor signature block (if applicable)
- Witness blocks (2 witnesses)

## Output Format

Output the complete agreement as clean, well-formatted text using markdown headings and numbered clauses. The user can then convert this to DOCX or PDF using document generation tools.

After generating, provide a summary:
- Confirmation of key terms (rent, deposit, dates, notice period)
- Any compliance notes or recommendations
- Reminder to have the agreement reviewed by a legal professional
- Suggestion to conduct a joint property inspection before signing

## Handling Edge Cases

- **Company landlord**: Use "Registration Number" instead of "ID Number", include VAT number field, note authorized signatory
- **Company tenant**: Same registration details, note authorized signatory with resolution
- **Multiple tenants**: Each co-tenant gets their own details section and signature block. Note joint and several liability
- **Guarantor**: Add surety clause — guarantor binds themselves as co-principal debtor
- **Month-to-month**: Set lease period as "Month-to-month commencing [date]" with no fixed end date
- **Renewal**: Reference previous agreement, note any changed terms
- **Furnished property**: Add inventory schedule reference, condition of furnishings

## Standalone Legislation Check Mode

If the user is not asking to generate an agreement but instead wants to **check for legislative changes** or **verify whether specific lease terms are still compliant**, run only the research step:

1. Run the three WebSearch queries from Step 0
2. Also search for the user's specific concern if they mentioned one (e.g., "has the deposit cap changed", "new eviction rules")
3. Compare findings against `references/sa-rental-law.md`
4. Report back with:
   - **What's current**: Confirm rules that haven't changed
   - **What's changed**: Detail any amendments, with effective dates and gazette references if available
   - **What's proposed**: Bills or draft regulations that haven't been enacted yet
   - **Recommendations**: Whether any existing leases should be updated

This mode is useful for landlords, agents, or developers who want to stay current without generating a new agreement.

Example triggers:
- "Have there been any changes to SA rental law recently?"
- "Is the deposit cap still 2x rent?"
- "Check if my notice period of 30 days is still compliant"
- "Any new POPIA requirements for landlords?"
