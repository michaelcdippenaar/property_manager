# Rental Mandate Requirements — SA Law

This file drives the `mandate_readiness` block computation (Phase 9). It answers: **can this owner legally sign a rental mandate right now, and if not, what's missing?**

A rental mandate is a legal appointment of an agent to manage the property. Get the signatory wrong, and the mandate is voidable — meaning the agent has no legal authority to lease, collect rent, or act. So the rules here are strict on *who can bind the entity*, not just on *who shows up to sign*.

---

## 1. Authority Matrix — who can sign per entity type

| Entity | Who has authority | Primary proof | Secondary proof (if needed) |
|--------|-------------------|---------------|-----------------------------|
| Individual | Owner personally | SA ID / Passport | If married ICOP: spouse ID + marriage certificate (spousal consent) |
| Individual (married ANC) | Owner alone | SA ID + Antenuptial Contract | — |
| Pty Ltd | Director(s) per MOI | CoR14.3 + CoR39 (current directors) + MOI clause on signing authority | Board resolution if MOI requires >1 signer OR if signer is a single director with co-director MOI clause |
| Pty Ltd (MOI silent) | *All* directors jointly | CoR14.3 + CoR39 | Board resolution is still best practice |
| NPC / SOC Ltd / Public Ltd | Directors per MOI | Same as Pty Ltd | Board resolution |
| Close Corporation (CC) | Any member (joint & several liability) | CK1 or CK2 (current members) + member ID | If multiple members, member consent is implied but best captured |
| Trust | All trustees jointly (default, unless deed states otherwise) | Trust Deed + **current** Letters of Authority + trustee IDs | Trust deed clause on signing authority |
| Partnership | Any partner (binds all partners) | Partnership Agreement + partner IDs | — |

**Critical nuance for trusts:** A trust has no separate legal personality. Trustees act in their capacity as trustees, *nominee officio*. If the Letters of Authority don't list a person as a current trustee, they cannot sign — even if they are named in the trust deed. A stale LoA is a **blocking issue**, full stop.

**Critical nuance for companies:** The MOI (Memorandum of Incorporation) is the source of truth for signing authority. If the MOI says "any one director may sign" → single signer OK. If it says "any two directors" → need two. If silent → default position under the Companies Act is all directors jointly, which in practice means a **board resolution** is required.

---

## 2. Required Entity Fields (for mandate pre-fill)

These fields populate `mandate_readiness.extracted_fields`. Missing ones appear in `missing_fields`. The skill only extracts what's in the source docs — it must not infer.

| Field | Required? | Source document |
|-------|-----------|-----------------|
| `legal_name` | Yes | CoR14.3 / CK1 / Trust Deed / SA ID |
| `entity_type` | Yes | Registration suffix or classification inference |
| `registration_number` | Yes (entities) | CoR14.3 / CK1 / CoR15.1 |
| `id_number` | Yes (individuals) | SA ID |
| `vat_number` | Conditional (if turnover ≥ R1m or voluntarily registered) | VAT Registration Certificate / SARS docs |
| `tax_number` | Yes | SARS tax certificate or any SARS correspondence showing TRN |
| `physical_address` | Yes | CoR14.3 registered office / Proof of Address |
| `postal_address` | Optional (defaults to physical) | CoR14.3 or entity letterhead |
| `bank_payout` | Yes | Bank Confirmation Letter |
| `title_deed` | Yes | Title Deed / Deeds Office extract |
| `marital_regime` | Yes (individuals) | SA ID (for married status) + marriage cert / ANC |

---

## 3. Bank Payout Rules

The bank account that receives rent must be in the name of the legal entity. Mismatches are a common source of mandate disputes — an owner who pays themselves via a personal account from a company-owned property creates tax and compliance problems.

| Check | Rule | On fail |
|-------|------|---------|
| Holder name matches entity legal name | Exact match (allowing ordinary case/abbreviation variance like "(Pty) Ltd" vs "Proprietary Limited") | **Blocking issue** |
| Branch code present | SA branch codes are 6 digits | Blocking if missing |
| Account type captured | Current / Savings / Transmission | Warning if missing |
| Account number last 4 only | Never log the full number | Enforced by extraction |
| Bank confirmation letter present | Must be an actual bank letter, not a statement or screenshot | Blocking if missing/unverifiable |
| Letter age | Typically ≤ 3 months for FICA purposes | Warning at > 3 months; blocking at > 6 months |

---

## 4. Title Deed Proof

Prove the owner actually owns the property they're mandating you to manage. This catches cases where the owner has sold the property but is still signing as landlord (happens more than you'd think after divorces and estate transfers).

Extract from the Title Deed or Deeds Office extract:
- `title_deed_number` (e.g. `T12345/2018`)
- `erf` or full property description
- `registered_owner` (the name on the deed)

Then compute `registered_owner_matches_entity`:
- For entities: `registered_owner` should match `legal_name` (allow (Pty) Ltd vs Proprietary Limited)
- For individuals: match on full name + ID number if available
- For trusts: `registered_owner` should reference the trust, not a specific trustee personally

Mismatch = **blocking issue**. Flag as "title deed registered to X, but entity being onboarded is Y — confirm ownership chain."

---

## 5. Marital Regime (Individuals Only)

South African matrimonial property law:

| Regime | Implication for mandate |
|--------|-------------------------|
| Single / Widowed / Divorced | Owner signs alone |
| Married in Community of Property (ICOP) | **Spouse must consent** — Matrimonial Property Act §15 — mandate is a juristic act affecting joint estate |
| Married Out of Community (ANC without accrual) | Owner signs alone — property is in their separate estate |
| Married Out of Community (ANC with accrual) | Owner signs alone — but property transfers may need ANC review |

**Extraction approach:** SA IDs don't always encode marital status. When the owner is an individual:
1. Look for marriage certificate (indicates ICOP unless ANC registered)
2. Look for Antenuptial Contract (ANC document)
3. If neither present and owner is an individual → add to `missing_fields: ["marital_regime"]` (not blocking on its own, but cannot finalise mandate without spouse consent if ICOP)

---

## 6. Gap Analysis — `mandate_readiness` population rules

Read the entity's `classification_data`. For each requirement above:

| Outcome | Placement |
|---------|-----------|
| Required document missing | `missing_fields[]` entry + `blocking_issues[]` if the doc is required to establish authority |
| Field present in doc but not extracted (OCR miss, unreadable) | `missing_fields[]` with a note on the source |
| Document present but stale (proof of address >3mo, LoA superseded) | `warnings[]` if ambiguous, `blocking_issues[]` if definitive |
| Signer attempting authority they don't have | `blocking_issues[]` with a human-readable explanation |
| Everything present and valid | `status: "ready"`, empty `blocking_issues`, empty `missing_fields` |

### Status derivation

```
if blocking_issues: status = "blocked"
elif missing_fields: status = "missing_info"
else: status = "ready"
```

### Blocking issue phrasing

Use concrete, human-readable sentences. The chat UI surfaces these verbatim to the owner/agent, so they need to be actionable.

**Good:**
- "Letters of Authority dated 2020-06-15 list trustees Alice and Bob. John (current signatory) is not listed. Upload current Letters of Authority naming John as trustee."
- "Board resolution authorising Sarah Jones to sign the mandate has not been provided. The MOI requires 2 directors — Sarah is listed but a second director must co-sign or a resolution must be uploaded."

**Bad:**
- "Authority issue"
- "LoA problem"
- "Missing signatory authorisation"

---

## 7. Quick entity-type checklist (what to look for first)

### Pty Ltd
1. CoR14.3 — company is Active (not Deregistered, not In Liquidation)
2. CoR39 — current directors list
3. MOI (CoR15.1A/B) — signing authority clause
4. Director ID for each signer
5. Board resolution if MOI requires joint signing
6. Bank confirmation letter in company name
7. Proof of registered office
8. Tax + VAT numbers

### Close Corporation
1. CK1 or CK2 — current members
2. Member ID for signer
3. Bank confirmation letter in CC name
4. Proof of CC business address
5. Tax + VAT numbers

### Trust
1. **Founding document** — one of:
   - **Trust Deed** (for *inter vivos* trusts — registered during the founder's lifetime), OR
   - **Last Will and Testament + Death Certificate** (for *testamentary* trusts — trust created by the deceased's will, comes into existence on death). A J246 Trust Registration form is also acceptable supporting evidence.
2. **Current** Letters of Authority — must list current trustees. The Master issues identical Letters of Authority regardless of how the trust was created.
3. Trustee ID for each trustee (FICA requires ALL trustees' IDs, not just signer)
4. Beneficiary IDs for beneficiaries with ≥25% interest
5. Bank confirmation letter in trust name
6. Proof of trust address
7. Tax number (trusts have their own tax number)

### Individual
1. SA ID or Passport
2. Proof of address ≤3 months
3. Tax number
4. Bank confirmation letter in individual's name
5. Marital status documentation
6. Title deed in individual's name

### Partnership
1. Partnership Agreement
2. Partner IDs for all partners (FICA)
3. Bank confirmation letter in partnership name
4. Proof of partnership business address
5. Tax + VAT numbers
