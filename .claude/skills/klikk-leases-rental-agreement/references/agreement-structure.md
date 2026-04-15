# Agreement Structure & Edge Cases

---

## Section Structure (15 sections)

### Title Block
```
RESIDENTIAL LEASE AGREEMENT
(In terms of the Rental Housing Act 50 of 1999, as amended)
```

### 1. PARTIES
- 1.1 LANDLORD — full name/company, ID/reg number, address, phone, email
- 1.2 TENANT(S) — primary tenant + co-tenants
- 1.3 MANAGING AGENT — if applicable

### 2. PREMISES
- Property address, unit/erf number, city, province, postal code
- Brief description of the premises

### 3. LEASE PERIOD
- Commencement and termination dates; fixed-term statement
- Month-to-month continuation clause after expiry

### 4. RENTAL AND DEPOSIT
- Monthly rental, payment due date and method, payment reference
- Deposit + interest-bearing account requirement (s5(3)(g) RHA)
- Deposit refund terms (within 14 days, lawful deductions only)
- Annual escalation % and effective date; late payment consequences

### 5. UTILITIES
- Water (included/excluded, usage limits)
- Electricity (prepaid/included)
- Other services (refuse, sewerage)

### 6. OCCUPANCY
- Maximum number of occupants; approved occupants list
- Pet policy; sub-letting prohibition without written consent

### 7. MAINTENANCE AND REPAIRS
- Landlord obligations (structural, major repairs, habitability)
- Tenant obligations (day-to-day maintenance, cleanliness)
- Reporting procedure; alterations only with written consent

### 8. INSPECTIONS
- Joint inspection at commencement (inventory list)
- Joint inspection at termination
- Landlord's right of access with 24 hours minimum notice

### 9. NOTICE AND TERMINATION
- Notice period (minimum one calendar month per RHA)
- Written notice requirement; early termination penalty
- Tenant liability until replacement found or notice period expires
- Breach and remediation (allow reasonable time to remedy)

### 10. HOUSE RULES
- Special conditions provided by the user
- Body corporate/HOA compliance where applicable

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
- Mediation before litigation; Magistrate's Court jurisdiction

### 14. GENERAL PROVISIONS
- Whole agreement clause; amendments in writing only; severability
- Domicilium citandi et executandi; governing law (SA)

### 15. SIGNATURES
- Landlord signature block (name, signature, date)
- Tenant signature block(s) — one per signatory
- Guarantor signature block (if applicable)
- Witness blocks (2 witnesses)

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Company landlord | "Registration Number" instead of "ID Number"; include VAT; note authorized signatory |
| Company tenant | Same registration details; authorized signatory with resolution |
| Multiple tenants | Each co-tenant gets own details section + signature block; note joint and several liability |
| Guarantor | Add surety clause — guarantor binds as co-principal debtor |
| Month-to-month | Set period as "Month-to-month commencing [date]" with no fixed end date |
| Renewal | Reference previous agreement; note any changed terms |
| Furnished property | Add inventory schedule reference; condition of furnishings |

---

## RHA Compliance Checks (mandatory before generating)

| Rule | Requirement | Severity |
|------|-------------|----------|
| Deposit cap | Must not exceed 2× monthly rent | Error — block generation |
| Notice period | Minimum 20 business days (~one calendar month) | Error — block generation |
| Lease dates | End date must be after start date | Error — block generation |
| Interest on deposit | Must be held in interest-bearing account | Auto-include clause |
| Deposit refund | Return within 14 days of lease end | Auto-include clause |
| Habitability | Landlord must deliver premises in habitable condition | Auto-include clause |
| CPA cooling-off | 5 business days for unsolicited agreements | Auto-include clause |
| POPIA consent | Data processing consent | Auto-include clause |
