# Klikk Rentals — Top 10 Objections and Responses

_For sales conversations, demos, and email follow-ups._
_All responses reference only BUILT features (verified against content/product/features.yaml 2026-04-23)._
_Pricing from content/product/pricing.yaml._

---

## How to use this document

Each objection is paired with a short acknowledgement, a direct response, and a supporting proof point or bridge. Responses are honest — they do not over-promise, and they acknowledge real gaps where they exist.

---

## Objection 1 — "You don't have trust accounting."

**Type:** Feature gap

**Acknowledgement:** "You're right — trust accounting is not in Klikk today."

**Response:**
"Trust accounting is on our roadmap for v2. In the meantime, Klikk is designed to sit alongside PayProp or your existing trust account provider — we handle everything except the trust account itself: lease generation, e-signing, maintenance, tenant communication, owner reporting, and rent tracking. Most of our customers run Klikk and PayProp together without friction.

If trust accounting is a hard requirement before you can switch, I'll be straight with you: wait for v2, or run both systems in parallel. We don't want you to choose us and then find a gap."

**Proof point:** "Rent tracking in Klikk generates unique payment references per tenant and flags arrears automatically — that feeds clean data into whatever trust account system you use."

---

## Objection 2 — "I've never heard of Klikk."

**Type:** Trust / vendor risk

**Acknowledgement:** "We are a new name in the market — that's fair."

**Response:**
"Klikk was built by a landlord managing real properties in South Africa. Every feature in the product exists because it solved an actual problem. It's not a startup that raised money and hired a product team to imagine what landlords need — it's software that has been running on live tenancies.

The platform is in production today. You can sign up for free, load a property, and generate a real lease this afternoon without giving us a credit card. That is the fastest way to evaluate whether it does what it says."

**Proof point:** "The free tier covers up to 5 properties. There is nothing to lose by trying it."

---

## Objection 3 — "The price is too high."

**Type:** Cost

**Acknowledgement:** "R2,500/month is real money — let's make sure the comparison is fair."

**Response:**
"WeConnectU charges R150–200/unit. If you are managing 20 units, that's R3,000–R4,000/month for a product with no AI and no tenant app. Klikk Pro is R2,500/month flat for up to 50 properties or 100 units.

If you have fewer than 5 properties, the free tier is R0/month with no credit card required.

If you're currently on spreadsheets, the question isn't whether R2,500/month is expensive — it's whether the time you spend on lease drafting, maintenance co-ordination, and tenant chasing is worth more than R2,500/month. For most agents it is."

**Proof point:** Break-even vs WeConnectU is 17 units. Pro vs WeConnectU at 100 units: R2,500 vs R15,000–R20,000/month.

---

## Objection 4 — "We are already on WeConnectU / PayProp / [competitor]."

**Type:** Switching cost / incumbent

**Acknowledgement:** "Switching costs are real — I don't want to pretend otherwise."

**Response:**
"A few things to consider. First, what is it costing you? WeConnectU is R150–200/unit. PayProp is payments-only — it does not do leases, maintenance, or tenant communication. If you're using PayProp for payments and nothing else for everything else, there's a gap Klikk fills directly.

Second, Klikk's document intelligence lets you upload your existing PDF leases and extract all the data automatically. Migration is not a manual exercise.

Third, you do not have to rip and replace on day one. Many customers run Klikk alongside an existing trust account provider. Start with lease generation and e-signing, prove the value, then migrate the rest."

**Proof point:** Document Intelligence (BUILT) — upload existing leases, AI extracts tenant name, dates, rent, clauses.

---

## Objection 5 — "AI gets things wrong. I can't trust it with legal documents."

**Type:** AI scepticism

**Acknowledgement:** "AI scepticism is healthy — you should verify what it produces."

**Response:**
"The AI in Klikk is not generating free-form text and hoping for the best. The lease builder works from a structured RHA-compliant clause library. AI fills in merge fields and selects clauses based on your inputs — it is not writing clauses from scratch.

You review every lease before it is sent for signing. If anything is wrong, you edit it in the TipTap editor. The AI does the 90% that is repetitive; you verify the 10% that is judgment.

Practically: the AI gets the standard clauses right every time because they are pre-written. The risk is in unusual situations — non-standard properties, complex tenancy arrangements. In those cases, treat the output as a first draft that you review, not a finished document."

**Proof point:** TipTap Template Editor (BUILT) — full WYSIWYG editing before any document leaves the system.

---

## Objection 6 — "Will tenants actually use the app?"

**Type:** Adoption risk

**Acknowledgement:** "Tenant adoption is a legitimate concern — a tool no one uses is not a tool."

**Response:**
"The Klikk tenant app is a native iOS and Android app on the App Store. It is not a portal link in an email. Tenants invite themselves via a registration link when you send a lease — the process is: lease sent → tenant registers → tenant signs in app → tenant has the app installed.

Two features drive retention: the AI chat (tenants ask questions about their lease without calling you) and maintenance reporting (photos, status tracking, real-time updates). Tenants use apps that save them effort. Klikk does that.

If a tenant absolutely refuses to use an app, they can still sign via the e-signing web link on any browser. The app is better, but it is not mandatory."

**Proof point:** Tenant Mobile App (BUILT) — iOS and Android; AI tenant chat with property-scoped knowledge base.

---

## Objection 7 — "We need TPN tenant screening."

**Type:** Feature gap

**Acknowledgement:** "TPN screening is not in Klikk today."

**Response:**
"TPN integration is on the roadmap for v2. In the meantime, you can run TPN checks directly on the TPN portal and attach the screening report to the tenant record in Klikk manually. It is a manual step, but the data lives in the right place.

If TPN integration is a dealbreaker before signing up, I'll tell you honestly: it is coming, but I cannot give you a firm date. Start on the free tier, use Klikk for leases and maintenance today, and the screening integration will be there when it ships."

---

## Objection 8 — "We need it to integrate with our accounting software (Xero / Sage / QuickBooks)."

**Type:** Integration concern

**Acknowledgement:** "Accounting integration is important — I want to be straight with you about where we are."

**Response:**
"Klikk has a REST API and an MCP server available on Pro and Enterprise plans. A developer can build an integration to any accounting system using the API today.

Native out-of-the-box connectors to Xero, Sage, and QuickBooks are planned — they are not live yet. If you need a point-and-click Xero sync today, Klikk is not the right fit on its own. If you have a developer or are comfortable with a lightweight API integration, we can talk about what that looks like.

What Klikk does today: generates unique payment references per tenant, tracks rent received, and flags arrears — that data is accessible via API and can be pushed to your accounting system."

**Proof point:** Klikk MCP Server + REST API (BUILT) — available on Pro tier.

---

## Objection 9 — "We are a large agency — is this built for us?"

**Type:** Scale / enterprise fit

**Acknowledgement:** "The product was initially designed for boutique PM firms and landlords, so your question is fair."

**Response:**
"Enterprise tier is R4,000/month base and covers 100+ properties with white-label portals, on-premises or cloud hosting, POPIA-compliant dedicated data storage, an SLA guarantee, and a dedicated account manager. User add-ons are role-based: Viewer R50/mo, Agent R90/mo, Admin R150/mo — you pay only for the roles you need.

What Klikk does not yet have for large agencies: trust accounting, TPN screening in-platform, and multi-portal vacancy advertising. If those are non-negotiable today, we should have an honest conversation about timeline before you commit.

What large agencies consistently value: the agent mobile app (field operations), the owner dashboard (owner retention), and the AI lease generation speed (throughput). If those are your primary pain points, we are a strong fit."

**Proof point:** Enterprise tier in pricing.yaml — white-label, on-premises/cloud, POPIA storage, SLA.

---

## Objection 10 — "Why should I trust a new SA vendor over an established one?"

**Type:** Vendor credibility / longevity risk

**Acknowledgement:** "Vendor longevity is a real consideration — you're embedding a platform into your operations."

**Response:**
"Two things I can say honestly. First, the product is in production and running on live tenancies today — this is not a demo environment. Second, the free tier means you can evaluate the platform on real properties without financial commitment. If Klikk ever shuts down, you lose the tooling — not your data. Leases are stored as PDFs, tenant data is exportable, and there are no proprietary lock-in formats.

On the 'new vendor' risk: established SA vendors like WeConnectU have been around longer. They also have no AI, no tenant mobile app, and charge three to eight times more per unit. The question is whether the risk of a newer vendor is higher than the cost of staying on a product that is not evolving.

We are transparent about what is built and what is planned. The gap list is in our positioning document and in every sales conversation we have. That is the kind of vendor you want — one that tells you what is not there, not just what is."

**Proof point:** Positioning.md gap transparency table — every PLANNED feature documented honestly.

---

## Quick-reference objection map

| Objection | Category | Key response theme |
|---|---|---|
| No trust accounting | Feature gap | Honest gap; pair with PayProp; v2 roadmap |
| Never heard of Klikk | Trust | Built by a landlord; free tier to evaluate |
| Too expensive | Cost | WeConnectU comparison; break-even at 17 units |
| Already on [competitor] | Switching cost | Document intelligence for migration; phased approach |
| AI gets things wrong | AI scepticism | Clause library + review workflow; not free-form |
| Tenants won't use the app | Adoption | Native app vs portal link; chat + maintenance retention drivers |
| Need TPN screening | Feature gap | Honest gap; manual workaround; v2 roadmap |
| Need accounting integration | Integration | API available today; native connectors planned |
| Large agency fit | Scale | Enterprise tier; honest about trust accounting / TPN gaps |
| New vendor risk | Credibility | Production today; free tier; no lock-in; transparent gap list |
