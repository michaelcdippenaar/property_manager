# Klikk Tenant Mobile App — Purpose & Screen-by-Screen

_Companion write-up for `tenant-home.html` / `tenant-home.png`._

## Why a mobile app at all?

A lot of property management can live on a mobile website. So the question isn't "do tenants need an app" — it's **"what justifies forcing an install?"**

Three reasons:

1. **Maintenance is the killer feature.** When the geyser bursts on a Sunday night, tenants need to photograph the damage, send it instantly, and see the plumber's ETA. That's camera + push notifications + location — all native. A mobile website cannot compete here.
2. **Push notifications replace WhatsApp chaos.** Today landlords and tenants exchange rent reminders, load-shedding alerts, water outages, and body corporate notices on WhatsApp. An app consolidates this into a managed channel the landlord controls, with receipts and audit trails.
3. **The Klikk Passport is a portable credential.** A tenant's payment history, landlord references, and verified ID should travel with them to the next lease. This only works if the tenant carries it in a wallet-like app on their phone — not a website they forget exists 3 months after moving in.

**What doesn't belong in the app:** uploading PDFs, long forms, lease signing (redirect to web), document review. Those are better on a 13" screen.

---

## The core IA — 5 tabs + a dynamic Home

| Tab | Purpose | Why it's a tab |
|---|---|---|
| **Home** | Context-aware dashboard that changes across the rental lifecycle | The most-visited screen; what they came for today |
| **Support** | Maintenance tickets — log, track, chat with landlord/contractor | Killer feature. Native camera, native notifications |
| **Calendar** | Notice board — rent due, inspections, load-shedding, body-corp notices | Replaces 40+ WhatsApp messages a month |
| **Chat** | Direct line to landlord or agent | Faster than email, permanent thread, POPIA-safe |
| **Services** | Marketplace — internet, insurance, cleaning, moving | Monetisation + tenant convenience |

---

## Home — the 11 lifecycle states

This is the core design insight. **Home is not one screen — it's 11 states** driven by where the tenant is in the rental cycle. Same tab, same IA, radically different content.

### 1. Onboarding (14 days before move-in)
Countdown + checklist: "Lease signed ✓, Deposit paid ✓, Set up debit order ◯, Contents insurance ◯, Transfer utilities ◯". This is the highest-anxiety moment of renting — the app replaces 15 emails with a single progress view.

### 2. Just moved in (first 30 days)
"Finish move-in inspection — 5 days left to flag anything." Reminds the tenant to log snags before the deposit clock starts. This single screen saves landlords from "the dent was already there" disputes at move-out.

### 3. Settled (month 2 through pre-renewal)
The "quiet state." Rent status, active tickets, unread messages, this week's calendar items, and a **Passport peek card** ("14 months on-time · 4.8 landlord rating") to remind the tenant their record is building value.

### 4. Pre-renewal (90 → 60 days before lease end)
"Your lease ends 14 July 2026 — 87 days, what's next?" Two radio options: *I want to renew* / *I'm thinking of moving*. This is the decision moment that drives retention — or triggers the Apply Elsewhere flow.

### 5. Renewal offered (landlord has proposed terms)
Side-by-side comparison of current vs new rent, escalation %, term. Acts on the offer in 2 taps. Replaces landlords chasing tenants for a reply.

### 6. Renewing (accepted, awaiting signing)
Progress indicator: offer accepted → landlord countersigned → signed copy ready. Same aesthetic as the onboarding checklist — closes the loop cleanly.

### 7. Giving notice (30+ day statutory notice period)
The tenant has committed to leaving. Screen switches to move-out mode: move-out inspection booking, final meter readings, forwarding address, deposit account details.

### 8. Moving out (final 14 days)
Keys handover date, cleaning checklist, utilities to close, outstanding items ("You still owe 1 month rent"). High-tension moment — app keeps it un-emotional.

### 9. Deposit pending (post-move-out, 7-21 days per RHA)
"Your deposit is being reconciled — landlord has 14 days to return it (RHA s5(3)(i))." Shows the legal clock ticking. Builds trust by citing the law.

### 10. Alumni (post-move-out, record retained)
Home becomes a **history view**. "3 properties · 4 years · R487,000 paid on time". This is the Passport in its fullest form — a tenant's portfolio of tenancies, portable to the next landlord.

### 11. Applying (to a new property)
The Apply Elsewhere flow: browse listings → one-tap apply (Passport auto-fills references, FICA, ID) → submitted. This is the network-effect moat: once a tenant has a verified Klikk Passport, they will prefer Klikk-listed properties.

---

## The Klikk Passport — accessed via the avatar, any time

Tapping the tenant's avatar from any screen opens the Passport: verified ID, FICA status, current tenancy, on-time payment record, landlord references (stars + short quotes), and a "Share with a landlord" button that generates a POPIA-compliant, time-limited link.

**Landlord-view of Passport** (the link recipient sees): Photo, verified badge, tenancy history with star ratings, no raw financial data — just a trust score. Think "LinkedIn for tenants," but privacy-first.

---

## Why this wins commercially

- **Tenant retention** — the Pre-renewal and Renewal Offered states directly combat lease churn. Every renewed tenant saves the landlord ~R15k in vacancy + ad + viewings costs.
- **Moat via Passport** — once 10,000 tenants have a Klikk Passport, a new landlord listing on Klikk pre-qualifies applicants 10x faster than rivals (PayProp, Red Rabbit don't have this). This is a network effect competitors cannot copy without starting from zero.
- **Services marketplace** — captive monetisation. A tenant needs internet, contents insurance, a cleaner, a mover. Klikk takes a referral fee on each.
- **Audit trail for disputes** — every ticket, message, inspection photo, notice is timestamped and POPIA-logged. When disputes hit the Rental Housing Tribunal, the landlord has the file already built.

---

## What the 17 prototype frames show (in `tenant-home.png`)

**Row 1 (3 frames):** Onboarding → Just moved in → Settled — lifecycle states 1–3
**Row 2 (3 frames):** Pre-renewal → Renewal offered → Renewing — lifecycle states 4–6
**Row 3 (3 frames):** Giving notice → Moving out → Deposit pending — lifecycle states 7–9
**Row 4 (2 frames):** Alumni → Applying (entry) — states 10–11
**Row 5 (4 frames):** Passport (tenant view) → Passport (landlord view) → Apply browse → Apply detail
**Row 6 (2 frames):** Apply confirm → Apply submitted

Each frame is the **Home tab only** — the four other tabs (Support, Calendar, Chat, Services) are not yet prototyped.

---

## Next prototypes to build

1. **Support (maintenance) tab** — the killer feature. Ticket list, new ticket with camera, ticket detail with chat + contractor ETA.
2. **Calendar tab** — month view + agenda view, filter by type (rent, inspection, load-shed, body-corp).
3. **Chat tab** — thread list, landlord/agent conversation, attachment support.
4. **Services marketplace** — category grid, vendor detail, quote-request flow.
