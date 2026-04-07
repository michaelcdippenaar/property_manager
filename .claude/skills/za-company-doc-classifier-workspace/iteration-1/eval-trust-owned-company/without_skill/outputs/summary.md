# Owner Document Classification — Trust-Owned Company
**Classification date:** 2026-04-06
**Source:** `/tmp/za-doc-test/trust_owned_company/`
**Overall status:** INCOMPLETE

---

## Entities

This is a two-tier ownership structure:

| Entity | Type | Identifier |
|--------|------|-----------|
| Stellenbosch Wine Estates (Pty) Ltd | Private Company | Reg: 2015/234567/07 |
| The Boland Property Trust | Inter Vivos Trust | IT4521/2010 |

The trust holds **100% of the shares** in the company (confirmed by both the trust deed and letters of authority).

### Natural Persons Identified

| Name | ID Number | Roles |
|------|-----------|-------|
| Francois Petrus Du Toit | 6809125034083 | Company MD, Trust Founder, Trustee |
| Sophia Eleanor Du Toit | 7002170089080 | Trustee |
| Hendrik Jacobus Meyer | 8104175067081 | Company Director |

---

## Document Classification

| Filename | Type | Category | Entity | Status |
|----------|------|----------|--------|--------|
| `cor14_3.txt` | Company Registration | Certificate of Incorporation (CoR14.3) | Company | Valid |
| `cor39_directors.txt` | Company Registration | Notice of Directors (CoR39) | Company | Valid |
| `trust_deed.txt` | Trust Registration | Deed of Trust (Trust Instrument) | Trust | Valid |
| `letters_of_authority.txt` | Trust Registration | Letters of Authority (Master's) | Trust | Valid (see caveat) |
| `francois_id.txt` | FICA | Proof of Identity — Certified ID Copy | Francois Du Toit | Valid |
| `proof_of_address_old.txt` | FICA | Proof of Address (Municipal Account) | Company | **EXPIRED** |

---

## Issues Found

### High Severity

1. **Proof of address expired** (`proof_of_address_old.txt`)
   - Statement date: 2025-09-30 — now 188 days old
   - FICA standard: not older than 3 months (90 days)
   - **Action:** Obtain current municipal account, utility bill, or bank statement

2. **No ID document for Sophia Eleanor Du Toit** (Trustee)
   - **Action:** Obtain certified SA ID copy

3. **No ID document for Hendrik Jacobus Meyer** (Company Director)
   - **Action:** Obtain certified SA ID copy

### Medium Severity

4. **No proof of residential address for Francois Du Toit** (as natural person / trustee)
5. **No proof of residential address for Sophia Du Toit** (trustee)
6. **No Memorandum of Incorporation (MOI)** for the company
7. **No share register / share certificate** formally confirming trust holds 100% of company shares

### Low Severity

8. **Letters of Authority issued 2010** — 16 years ago
   - These do not expire, but best practice is to verify no trustee changes have occurred
   - If trustees have changed, fresh Letters of Authority are required

---

## What is Present and Valid

- Company Certificate of Incorporation (CoR14.3) — confirms active Pty Ltd
- CoR39 Directors Notice — lists both directors with SA ID numbers
- Trust Deed — establishes the trust, names trustees, confirms 100% ownership of company
- Letters of Authority — Master of the High Court authorisation of trustees
- Certified ID for Francois Du Toit — certified 2026-02-10, valid (55 days old, within 3-month window)

---

## FICA Completeness by Entity

### Company (Stellenbosch Wine Estates Pty Ltd)
- Proof of existence (CoR14.3): Present
- Directors / control persons (CoR39): Present
- Proof of address: **Expired — must replace**
- MOI: Missing (medium requirement)

### Trust (The Boland Property Trust)
- Trust instrument (Deed of Trust): Present
- Authority to act (Letters of Authority): Present (with age caveat)
- Trust proof of address: Missing
- Link to company (shareholding): Confirmed in trust deed text but no formal share register

### Natural Persons
| Person | ID Doc | Proof of Address |
|--------|--------|-----------------|
| Francois Du Toit | Present (valid) | Missing |
| Sophia Du Toit | Missing | Missing |
| Hendrik Meyer | Missing | Missing |

---

## Summary

The document set is partially complete. The structural documentation for the ownership chain is sound — the trust deed and letters of authority clearly establish the trust, and the CoR14.3 and CoR39 establish the company. However, **FICA compliance is not met** because: the company's proof of address is expired, and ID documents and proof of address are missing for two of the three natural persons (Sophia Du Toit and Hendrik Meyer). The proof of address must be replaced immediately; ID documents for all directors and trustees must be collected as a priority.
