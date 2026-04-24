# Pricing v1.1 Review — Tier Rename and Billing Model Analysis

**Task:** RNT-QUAL-049  
**Status:** Analysis for MC sign-off (DEC-016 follow-on)  
**Date:** 2026-04-24  
**Author:** rentals-implementer  
**Decision required from:** MC — see Section 4 for sign-off checklist

---

## 1. Current State (as frozen by DEC-016 for v1.0)

| Tier key | Display name | Price | Range |
|---|---|---|---|
| `free` | Free | R0/month | Up to 5 properties |
| `pro` | Pro | R2,500/month flat | Up to 50 properties / 100 units |
| `enterprise` | Enterprise | R4,000/month base + R50/property above 100 | 100+ properties |
| `custom` | Custom | POA | Unlimited |

**Billing model:** flat-rate per organisation, per month (no per-unit pricing).  
**Key principle established in DEC-016:** Do not use "Agency" naming. Tiers are Free, Pro, Enterprise, Custom.

---

## 2. The Enterprise → Agency Rename Question

### Background

The GTM-010 pricing research report (referenced in the task but not yet written as of 2026-04-24 — the file `content/sales/pricing-research-2026.md` does not yet exist) proposed renaming `enterprise` to `agency` on the grounds that:
- The primary ICP is boutique rental agencies
- "Enterprise" carries corporate/SaaS connotations that may feel out-of-reach to a small agency principal
- "Agency" is self-descriptive for the segment

DEC-016 explicitly rejected this for v1.0 ("Do NOT use 'Agency tier' naming" per `content/brand/positioning.md`). This analysis evaluates whether v1.1 warrants reopening the question.

### Arguments for renaming Enterprise → Agency

1. **ICP alignment:** The primary ICP (boutique agency, 2–10 agents, 20–100 units) sits in Pro. The Enterprise tier serves larger agencies and estate agencies with rental books. "Agency" signals that the tier is for their business type, not for an abstract "enterprise" category.
2. **SA market language:** In SA property management, "estate agency" and "rental agency" are the natural terms. "Enterprise" is a generic SaaS word with no SA market resonance.
3. **Reduces cognitive friction:** A prospect managing 150 units sees "Enterprise" and assumes it is for large corporates. "Agency" matches their self-concept.
4. **Competitive comparison:** WeConnectU and PropWorx do not use "Enterprise" — they use agency-specific language. Klikk is entering a market where terminology matters for trust.
5. **White-label is an agency feature:** The enterprise tier's headline differentiator (white-label portals, agent app branding) is explicitly an agency need, not a corporate IT one.

### Arguments against renaming Enterprise → Agency

1. **DEC-016 was just made (2026-04-24):** Reversing a frozen decision before v1.0 data exists undermines the decision-making process. v1.1 is the correct time.
2. **Code key change risk:** Renaming the tier key from `enterprise` to `agency` in `pricing.yaml` would cascade to: backend permission checks, tier enforcement middleware, frontend Pinia store, Stripe/billing integration (when live), and any API clients. Migration and feature-flagging required. Not a trivial change.
3. **"Agency" is ambiguous at Custom tier:** The Custom tier serves non-agency clients (e.g., body corporates if scope expands, large landlord groups). A naming convention that equates the product with "agency" may close doors at enterprise/institutional level.
4. **Display name vs key are independent:** The `name` field in pricing.yaml is the display name; the `enterprise` key is internal. We can change the display name to "Agency" without changing the YAML key or any code. This is the lowest-risk path if the rename is approved.

### Recommendation on rename

**Decouple display name from tier key.** If MC approves the rename for v1.1, change only `name: "Enterprise"` → `name: "Agency"` in `pricing.yaml` and update sales/marketing content. Do not change the `enterprise` key — keep it as the internal identifier to avoid code migration overhead. This delivers the positioning benefit at zero technical risk.

**Escalate to MC as DEC-NNN** before applying any change. The decision to rename should be informed by first-client onboarding feedback on how they perceive the tier name.

---

## 3. Per-Unit vs Flat-Rate Billing Model

### Current model: flat-rate per organisation

Klikk charges R2,500/month (Pro) or R4,000/month base (Enterprise) regardless of unit count within tier limits. This is the current DEC-016-frozen position.

### Per-unit model: how it would work

A per-unit model would charge, for example, R30–R60/unit/month. Revenue scales linearly with portfolio size. This is how WeConnectU and similar SA competitors bill.

### Comparison

| Dimension | Flat-rate (current) | Per-unit |
|---|---|---|
| Revenue at 20 units | R2,500 | R600–R1,200 |
| Revenue at 50 units | R2,500 | R1,500–R3,000 |
| Revenue at 100 units | R2,500 | R3,000–R6,000 |
| Revenue at 200 units | R4,000 + R5,000 overage = R9,000 | R6,000–R12,000 |
| Customer predictability | High — fixed monthly bill | Low — varies with portfolio changes |
| Sales friction | Low — "R2,500 flat, no surprises" | High — requires portfolio audit before quote |
| Churn trigger | None within tier | Unit count drops → customer renegotiates |
| Upsell mechanic | Portfolio growth → tier upgrade | Automatic — revenue grows with portfolio |
| Competitive positioning | Disruptive (vs WeConnectU R15k at 100 units) | Converges with competitors |

### Revenue impact modelling

Assume 50 Pro customers at launch, average portfolio 40 units:

| Model | Monthly recurring revenue |
|---|---|
| Flat-rate R2,500 | R125,000 |
| Per-unit R40/unit, 40 units | R80,000 |
| Per-unit R60/unit, 40 units | R120,000 |

At small portfolio sizes (the primary ICP at launch), per-unit pricing generates *less* revenue than flat-rate unless the per-unit rate is set above R62.50/unit — at which point Klikk loses its price advantage over WeConnectU (R150–200/unit).

The flat-rate model is superior at v1.0–v1.1 portfolio sizes because:
1. The ICP (boutique agency, 20–100 units) is priced below WeConnectU breakeven
2. Sales friction is lower — agents can quote without asking "how many units do you have"
3. Revenue is predictable for both Klikk and the customer

Per-unit pricing becomes attractive only at 150+ units where Klikk would leave money on the table under flat-rate. The Enterprise overage structure (`+R50/property above 100`) already addresses this: Enterprise customers pay incrementally as they grow past 100 properties.

### Hybrid option: tiered flat-rate with per-unit overage

The current Enterprise model is already a hybrid:
- Base flat rate (R4,000/month) covers 100 properties / 200 units
- R50/property/month overage above 100

This is the right structure. The only question is whether to introduce a similar overage within the Pro tier (e.g. R50/unit above 100 units). This would capture revenue from Pro customers who are close to or at the 100-unit limit without upgrading to Enterprise. Decision for MC.

---

## 4. Findings Summary and Decision Points for MC

### Finding 1: The rename is low-risk if decoupled from the tier key

The `enterprise` → `Agency` display-name change is a content update, not a code change, if the YAML key is preserved. It requires MC sign-off (DEC-016 explicitly blocked it) and should be evaluated after first-client feedback on tier perception. No code migration needed if we rename the display name only.

**Decision required:** DEC-NNN — "Approve 'Agency' as display name for the Enterprise tier in v1.1?"

### Finding 2: Keep flat-rate for v1.1 — the maths support it

Per-unit billing is not advantageous at the current ICP portfolio sizes (20–100 units). It would either undercut Klikk's margin or destroy the competitive price story vs WeConnectU. Revisit when the customer base includes significant 200+ unit portfolios.

**Recommendation:** No model change in v1.1. Re-evaluate at v2.0 when trust accounting and vacancy advertising are live (those features justify a higher per-unit rate).

### Finding 3: Pro overage is worth evaluating

A light overage on Pro (e.g. R25–R50/unit above 100 units, before requiring Enterprise upgrade) could capture revenue from customers who are at-limit. This is a small revenue lever and low implementation effort.

**Decision required:** DEC-NNN — "Add per-unit overage to Pro tier above 100 units?"

### Finding 4: pricing-research-2026.md does not exist yet

The file `content/sales/pricing-research-2026.md` referenced in the task and in DEC-016 context has not been created. The GTM-010 task that was meant to produce it is presumably not yet complete. This analysis substitutes for that document using direct inspection of `pricing.yaml`, `icp.md`, `demo-script.md`, and `positioning.md`.

**Action:** GTM-010 should produce `content/sales/pricing-research-2026.md`. Until it exists, this document is the authoritative pricing analysis for v1.1.

---

## 5. What changes are blocked on MC sign-off

None of the following should be applied until MC explicitly approves:

1. Any rename of the `enterprise` tier display name
2. Any change to tier pricing amounts
3. Any introduction of per-unit or overage pricing in the Pro tier
4. Any change to the `enterprise` YAML key (requires code migration + feature flag)

This analysis is informational only. `content/product/pricing.yaml` is unchanged.

---

## 6. Suggested DEC tasks for rentals-pm to author

| Question | Blocks |
|---|---|
| Approve "Agency" as display name for Enterprise tier in v1.1? | RNT-QUAL-049 downstream |
| Add per-unit overage to Pro tier above 100 units? | RNT-QUAL-049 downstream |
| Timing: open this review after first-client or after 10 customers? | RNT-QUAL-049 downstream |
