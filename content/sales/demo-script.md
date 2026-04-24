# Klikk Rentals — 15-Minute Demo Script

_For sales reps and product demos. All screens referenced are live in the production app._
_All features cited are BUILT (verified against content/product/features.yaml 2026-04-23)._
_Pricing from `content/product/pricing.yaml`. Flat-rate per organisation — do NOT quote per-unit prices for Klikk. Tier keys: free · pro · enterprise · custom._

---

## Before the call

- Log in to the Klikk admin dashboard (localhost or demo.klikk.co.za)
- Have a property pre-loaded with at least one active lease and one open maintenance job
- Have the tenant mobile app open on your phone (or screen-share a second device)
- Know your prospect's portfolio size before the call — tailor the pricing slide accordingly

---

## Scene 0 — Hook (0:00–1:00)

**What you say:**

"Before I show you the product, let me ask: how long did your last lease take — from the conversation with the tenant to the countersigned PDF in your inbox?"

_[Let them answer. Common responses: 3–5 days, a week, "we still chase people for signatures".]_

"By the end of this demo, you'll have signed a full RHA-compliant lease in under 10 minutes. That's not a future feature — that's what we'll do right now."

**Why it works:** Opens with a concrete, personal pain point. The promise is specific and immediately demoable.

---

## Scene 1 — AI Lease Generation (1:00–4:00)

**Screen:** Admin dashboard → Leases → New Lease → Lease Builder

**What to show:**
1. Open the AI Lease Builder chat
2. Type a natural-language prompt: "Two-year lease for a 2-bed apartment in Stellenbosch. Tenant is Jane Nkosi. Rent R12,500/month payable on the 1st. No pets. Month-to-month after the initial term."
3. AI generates the full lease with merge fields filled in, RHA-compliant clauses, and signature blocks
4. Briefly scroll through the document to show clause structure

**What you say:**
"This is Claude AI generating a fully RHA-compliant lease from that one paragraph. The merge fields are filled in — tenant name, rent amount, property address, payment date. Every clause is checked against the Rental Housing Act. No template hunting. No copy-pasting from last month's lease."

_[Point out the RHA compliance check panel if the prospect is compliance-minded.]_

"You can also edit any clause directly in the TipTap editor, or pull from your own clause library. But for 90% of leases, AI gets it right first time."

**Handles objection:** "Does AI get the clauses right?" → "RHA compliance is built into the prompt engine — the same way a good conveyancer knows which clauses are mandatory, the AI does too. You can always review and edit before sending."

---

## Scene 2 — Native E-Signing (4:00–6:00)

**Screen:** Lease Builder → Submit for Signing → E-Signing Panel

**What to show:**
1. Click "Send for signing" — the system creates signing links for each signer (agent, tenant)
2. Open the tenant signing link on your phone (or second device)
3. Show the document in the signing view: scroll through, click to place signature, sign
4. Return to the admin panel — show the real-time WebSocket update as the signature is confirmed
5. Show the countersigned PDF that is stored automatically

**What you say:**
"The tenant gets a link — no app download, no account required. They sign from their phone, their laptop, anything. You see the completion in real time, right here. By the time you close this tab, the countersigned PDF is already in the system."

_[If the prospect asks about legal validity:]_ "These signatures are legally valid under ECTA section 13 — the same legislation that governs banking and financial e-signatures in South Africa."

**Handles objection:** "Is it legally valid?" → Covered above. Have the ECTA s13 reference ready.

---

## Scene 3 — Document Intelligence (6:00–7:00)

**Screen:** Leases → Upload Existing Lease

**What to show:**
1. Drop in a sample PDF lease (have one ready — an old lease or a template)
2. AI extracts: tenant name, landlord name, rent amount, deposit, term dates, and key clauses
3. Show the extracted data populating the Klikk lease record

**What you say:**
"If you have existing leases on paper or in PDF — and most of our customers do — upload them here. AI reads the document and extracts every field automatically. Your historical tenancies live in Klikk in minutes, not days."

_[This is a brief scene — 60 seconds is enough. The point is "migration isn't painful".]_

---

## Scene 4 — Maintenance Workflow (7:00–10:00)

**Screen:** Admin dashboard → Maintenance → Open a request

**What to show:**
1. Open an existing maintenance request (have one ready with status "Submitted" or "Triaged")
2. Show the AI triage: urgency classification, trade category, AI-generated notes
3. Navigate to Supplier Matching — show the ranked supplier list with match scores
4. Click "Dispatch" to the top-ranked supplier
5. Switch to the Supplier Portal view (admin → Suppliers → [supplier name] → Jobs) — show the job notification

**What you say:**
"Tenant reports a plumbing leak in the tenant app. AI classifies it as urgent, trade: plumbing. It then scores every plumber in your supplier directory against five factors — how close they are, whether they have plumbing as a trade, their price history, whether this owner has a preferred supplier, and their rating. Best match is at the top. One click dispatches them."

_[Show the supplier portal:]_ "The supplier sees the job here — no login required to accept it. They can accept, quote, and confirm availability without a Klikk account. This is how you get suppliers to actually use the system."

_[If the prospect asks about the tenant app:]_ "Let me show you that next."

---

## Scene 5 — Tenant Mobile App (10:00–11:30)

**Screen:** Tenant app on phone (or second device / simulator)

**What to show:**
1. Home screen — show the active lease summary
2. Chat view — send a question like "What is my notice period?" — AI answers using the lease data
3. Issues view — show "Report Issue" (photo attachment, description, submit)
4. Lease view — show the signed lease PDF accessible in-app

**What you say:**
"Tenants have their own app. Not a portal — a real iOS and Android app. They can see their lease, report a maintenance issue with photos, and chat with an AI that knows their property — lease terms, house rules, appliance manuals, maintenance history. The AI answers questions like 'what is my notice period' or 'is the internet included in my rent' based on the actual lease. Tenants stop calling you."

**Handles objection:** "Will tenants actually use it?" → "Tenants use apps every day. What they don't use is a login link in an email that leads to a PDF. The Klikk app is a real app on the App Store. It's as simple as WhatsApp."

---

## Scene 6 — Owner Dashboard + Agent Mobile App (11:30–13:00)

**Screen:** Owner portal (or admin → Owner → [owner name] dashboard)

**What to show:**
1. Owner dashboard: occupancy rate, income this month, open maintenance tickets
2. Brief — 30 seconds is enough

**Then switch to:** Agent app on phone

**What to show:**
1. Dashboard — portfolio summary
2. Viewings — open a booked viewing, show prospect details
3. Viewing calendar

**What you say (owner dashboard):**
"Your owners have a read-only portal. Real-time occupancy, rent received this month, and any open maintenance — without calling you. Owner reporting stops being a task."

**What you say (agent app):**
"Agents have a mobile app too. Book viewings in the field, capture prospect details, see the full calendar. Everything syncs back to the dashboard."

---

## Scene 7 — Pricing and Next Steps (13:00–15:00)

**Screen:** Pricing page or slide — use the relevant tier for their portfolio size

**What you say:**
"Pricing is straightforward. The free tier covers up to 5 properties with no credit card — you can run a real tenancy on it today. Pro is R2,500/month flat — one price for up to 50 properties or 100 units, regardless of your unit count. Enterprise is R4,000/month base and covers 100+ properties with white-label portals and an SLA."

_[For context: WeConnectU charges R150–200/unit. A 100-unit portfolio on WeConnectU costs R15,000–R20,000/month. Klikk Pro is R2,500 flat. You break even against WeConnectU at 17 units. Do not frame Klikk's price as a per-unit rate — it is a flat monthly fee.]_

"There are no setup fees. No per-transaction fees on the base plan. You can start on free today and upgrade when you need to."

**Close:**
"What I'd suggest is this: sign up for free, load two or three of your current properties, and generate a lease. You'll know in 20 minutes whether this works for you. If you want me to sit on that call with you, I can. Otherwise here's the link: klikk.co.za/signup."

---

## Timing cheat sheet

| Scene | Time | Key screen |
|---|---|---|
| 0 — Hook | 0:00–1:00 | None |
| 1 — AI Lease | 1:00–4:00 | Lease Builder chat |
| 2 — E-Signing | 4:00–6:00 | E-Signing panel + tenant link |
| 3 — Document Intel | 6:00–7:00 | Upload existing lease |
| 4 — Maintenance | 7:00–10:00 | Maintenance request + supplier match |
| 5 — Tenant App | 10:00–11:30 | Tenant mobile app |
| 6 — Owner + Agent | 11:30–13:00 | Owner dashboard + agent app |
| 7 — Pricing + CTA | 13:00–15:00 | Pricing slide or page |

---

## Common prospect profiles and demo adjustments

### Boutique PM firm (5–50 units)
- Lead with price: "You are currently paying R[X] on WeConnectU / nothing on spreadsheets."
- Spend more time on lease generation and e-signing — these save the most time for a small team
- Mention the free tier as a low-risk entry point

### Self-managing landlord (1–5 properties)
- Lead with the free tier — no card, start today
- Demo is best done with screen-share; skip the agent mobile app
- Emphasise lease generation and the tenant app (owner retention)

### Estate agency with a rental book (20–150 units)
- Lead with the agent mobile app and viewing scheduler — this is what estate agents care about most
- Emphasise the owner dashboard as a differentiator vs competing agencies
- Use the price comparison: "What does WeConnectU cost your agency today?"

---

## What NOT to demo

The following features are PLANNED and must not be shown as live:
- Trust accounting / deposit management
- TPN tenant screening
- Vacancy advertising (Property24, Private Property integration)
- Incoming / outgoing inspections
- Notice period management
- Deposit refund workflow

If a prospect asks about any of these: "That is on the roadmap. Right now we integrate well alongside PayProp for trust accounting, and TPN screening is coming in v2."
