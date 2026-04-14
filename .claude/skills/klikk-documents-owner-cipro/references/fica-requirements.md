# FICA Requirements per Entity Type

## Overview

The Financial Intelligence Centre Act (FICA) 38 of 2001 requires accountable institutions (banks, estate agents, conveyancers, investment firms) to verify the identity and address of all clients before establishing a business relationship. For property management, this applies to landlords/owners.

**Today's date context:** Always compare proof-of-address dates against today's date. Documents older than 3 months must be flagged.

---

## 1. Individual

Required FICA documents:

| Document | Notes |
|---|---|
| SA Identity Document or valid Passport | Must be current. SA green ID book or Smart ID card both accepted. |
| Proof of Residential Address | Utility bill, bank statement, or municipal account. Dated within 3 months. Must show name + address. |
| SARS Income Tax Number | Verbal or written confirmation acceptable. |
| VAT Registration Number | Only if VAT registered. |

Optional / contextual:
- Source of funds declaration (if large sums or unusual activity)

---

## 2. Company (Pty Ltd / NPC / SOC Ltd / Public Ltd)

Required FICA documents:

| Document | Notes |
|---|---|
| Certified ID / Passport for **all directors** | Each director listed on CoR39 needs a certified ID copy. |
| Certified ID / Passport for **all persons holding 25%+ voting rights or beneficial interest** | Cross-reference CoR14.1 / CoR15 shareholder register. |
| Proof of Registered Address | Utility bill, bank statement, or municipal account in company name. Dated within 3 months. |
| SARS Company Income Tax Number | |
| VAT Registration Number | Only if VAT registered. |
| Bank Confirmation Letter | On bank letterhead. Shows account holder, account type, last 4 digits. |

Optional:
- CIPC annual compliance certificate
- Source of funds / board resolution authorising the signatory

---

## 2a. Company Owned by a Trust (Nested Ownership)

When a Pty Ltd is wholly or partly owned by a Trust, FICA requires tracing beneficial ownership to the natural persons behind the trust.

**Required: all Company requirements (above) PLUS:**

| Document | Notes |
|---|---|
| Certified ID / Passport for **all trustees** | Every trustee named on the Letter of Authority. |
| Certified ID / Passport for **beneficiaries with 25%+ interest** | If named in the trust deed. |
| Trust Letter of Authority | Issued by Master of the High Court. Must be current. |
| Trust Deed (or certified copy) | Founding document of the trust. |
| Proof of Trust Address | Dated within 3 months. |
| SARS Tax Number for the Trust | |

The beneficial ownership chain must be documented from the company through to the individual natural persons.

---

## 3. Trust

Required FICA documents:

| Document | Notes |
|---|---|
| Trust Deed (original or notarially certified copy) | |
| Letters of Authority from Master of the High Court | Must reflect current trustees. If trustees changed, new Letter of Authority required. |
| Certified ID / Passport for **all trustees** | Each trustee listed on the Letter of Authority. |
| Certified ID / Passport for **named beneficiaries with 25%+ beneficial interest** | Only if beneficiaries are specifically named in the trust deed. |
| Proof of Address for the trust | Dated within 3 months. |
| SARS Tax Number for the Trust | |

Optional:
- Bank confirmation letter for the trust account

---

## 4. Close Corporation (CC)

Required FICA documents:

| Document | Notes |
|---|---|
| Certified ID / Passport for **all members** | Every member named on CK1 / CK2. |
| Proof of CC business address | Dated within 3 months. |
| SARS Income Tax Number for the CC | |
| VAT Registration Number | Only if VAT registered. |
| Bank Confirmation Letter | |

---

## 5. Partnership

Required FICA documents:

| Document | Notes |
|---|---|
| Certified ID / Passport for **all partners** | Every partner named in the Partnership Agreement. |
| Partnership Agreement | Founding document evidencing the partnership. |
| Proof of business address | Dated within 3 months. |
| SARS Income Tax Number | |
| VAT Registration Number | Only if VAT registered. |
| Bank Confirmation Letter | |

---

## Address Document Acceptance Rules

The following are accepted as proof of address, **dated within 3 months**:

- Utility bill (electricity, water, gas) in the entity's/person's name
- Municipal rates account
- Bank statement (showing name and physical address, not PO Box)
- Fixed telephone/internet service account
- SARS correspondence (showing address)
- Lease agreement (if signed, with landlord details — limited acceptance)

**Not accepted:**
- PO Box addresses
- Documents older than 3 months
- Documents in a different name to the entity/person being verified
- Cell phone accounts (in most institutions)

---

## Proof of Address Age Check

To determine if a proof-of-address document is within 3 months:

```
Document issue date + 3 months >= today's date  →  VALID
Document issue date + 3 months < today's date   →  EXPIRED — flag as needs_review
```

Example: Document dated 2025-11-10. Today is 2026-04-06.
- Months since issue: ~5 months → EXPIRED → flag

---

## FICA Status Definitions

| Status | Meaning |
|---|---|
| `complete` | All required documents present and valid (address documents within 3 months) |
| `incomplete` | One or more required documents missing entirely |
| `needs_review` | All documents present but one or more has a flag (e.g. address document may be expired, trustee mismatch, etc.) |
