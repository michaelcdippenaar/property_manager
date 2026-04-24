<!--
  KLIKK RENTALS — COMPETITIVE MATRIX
  Authoritative pricing source: content/product/pricing.yaml
  Pricing model: FLAT-RATE per organisation — not per-unit.
  Klikk does not have per-unit pricing. Competitor per-unit prices are shown
  as a contrast point to illustrate Klikk's pricing advantage.
  Tier keys: free · pro · enterprise · custom
  DEC-016 locked 2026-04-24.
-->

# Klikk Rentals — Competitive Matrix

_Klikk pricing is flat-rate per organisation (from `content/product/pricing.yaml`). Competitor per-unit figures below are their pricing models, not Klikk's — shown as a contrast point only._

---

## Pricing model comparison

| Platform | Pricing model | Entry price | 20-unit cost/mo | 100-unit cost/mo |
|---|---|---|---|---|
| **Klikk Free** | Flat-rate / org | R0 | R0 (≤5 props) | — |
| **Klikk Pro** | Flat-rate / org | R2,500/mo | R2,500 flat | R2,500 flat |
| **Klikk Enterprise** | Flat-rate base + per-property above 100 | R4,000/mo base | — | R4,000 flat |
| WeConnectU | Per-unit (est.) | Custom quotes | ~R3,000–R4,000 | ~R15,000–R20,000 |
| PropWorx | Per-user licence | R795/user/mo | Varies by team size | Varies by team size |
| reOS | % of transactions | R0 subscription | ~R880 (0.55%) | ~R4,400 (0.55%) |
| MRI Rentbook | Freemium + per-lease | R0 (≤20 props) | R0 | Pay-per-lease |
| PayProp | % of volume + licence | R434/mo + fees | R434 + % | R434 + % |

_WeConnectU per-unit estimate based on market intelligence (2026-04-14). Not publicly disclosed — must book demo._

---

## Feature comparison — primary SA competitors

| Feature | Klikk | WeConnectU | PayProp | PropWorx | reOS | Talozen |
|---|---|---|---|---|---|---|
| AI lease generation | Yes (Claude API) | No | No | No | No | No |
| Native e-signing (ECTA s13) | Yes | No | No | No | No | Yes |
| Tenant mobile app | Yes (native) | No | No | No | No | No |
| Agent mobile app | Yes (native) | No | No | No | No | No |
| Owner portal | Yes | No (unconfirmed) | Passive | Yes | No | Yes |
| Supplier portal | Yes | Yes (RedRabbit) | No | Partial | No | No |
| AI maintenance triage | Yes | No | No | No | No | No |
| AI tenant chat (RAG) | Yes | No | No | No | No | No |
| Trust accounting | Roadmap (v2) | Yes | Yes (core) | Yes | Yes | No (PayProp) |
| TPN screening | Roadmap (v2) | Yes | Via TPN | Yes | Via TPN | No |
| Lease management | Yes | Yes | No | Yes | Partial | Yes |
| REST API + MCP | Yes (Pro+) | No | Yes (API) | No | Yes (API) | No |
| POPIA compliant | Yes | Yes | Yes | Yes | Yes | Yes |
| Flat-rate pricing | Yes | No | No | No | No | No |
| SA-built | Yes | Yes | Yes | Yes | Yes | Yes |

---

## Positioning axis

**X-axis:** Generative AI capability (none → full LLM-native)
**Y-axis:** SA compliance depth (none → RHA + ECTA + POPIA native)

```
High SA compliance
        |
PayProp |            WeConnectU   PropWorx
        |
        |                              Talozen    KLIKK ← top-right
        |
        |
Low     +----------------------------------------→ High AI
        No AI                              Generative AI
```

Klikk occupies the top-right quadrant uniquely: the only SA-built platform with both deep RHA/ECTA compliance AND generative AI.

---

## Key differentiators to lead with

1. **Generative AI** — No SA competitor has LLM-powered AI. AppFolio (US) has predictive AI only. Klikk uses Claude API for lease writing, tenant chat, and document parsing.
2. **Native e-signing** — Only Klikk and Talozen in SA have native e-signing. Talozen relies on third-party integrations; Klikk is self-contained (Gotenberg).
3. **Flat-rate pricing** — Klikk Pro is R2,500/month regardless of unit count (up to 100 units). Every SA competitor charges per-unit, per-user, or % of volume. Break-even vs WeConnectU: 17 units.
4. **Four purpose-built apps** — Tenant app, agent app, owner portal, supplier portal in one platform. No SA competitor has a native tenant mobile app (MRI Rentbook has limited mobile only).

---

## Honest gaps — where competitors beat Klikk today

| Gap | Best competitor | Klikk plan |
|---|---|---|
| Trust accounting | PayProp (market leader) | v2 roadmap |
| TPN screening | TPN / PropWorx | v2 roadmap |
| Vacancy advertising | Prop Data / Entegral | v2 roadmap |
| Inspections | WeConnectU (RedRabbit) | v2 roadmap |
| Accounting write-back | PropWorx / reOS | API today; native connectors v2 |

_Full competitor intelligence: `content/competitive/competitors.yaml`_
