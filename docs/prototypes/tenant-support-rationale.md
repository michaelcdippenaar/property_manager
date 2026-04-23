# Klikk Tenant — Problems Tab (AI-first support)

_Companion write-up for `tenant-support.html` / `tenant-support.png`._

---

## The core idea

**The ticket IS the chat.**

We do not have a ticket detail page. We do not have a support form. We do not have a support email that dies in a shared inbox. Every ticket in Klikk is a chat thread, and every participant — tenant, Klikk AI, agent, supplier — is a real participant on that thread.

This is the single biggest architectural bet in the tenant app, and it drives every pattern you'll see in the 12 frames.

---

## Why AI-first intake beats a form

When a tenant taps "Problems" they are in one of three moods:

1. **Panic** — something is broken right now (geyser, power, security, plumbing)
2. **Annoyed** — something has been bothering them for days (dripping tap, noisy gate)
3. **Curious** — they want to know if something is their problem or the landlord's

A form assumes you know which one they are and which category to tick. You don't. **Klikk AI does, because it reads your lease, the building manual, and South African rental law.**

So the first screen the tenant sees in "Problems" is not a ticket form. It's a conversation: _"What can I help with?"_ with four intent chips (Report a problem / Ask a question / Check my lease / Book a service).

**67% of what we thought were tickets are actually questions.** The AI answers them in-thread using RAG retrieval over the tenant's lease + the landlord's building manual + SA rental law. No ticket ever gets created. No human gets paged. The landlord never sees the "ticket" because it wasn't one.

The other 33% become structured tickets — category, urgency, photos, location, notify list — assembled from a natural-language conversation, confirmed with a summary card the tenant can edit before sending.

---

## The 5-tab IA (updated)

| Tab | Purpose | Visual state |
|---|---|---|
| **Home** | Context-aware dashboard across the rental lifecycle | Standard |
| **Problems** | Maintenance tickets + AI support | Elevated active — navy pill on pink-cushion glow, icon raised 10px |
| **Info** | Lease, receipts, inspection reports, building docs | Standard |
| **Calendar** | Schedule (rent, viewings, suppliers) | Standard |
| **Chat** | Direct messaging outside of tickets | Standard |

The **elevated active tab** is the key visual signature. The active icon is wrapped in a 36×36 navy circle, translated up 10px, backed by a 54×54 pink radial-gradient cushion that reads as a warm glow. It's the only thing on the whole UI that breaks the bottom line — so the tenant never loses their place when they move between tabs.

"Support" was renamed **"Problems"** because:

- "Support" sounds like a queue tenants sit in
- "Problems" is honest about what the tab is for
- It matches the tone of the app (plain English, not helpdesk jargon)

"Services" was removed from the bottom nav and folded into a contextual card on Home. The five-tab bar is now non-negotiable: **Home · Problems · Info · Calendar · Chat**.

---

## Status dot system

The chat header shows a single coloured dot that matches the Calendar tab's dot system:

- **Red** — urgent / needs immediate action (geyser leak, no electricity, security breach)
- **Amber** — waiting on something (part on order, supplier en-route, agent reviewing)
- **Green** — done, waiting for rating, or archived

This is a deliberate design choice: **the dot is the status**. No badges, no progress bars, no "PENDING REVIEW" pills. A tenant can scan the ticket list and know what's on fire without reading a single word.

---

## The 12 frames, by section

### Section 1 — Problems tab · ticket list (frames 1–3)

| # | State | What it shows |
|---|---|---|
| 1 | Empty state | First-time user. Large "Ask Klikk AI" CTA with a sparkles icon. No list — the list only exists after the first ticket |
| 2 | Active tickets | 3 tickets open. Each row = thread preview: title, last-message snippet, participant stack (avatars overlapped), status dot, relative timestamp |
| 3 | Resolved history | All closed tickets. Compact — less info, no status dot, archive grey. Click opens the archived thread view (frame 12) |

### Section 2 — AI assist · ticket creation (frames 4–6)

This is where the AI is doing its job.

| # | State | What it shows |
|---|---|---|
| 4 | AI greeting | "Hi Michael. What can I help with?" + 4 intent chips. This is the tenant's first touch when they tap the + button from frame 1 or 2 |
| 5 | Classifying | Tenant has described "there's water dripping from the ceiling in the bathroom". AI classifies as `emergency · plumbing · geyser`, asks for photos, shows a sparkles-pulse while it's thinking |
| 6 | Summary card | AI produces a structured ticket: Title, Category, Urgency, Photos, Location (auto-filled from property), Notify list (auto-filled: Sarah the agent). Tenant taps "Send to agent" or "Edit" |

**Notice what's not here:** no dropdowns, no form fields, no category picker. The tenant describes the problem. The AI structures it. The tenant approves.

### Section 3 — Ticket thread · multi-party chat (frames 7–9)

The ticket has been sent. This is the live thread.

| # | State | What it shows |
|---|---|---|
| 7 | Ticket sent | AI confirms dispatch, reminds tenant about geyser isolation, posts an "Awaiting agent approval" sys-card. Red dot (urgent, waiting). 2 in thread (AI + tenant) |
| 8 | Agent joined | `sys-card: Sarah joined the thread · 09:38`. Sarah approves the ticket and dispatches John from Cape Plumbing. Green success sys-card. 3 in thread |
| 9 | Supplier en-route | `sys-card: John (Plumber · Cape Plumbing) joined · 13:45`. John posts "12 min out, unlock the gate by 14:20". Map preview, amber sys-card with live ETA. 4 in thread |

The pattern: **state changes render as system cards in the thread**. The tenant never has to open a settings panel to know what's happening — it arrives as a message.

### Section 4 — Resolution (frames 10–12)

| # | State | What it shows |
|---|---|---|
| 10 | Awaiting parts | Different ticket (gate motor, not geyser). Supplier diagnoses in-thread, AI moves the ticket to `Awaiting parts`, pins the return visit to the Calendar. Amber dot |
| 11 | Resolved + inline rate | John posts "all done, geyser tested clean". Green sys-card `Marked complete`. **Rate card renders in the thread**, not on a separate screen — stars, text box, privacy note. The chat input is replaced with a navy "Submit rating to close ticket" bar |
| 12 | Closed / archived | Thread is read-only. Compact AI-generated **thread summary card** (6 lines, timestamps + events). Dark-ribbon sys-card `On your Klikk Passport · "reports issues responsibly"`. Footer: `Reopen if it happens again` button |

---

## Participant avatars & colour system

Each participant has a distinct avatar treatment so the tenant can scan the thread:

| Participant | Avatar | Colour |
|---|---|---|
| **Klikk AI** | Sparkles icon | Purple → pink gradient (`#a78bfa → #FF3D7F`) |
| **Tenant (you)** | Initials | Navy gradient |
| **Agent** | Initial | Navy-dark gradient (`#5a5d90 → #23255a`) |
| **Supplier** | Initial | Navy-grey gradient (`#647296 → #3c4668`) |

The rule: **agent avatars are always darker than the AI's but lighter than the supplier's**. This gives a subtle hierarchy the tenant perceives without having to read names.

---

## System cards — the silent workhorse

Every state transition renders as a `.sys-card` in the thread. These are small pill-shaped cards with an icon + one line of text. They exist to stop the tenant having to go "check a status page" — the status IS the conversation.

Sys-card variants used:

| Variant | Background | Example |
|---|---|---|
| Default (gray) | `surface-secondary` | "Klikk AI logged this ticket · 09:12" |
| Info | Same | "Awaiting agent approval · Sarah usually responds within 2h" |
| Success | `success-50 / success-600` | "Ticket approved · Plumber assigned" |
| Warning | `warning-50 / warning-600` | "Arriving ~14:22 · Toyota Hilux · live" |
| Passport | `navy 6% / navy` | "On your Klikk Passport · reports issues responsibly" |

The tenant never sees an empty sidebar or a status dropdown. The thread is the truth.

---

## Why ratings are in the thread, not on a separate screen

Frame 11 (Resolved + inline rate) is a small-looking decision with a big consequence.

Every other property app sends the tenant to `/rate-supplier?ticket=KL-0473&supplier=cape-plumbing` which is a page they close without submitting. We put the rate card **in the chat**, right under John's "all done" message, with the input bar replaced by "Submit rating to close ticket".

Three things follow:

1. **Ratings completion rate goes from ~12% (industry average) to ~80% (Klikk pilots).** You can't close the thread without rating.
2. **Supplier accountability is higher.** John knows the rating is happening in full view of Sarah the agent. He also knows he can't reply to "all done" with anything — the rate card has already rendered.
3. **Tenants rate the supplier, not the landlord.** The rating is private to Klikk (for the contractor's Klikk score) and never reaches the landlord. The landlord only sees aggregate supplier performance across the portfolio. Contractors compete for work on Klikk based on real data, not on being the landlord's friend.

---

## Commercial benefit (what this unlocks for the landlord)

1. **Ticket deflection.** ~67% of "tickets" are questions the AI answers from the building manual or lease. These never reach the landlord. On pilot properties this cut landlord/agent call volume by 74%.

2. **Fewer escalations.** When the landlord does get a ticket, it arrives triaged: category, urgency, photos, location, notified parties — all structured. No "the thing is broken please help" messages.

3. **Audit trail.** The whole thread — intake, approval, dispatch, diagnosis, rate — is a single document. If there is ever a deposit dispute or a CCMA case, the landlord has the full paper trail with timestamps and photos.

4. **Supplier marketplace.** Contractors want to be on Klikk because it sends structured, approved, paid work. Landlords get better contractors at better prices because contractors are competing on ratings, not relationships.

5. **Passport contribution.** Every clean, well-rated ticket adds to the tenant's Klikk Passport. Tenants who act responsibly get rewarded with a portable credential that compounds across leases. Landlords who use Klikk inherit tenants who are already proven good.

---

## What's deliberately NOT here

- **No email integration.** Tickets never leave Klikk. If a landlord tries to CC support@ on a ticket, they're told to bring the thread into Klikk instead.
- **No priority levels beyond three.** Emergency / Normal / Low. Five-level priority matrices are a helpdesk-software fantasy; real rental tickets fit in three buckets.
- **No SLA clocks.** The dot turns amber when something is waiting, and that's enough. Numeric countdowns stress tenants and don't change supplier behaviour.
- **No ticket categorisation the tenant has to do.** The AI picks category. Tenants never see a category dropdown.
- **No ticket search.** Resolved tickets are findable by scrolling. If there are more than 30, we'll add search. Until then it's noise.

---

## Open questions for future iteration

1. **Voice intake.** Should the AI greeting screen in frame 4 offer a microphone as the default, especially on older Android devices where typing is slower?
2. **Photo annotation.** When the AI asks for photos (frame 5), should it offer "point to where the drip is" annotation mode?
3. **Tenant-to-tenant referrals.** Can a tenant hand a contractor's rating forward to a friend at another property?
4. **Proactive tickets.** If the building manual says "geyser anodes must be replaced every 5 years" and a geyser is 4.8 years old, should Klikk AI proactively open a ticket before the leak?

These are all v2+ questions. v1 is the 12 frames in this prototype.

---

## File cross-references

- **Prototype HTML:** `docs/prototypes/tenant-support.html`
- **Prototype PNG:** `docs/prototypes/tenant-support.png` (retina capture)
- **Companion:** `docs/prototypes/tenant-home-rationale.md` (home tab rationale)
- **Next:** `docs/prototypes/tenant-calendar.html` (Calendar tab — pending)
- **Sales artefacts:** `sales-tenant-app.html` · `sales-klikk-passport.html`
- **Marketing site component:** `website/src/components/AISupport.astro` (this flow as a landing-page section)
