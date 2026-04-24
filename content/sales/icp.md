<!--
  KLIKK RENTALS — IDEAL CUSTOMER PROFILE (ICP)
  Authoritative pricing source: content/product/pricing.yaml
  All prices are flat-rate per organisation per month (not per-unit).
  Tier keys: free · pro · enterprise · custom
  DEC-016 locked 2026-04-24: freeze pricing.yaml as-is for v1.0.
-->

# Klikk Rentals — Ideal Customer Profile

_All budget ranges reference flat-rate pricing from `content/product/pricing.yaml`. Do not use per-unit pricing in sales conversations — Klikk charges per organisation, not per unit._

---

## Primary ICP — Boutique Rental Agency

**Profile:** Independent residential property management firm, 2–10 agents, managing 20–100 units in South Africa.

**Pain points:**
- Lease drafting is manual, slow, and legally risky (copy-paste from last month's lease)
- E-signing is not native — using DocuSign or paper-based, which adds days to every tenancy
- Maintenance co-ordination happens on WhatsApp with no audit trail
- Owners call constantly for updates — no self-service portal
- Tenant queries (lease terms, notice periods, appliance issues) land in the agent's inbox

**Why Klikk wins:**
- AI lease generation eliminates the most time-intensive task in the rental cycle
- Native ECTA-compliant e-signing with real-time WebSocket tracking
- AI maintenance triage + supplier matching replaces WhatsApp chains
- Owner and tenant portals reduce agent interruptions

**Budget:**
- Portfolio of 20–50 units: **Pro R2,500/month flat** — one price covers the whole portfolio up to 50 properties or 100 units
- Portfolio of 51–100 units: still **Pro R2,500/month flat** (Pro covers up to 100 units)
- Growth path: **Enterprise R4,000/month base** when portfolio exceeds 100 properties or 200 units

**Decision maker:** Agency principal or director
**Sales motion:** 15-minute demo → free trial → upgrade at portfolio milestone
**Objection map:** See `content/sales/objections.md`

---

## Secondary ICP — Self-Managing Landlord

**Profile:** Individual owner managing 1–5 properties without a rental agent.

**Pain points:**
- Uses a lawyer or conveyancer to draft leases — expensive and slow
- Paper-based or email-and-scan e-signing
- No tenant communication layer — tenants WhatsApp or call directly

**Why Klikk wins:**
- Free tier covers up to 5 properties with no credit card
- AI lease generation replaces the lawyer for standard residential leases
- Tenant mobile app gives tenants a self-service channel (maintenance, lease, chat)

**Budget:**
- **Free tier (R0/month)** — up to 5 properties, 2 AI-generated leases/year, bring-your-own LLM key
- Upgrade path: **Pro R2,500/month flat** when portfolio grows past 5 properties

**Decision maker:** Property owner
**Sales motion:** Organic signup → self-serve → upgrade on portfolio trigger
**Objection map:** See `content/sales/objections.md`

---

## Tertiary ICP — Estate Agency with Rental Book

**Profile:** Estate agency with a hybrid sales + rental portfolio, 5–20 agents, managing 50–200 units alongside a sales pipeline.

**Pain points:**
- Rental management is a revenue stream but not the core focus — agents are generalists
- Owner retention depends on owner dashboard quality
- Field agents need mobile-first tooling for viewings and prospect capture

**Why Klikk wins:**
- Agent mobile app built for field operations — viewings, prospect capture, portfolio overview
- Owner dashboard gives landlords real-time visibility, reducing agent interruption
- API + MCP server allows integration into existing CRM or accounting stack

**Budget:**
- Rental book 50–100 units: **Pro R2,500/month flat**
- Rental book 100+ units: **Enterprise R4,000/month base** (+ R50/property above 100)

**Decision maker:** Principal or rental division head
**Sales motion:** Demo → pilot on rental division only → expand

---

## Out-of-ICP (do not target for v1.0)

- Large franchise groups (WeConnectU territory — trust accounting is a blocker)
- Body corporate / community scheme managers (not in product scope)
- Commercial property managers (residential RHA only)
- Tenants (inbound channel, not sales target)
