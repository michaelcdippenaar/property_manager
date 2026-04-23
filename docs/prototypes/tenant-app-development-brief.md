# Klikk Tenant App — Development Brief

_Feeding the dev agent. Covers the Problems and Calendar tabs end-to-end._

**Source prototypes:**
- `docs/prototypes/tenant-support.html` → `tenant-support.png` (12 frames)
- `docs/prototypes/tenant-calendar.html` → `tenant-calendar.png` (9 frames)
- PNG copies for web hosting: `website/public/prototypes/tenant-support.png` · `tenant-calendar.png`

**Companion rationale:**
- `docs/prototypes/tenant-support-rationale.md` (design decisions for Problems tab)

---

## 1. What the app is

The Klikk Tenant app is a mobile-first React Native / Flutter app (current target: Flutter, `mobile/` or `tenant_app/` in the monorepo) used by **residential tenants in South Africa**. It is a companion to the Klikk admin platform used by landlords, letting agents, and contractors.

The app's job is to make the tenant's side of a rental relationship feel like a coherent, low-anxiety stream rather than a filing cabinet. Every screen answers one of three questions:

1. **What's happening now?** (Home, Calendar)
2. **What do I do about this problem?** (Problems)
3. **Where's the paperwork?** (Info, Chat)

The prototypes in this brief cover the two most load-bearing tabs: **Problems** (all maintenance/support) and **Calendar** (the rhythm of the rental).

---

## 2. Design system foundations

### 2.1 Colour tokens (copy these into the tenant app's theme)

| Token | Value | Purpose |
|---|---|---|
| `navy` | `#2B2D6E` | Brand primary; active state, titles, CTAs |
| `navy-dark` | `#23255a` | Gradient end stop |
| `navy-light` | `#3b3e8f` | Chat-quote accent |
| `accent` | `#FF3D7F` | Klikk pink; elevated-tab cushion, primary CTAs |
| `accent-light` | `#FF6B9D` | Hover/secondary accent |
| `surface` | `#F5F5F8` | App background |
| `surface-secondary` | `#F0EFF8` | Cards on surface, sys-card bg |
| `success-600` | `#0d9488` | Green dot / "done" |
| `warning-600` | `#d97706` | Amber dot / "waiting" |
| `danger-600` | `#dc2626` | Red dot / "urgent" |
| `info-600` | `#2563eb` | Info banners only |
| `gray-100..900` | standard Tailwind | Text + dividers |

### 2.2 Typography

The prototype uses **Fraunces** for display (Georgia fallback) and **DM Sans** for body. In the shipped Flutter app, substitute:

- Display → **Fraunces** (Google Fonts) or **Crimson Pro** / **Playfair** as safe fallbacks. The feel is "editorial serif with a warm curve", not corporate sans.
- Body → **DM Sans** (Google Fonts) at 13–15 px.
- Numerals that represent money or live data (rent amount, countdown) → display font weight 500.

Base font size is **15 px** (not 16). This matches the admin spec.

### 2.3 Icons

**Lucide only.** Stroke width `1.75` at 14–18 px, `1.5` at 22–28 px. The prototype hand-inlines Lucide SVGs — in Flutter use `flutter_lucide` or similar. **No emoji, anywhere.**

### 2.4 Shadows, radii

| Name | Value |
|---|---|
| `shadow-soft` | `0 1px 2px rgba(15,17,57,.04), 0 2px 6px rgba(15,17,57,.04)` |
| `shadow-lifted` | `0 4px 12px rgba(15,17,57,.08), 0 12px 24px rgba(15,17,57,.06)` |
| radius-sm | 10 px (sys-cards, chips) |
| radius-md | 12 px (timeline cards, buttons) |
| radius-lg | 14 px (notification flyout) |
| radius-pill | 999 px (property pill, filter chips) |

### 2.5 Phone mockup spec (for reference)

The prototypes are drawn at 320 × 658 (iPhone 13-ish proportions with home indicator removed) with a 44 px status bar and a 78 px bottom tab bar. Build for 375-pt wide screens as baseline; layouts must scale up to 428 pt without changes to structure.

---

## 3. The 5-tab bar (mandatory across the app)

| Index | Tab | Icon | Purpose |
|---|---|---|---|
| 0 | **Home** | `home` | Context-aware dashboard |
| 1 | **Problems** | `wrench` | Maintenance + AI support (covered here) |
| 2 | **Info** | `info` | Lease, receipts, inspection reports, building docs |
| 3 | **Calendar** | `calendar` | Schedule (covered here) |
| 4 | **Chat** | `message-square` | Direct messaging outside of tickets |

### 3.1 The elevated-active pattern (non-negotiable)

The active tab's icon is rendered in a **36 × 36 navy circle** translated **up 10 px** so it breaks above the tab-bar top edge. Behind it sits a **54 × 54 pink radial-gradient cushion** (`radial-gradient(circle, rgba(255,61,127,0.18) 30%, transparent 70%)`) that reads as a warm glow. The icon inside the circle is white, stroke-width 2, 18 px.

CSS for the elevated state (translate to Flutter as a `Transform.translate` + `Container` decoration):

```
.tab.active .tab-ico-wrap {
  width: 36px; height: 36px; border-radius: 50%;
  background: navy;
  transform: translateY(-10px);
  box-shadow: 0 6px 14px rgba(43,45,110,0.35);
}
.tab.active .tab-ico-wrap::before {
  /* the pink cushion */
  width: 54px; height: 54px; border-radius: 50%;
  background: radial-gradient(circle, rgba(255,61,127,0.18) 30%, transparent 70%);
  z-index: -1;
}
```

**This is the only element in the whole UI that breaks the bottom line.** Do not add a second elevated element, ever.

---

## 4. Cross-cutting systems

### 4.1 Status dots — one colour language across the app

The tenant only has to learn three colours and they mean the same thing everywhere (ticket list, calendar rail, chat header):

- **Red** (`danger-600`) — urgent / needs action today (rent due tomorrow, geyser leaking, no electricity)
- **Amber** (`warning-600`) — waiting on something (supplier en-route, part on order, agent reviewing)
- **Green** (`success-600`) — done / confirmed / no action needed

Dots have a **2 px white ring + 5 px translucent colour halo** (`box-shadow: 0 0 0 2px white, 0 0 0 5px rgba(220,38,38,0.15)`). In the timeline rail, "today" gets a 16 px dot, everything else 12 px. Every dot placement is also echoed by the **left border of its card** (3 px in the matching colour) and optionally a coloured badge — redundancy protects colour-blind users.

### 4.2 Participant avatars

The tenant app renders four kinds of participants. Each has a distinct gradient so the tenant can tell them apart without reading names.

| Participant | Avatar | Gradient |
|---|---|---|
| Klikk AI | `sparkles` icon | `#a78bfa → #FF3D7F` (purple→pink) |
| Tenant (you) | Initials | `navy → navy-dark` |
| Agent | Initial | `#5a5d90 → #23255a` (navy-dark mid) |
| Supplier | Initial | `#647296 → #3c4668` (navy-grey) |

Rule: **agents are darker than the AI, suppliers are darker than agents.** The hierarchy is felt, not read. Mini avatars used inline in timeline cards are 18 px; full avatars in the chat header are 28 px; the ticket-list participant stack uses 22 px with -6 px overlap.

### 4.3 System cards (`.sys-card`)

Every state transition in a ticket renders as a pill-shaped card in the thread, not as a status page. Variants:

| Variant | Background | Example |
|---|---|---|
| Default / grey | `surface-secondary` | "Klikk AI logged this ticket · 09:12" |
| Success | `success-50` bg, `success-600` text | "Ticket approved · Plumber assigned" |
| Warning | `warning-50` bg, `warning-600` text | "Arriving ~14:22 · Toyota Hilux · live" |
| Passport | `navy` at 6% bg, `navy` text | "On your Klikk Passport · reports issues responsibly" |

System cards are short (one line), have a 13-px Lucide icon on the left, and **never have an action button** — they are announcements, not CTAs.

### 4.4 Property context pill

At the top of Problems and Calendar (below the header, above the filter chips) is a white pill showing `<map-pin>  12 Dorp St · Stellenbosch`. For multi-property tenants it becomes a tappable switcher; for single-property tenants it is still rendered (it is the title of the tab contextually). Height 32 px, `shadow-soft`.

---

## 5. Problems tab — 12 frames

The core bet: **the ticket IS the chat.** No ticket detail page, no status dropdown — every ticket is a chat thread, and the tenant, Klikk AI, agent, and supplier are all participants. State transitions arrive as sys-cards in the thread.

### 5.1 Frames 1–3: Ticket list

| # | State | Page description |
|---|---|---|
| **1** | **Empty state** | First-time user. Header ("Problems"). Large centred empty-state block with purple-to-pink gradient sparkles avatar, copy "Ask Klikk AI anything", subcopy explaining it reads your lease + building manual + SA rental law. **Primary CTA: navy "Ask Klikk AI" button with sparkles icon.** Below CTA: three grey "what you can ask" examples. No ticket list is rendered yet — list only appears after the first ticket. |
| **2** | **Active tickets** | Header ("Problems"). Filter chips row: `All · Open · Waiting · Resolved`. Three ticket rows. Each row is a **thread preview**: `title · last-message snippet · participant stack (overlapped avatars of AI/tenant/agent/supplier) · status dot · relative timestamp`. Row 1 red dot (geyser leak). Row 2 amber (gate motor waiting on part). Row 3 amber (curtain rod review). FAB `+` (pink) bottom-right that opens Frame 4. |
| **3** | **Resolved history** | Same list structure as Frame 2 but compact — smaller row height, no status dot, archived-grey palette. Closed tickets with "John · rated 5 · 3 Apr" style timestamp. Tapping a row opens Frame 12 (archived read-only view). |

### 5.2 Frames 4–6: AI-first intake

When the tenant taps the FAB, they do **not** see a form. They see a chat with Klikk AI.

| # | State | Page description |
|---|---|---|
| **4** | **AI greeting** | Chat canvas with one AI message: `"Hi Michael. What can I help with?"` plus **4 intent chips**: `Report a problem · Ask a question · Check my lease · Book a service`. The chat input at the bottom has a microphone icon and placeholder `"Describe what's happening..."`. No ticket exists yet. |
| **5** | **AI classifying** | Tenant has typed `"there's water dripping from the ceiling in the bathroom"`. AI responds with a message bubble classifying the event: `"Sounds like a geyser leak — that's an emergency. Can you send me a photo?"`. Below the AI bubble: a pulsing sparkles-dots indicator (the AI is "thinking"). Chips below the input offer: `Take photo · Choose from library · Describe with words`. The taxonomy inferred (`emergency · plumbing · geyser`) is shown as small meta tags under the AI message. |
| **6** | **Summary card** | AI has assembled a structured ticket and renders it as an in-thread **summary card** — not a new screen. Fields: `Title: "Water dripping from bathroom ceiling" · Category: Emergency plumbing · Urgency: High · Photos (2 thumbnails) · Location: 12 Dorp St, Stellenbosch (auto) · Notify: Sarah (agent)`. Two buttons below the card: **primary navy "Send to agent"** and ghost **"Edit"**. No dropdown, no category picker — the tenant only confirms. |

### 5.3 Frames 7–9: Multi-party thread (live)

The ticket has been sent. The thread is now visible. The chat header shows a **coloured status dot** (same language as the calendar), a **2–4 participant stack**, and the ticket ID.

| # | State | Page description |
|---|---|---|
| **7** | **Ticket sent** | Chat header: red dot + "KL-0473 · Water dripping" + 2 avatars (AI + MD). AI confirms dispatch: `"Ticket sent to Sarah. She usually responds within 2h."` Sys-card (warning, amber): `"Awaiting agent approval"`. Below: AI reminder `"While you wait: please turn off the geyser isolator if safe — I can show you where."` with a small action chip **"Show me"**. |
| **8** | **Agent joined** | Sys-card (default): `"Sarah joined the thread · 09:38"`. Header participant stack now 3 avatars (AI, MD, S). Sarah message: `"Approving now — sending John from Cape Plumbing."` Sys-card (success, green): `"Ticket approved · Plumber assigned"`. Status dot in the header transitions from red → amber. |
| **9** | **Supplier en-route** | Sys-card (default): `"John (Plumber · Cape Plumbing) joined · 13:45"`. Stack now 4 avatars. John message with a **live map preview** (90-ish px gradient rectangle, home pin + supplier pin + an angled track line) plus text `"12 min out, unlock the gate by 14:20"`. Amber sys-card below: `"Arriving ~14:22 · Toyota Hilux · live"`. |

### 5.4 Frames 10–12: Resolution

| # | State | Page description |
|---|---|---|
| **10** | **Awaiting parts** | Different ticket (gate motor, not geyser). Supplier Thabo diagnoses in-thread with two photos. Amber sys-card `"Status → Awaiting parts · expected Fri"`. Klikk AI follows with a sys-card `"Pinned return visit to your Calendar · Fri 14:00"`. Header shows amber dot, 4 participants (AI/MD/Sarah/Thabo). |
| **11** | **Resolved + inline rate** | John's last message: `"All done, geyser tested clean, pressure 3.2 bar."` Green sys-card `"Marked complete"`. Immediately below (same thread, no new screen): an **inline rate card** — 5 star row (two filled via default), free-text box ("Anything Sarah should know?"), privacy note ("Ratings stay on Klikk · your agent doesn't see stars"). The chat input bar at the bottom is **replaced** with a full-width navy bar: **"Submit rating to close ticket"**. Ratings cannot be skipped — the tenant can't reach the next ticket without submitting. |
| **12** | **Closed / archived** | Thread is read-only. At the top of the thread: a compact AI-generated **summary card** — 6 rows of `time · event`: logged → approved → dispatched → arrived → resolved → rated. Dark-ribbon navy-tinted sys-card `"On your Klikk Passport · reports issues responsibly"`. Bottom bar replaced with a single ghost button **"Reopen if it happens again"**. Status dot is grey. |

---

## 6. Calendar tab — 9 frames

The Calendar is organised as a **single vertical timeline** (not a monthly grid). Events hang off a central rail as dots, grouped by relative time: `Tomorrow · Next 2 days · Next 30 days · Next 2 months`. The colour of each dot tells the tenant what it is — red = money/action due, amber = waiting on someone, green = routine/done. Filter chips let them narrow to `Occupation · Viewings · Suppliers`.

### 6.1 Shared chrome on every Calendar frame

1. App header: hamburger (left), centred eyebrow "Calendar" + serif title (e.g. "Timeline" / "Viewings" / "Suppliers"), bell (right) with red notification dot
2. Property pill: `<map-pin>  12 Dorp St · Stellenbosch`
3. Filter chips row: `All · Occupation (n) · Viewings (n) · Suppliers (n)` (horizontally scrollable; active chip is navy)
4. Timeline scroll area with grouped date headers (`TOMORROW · 1 event` etc.)
5. 5-tab bar with **Calendar** elevated active

### 6.2 Section 1: Timeline core (frames 1–3)

| # | State | Page description |
|---|---|---|
| **1** | **Default · All filter** | "All" chip active. Groups visible: **Tomorrow** (1) → red dot, Rent due · April, R 14,500 · Debit order active · **Due tomorrow** badge. **Next 2 days** (2) → amber dot, Plumber · Cape Plumbing (John) + amber dot, Inspection (Sarah · be home). **Next 30 days** (4) → green dot, Garden service + red dot, Rent due · May. Establishes the vocabulary. |
| **2** | **Quiet week** | One event total — rent tomorrow. The `Next 2 days` group shows an empty state: a muted clock icon, `"Clear diary"` headline, "No commitments · enjoy it" subcopy. This is important — the app rewards quiet. The empty-state block sits in-line where event rows would, not as a modal. |
| **3** | **Next 2 months · scrolled** | Same page but scrolled down past `Tomorrow` and `Next 2 days`. Visible: `Next 30 days` (6) with Rent May, Pest control quarterly, **Lease renewal window opens** (amber — "Sarah will send terms · you have 14 days"). `Next 2 months` (6) with Rent June and lease-end markers. The renewal card has a subtle amber background tint (`warning-50`) to distinguish "life decision" from "routine event". |

### 6.3 Section 2: Filter chips (frames 4–6)

Three deliberate one-stream-at-a-time views. The chip count updates dynamically.

| # | State | Page description |
|---|---|---|
| **4** | **Occupation** filter | Only rent, inspections, and lease milestones. Tomorrow: Rent · April (red). Next 2 days: Inspection · Sarah 45 min. Next 30 days: Rent · May + Lease renewal window. All other event types hidden. |
| **5** | **Viewings** filter | Header title changes to "Unit shown" (context-aware). **Info banner** at the top (amber tint): `"Your lease ends 30 Jun. Sarah may show the unit to new prospects in the last 30 days."` Next 30 days shows two viewings: `Viewing · prospect · Sarah + 1 couple · you can be out` and `Sarah + 2 people · 30 min`. Next 2 months: empty state `"Nothing booked yet · Sarah will request times · you can approve or counter"`. |
| **6** | **Suppliers** filter | Next 2 days: one large amber dot, `John · Plumber · Cape Plumbing · Fri 18 Apr 14:00–16:00`, badge **"Arriving"**, sub-chip **"Access"** indicating tenant must be home. Next 30 days: Garden service (green). Next 2 months: Pest control quarterly (amber). The supplier row is the richest card type — includes mini supplier avatar, company name, and the "Access" sub-chip. |

### 6.4 Section 3: Detail drawers (frames 7–9)

Tapping a timeline card opens a **detail drawer** (full-screen sheet, back arrow top-left). The drawer has a coloured **hero** (matching the event's dot colour) and `detail-card` blocks below.

| # | State | Page description |
|---|---|---|
| **7** | **Rent due detail** | Hero: red gradient (`danger-600 → #991b1b`). Eyebrow "Due tomorrow", title "Monthly rent", meta "Thu 17 Apr · 09:00", amount `R 14,500` (serif), subcopy "No admin fee · Klikk trust account". Body cards: **Payment options** (debit order · active, EFT, card) — debit order row has a green "Active" badge. **Linked thread quote** — styled blockquote with navy-light border, "Klikk AI" attribution: `"Your debit order is scheduled for Thursday 09:00 — you don't need to do anything."` Bottom bar: ghost **"View receipt history"**. |
| **8** | **Supplier arriving detail** | Hero: amber gradient (`warning-600 → #92400e`). Eyebrow "Arriving in 28 hours", title "John Mbeki" (serif), meta `<truck> Cape Plumbing · geyser follow-up`. Body cards: **Map preview** (110-px gradient rectangle with navy supplier-pin top-left and pink home-pin bottom-right, diagonal track line). **Access notes**: "You need to be home. Gate code **\*1834**. John has a Cape Plumbing uniform — ID on file in Info → People." **Chat quote from John**: `"On my way Friday 14:00. Gate open by 14:20 please — I'll ring on arrival."` Button row: navy **"Open ticket thread"** + ghost **"Message John"**. |
| **9** | **Bell tapped** | Overlay state on top of the default timeline. A **dim backdrop** (rgba(17,24,39,.4) with 2px backdrop-blur) covers the screen. A **notification flyout** (240 px wide, white, 14-px radius, soft floating shadow) anchors under the bell. Header: `Recent · 3 new`. Three items: (1) pink dot — "John confirmed his arrival Friday at 14:00" · 2m ago. (2) pink dot — "Sarah booked an inspection for Sat 19 Apr" · 1h ago. (3) grey dot — "Your rent statement is ready to view" · Yesterday. The bell in the header is in a **navy active state** (filled circle, white icon). |

---

## 7. Build order (how to approach this)

### Phase 0 — Foundation (no screens yet)

1. Install Fraunces + DM Sans, wire the Klikk theme tokens (section 2.1) into Flutter's ThemeData.
2. Build the **5-tab shell** with the elevated-active pattern (section 3.1). Accept a single `activeIndex` prop, don't worry about routing yet. Screenshot-test at 375, 390, 428 pt.
3. Build the **status dot** widget (12 / 16 px; red/amber/green/grey) including the translucent halo box-shadow. Unit-test colour mapping.
4. Build the **participant avatar** widget (AI, tenant, agent, supplier) with the gradient rules from section 4.2. Provide sizes 18 / 22 / 28 px.
5. Build the **`SysCard`** widget (default/success/warning/passport variants).

### Phase 1 — Calendar (read-only data)

The Calendar is simpler than Problems and exercises all foundation widgets, so build it first.

1. `PropertyPill` header component.
2. `FilterChipRow` with scroll + active state. Controlled component — the parent owns which filter is selected.
3. `TimelineGroup` (header row with label, count, horizontal rule).
4. `TimelineEventRow` — the rail + dot + card composition. Handles first/last-child rail overrides so the vertical line terminates cleanly at the last dot in a group.
5. `TimelineEmptyGroup` (for the "Clear diary" state).
6. Compose Frames **1, 2, 3** in pure markup with mock data. Ship these behind a feature flag so QA can exercise them.
7. Wire **filter chips** (Frames 4, 5, 6). Filter logic lives in the parent; children re-render on the filtered list.
8. Build `EventDetailSheet` with the coloured hero and slots for body cards.
9. Implement `RentDueDetail` (Frame 7), `SupplierArrivingDetail` (Frame 8). Each is a concrete composition on top of `EventDetailSheet`.
10. Add the `NotificationFlyout` overlay + backdrop (Frame 9). Use a real bottom-sheet library if available; fall back to a custom `OverlayEntry` in Flutter.

### Phase 2 — Problems (read-only thread)

1. `TicketListRow` component — thread preview shape from Frame 2.
2. `TicketListScreen` with filter chips (All / Open / Waiting / Resolved). Compose Frames **2, 3**.
3. `ChatMessageBubble` variants: AI, tenant, agent, supplier. Use participant avatars from Phase 0.
4. `ChatHeader` with status dot + participant stack + ticket ID.
5. `TicketThreadScreen` composing bubbles + sys-cards. Hydrate from mock data. Render Frames **7, 8, 9, 10**.

### Phase 3 — Problems (AI intake)

This is where the app becomes agentic. It depends on a **Klikk AI service endpoint** (not in this brief) that takes free-text + attachments and returns a classification + suggested ticket structure.

1. `EmptyStateCTA` component for Frame 1.
2. `IntentChipGreeting` (Frame 4).
3. `AIClassifyingView` — streaming / thinking-dots state (Frame 5). Wire to a mock RAG endpoint first.
4. `SummaryCardInThread` — inline ticket preview with Send/Edit (Frame 6).
5. Wire the "Send to agent" flow to create a real ticket and transition into the thread screen (Frame 7).

### Phase 4 — Resolution & Passport

1. `InlineRateCard` in the thread (Frame 11). Block bottom-bar submit until stars are set.
2. `ArchivedThreadView` — read-only + summary (Frame 12).
3. Passport sys-card — requires a Passport API endpoint to confirm the increment happened.
4. Deep-link "Reopen if it happens again" back into the AI intake flow with context pre-filled.

### Phase 5 — Cross-tab plumbing

1. Tapping a Calendar supplier event → deep-links to the supplier's **ticket thread** in Problems (not a separate screen).
2. Tapping "Pinned to Calendar · Fri 14:00" in a ticket thread (Frame 10 sys-card) → deep-links to the Calendar event detail (Frame 8).
3. The bell notification flyout (Frame 9) items each deep-link to the relevant tab.

---

## 8. What's deliberately NOT in scope

These are explicit anti-features — don't build them, even if asked.

- **No email integration.** Tickets never leave Klikk.
- **No SLA clocks or numeric countdowns.** The amber dot is the status.
- **No priority matrix beyond three.** Emergency / Normal / Low only.
- **No category dropdown for the tenant.** The AI classifies; the tenant confirms.
- **No monthly-grid calendar view.** Timeline only.
- **No ticket search.** Scroll the list. Revisit when > 30 resolved tickets exist.
- **No separate "status page" inside a ticket.** State changes are sys-cards in the thread.
- **No second elevated tab or floating element in the bottom bar.** The navy circle on the active tab is the only thing that breaks the bottom line.

---

## 9. Data contracts (sketch)

These are illustrative — confirm with the backend team before implementing.

```ts
type TicketStatus = 'open' | 'waiting' | 'resolved';
type DotColour = 'red' | 'amber' | 'green' | 'grey';
type Participant = { id: string; role: 'ai'|'tenant'|'agent'|'supplier'; initials: string; name: string; };

type Ticket = {
  id: string;              // "KL-0473"
  title: string;
  status: TicketStatus;
  dot: DotColour;
  participants: Participant[];
  lastMessageAt: string;   // ISO
  lastMessageSnippet: string;
};

type ThreadMessage =
  | { kind:'chat'; from: Participant; text: string; attachments?: string[]; at: string; }
  | { kind:'sys';  variant:'default'|'success'|'warning'|'passport'; icon: string; text: string; at: string; }
  | { kind:'summary_card'; ticket: Omit<Ticket,'id'|'participants'> & { photos: string[]; location: string; notify: string[]; } }
  | { kind:'rate_card'; supplier: Participant; stars?: number; comment?: string; };

type CalendarEvent = {
  id: string;
  type: 'rent'|'viewing'|'inspection'|'supplier'|'renewal'|'garden'|'pest';
  dot: DotColour;
  titleMain: string;
  titleSub?: string;
  startsAt: string;  // ISO
  endsAt?: string;   // ISO
  linkedTicketId?: string;  // deep-link back to Problems
  accessRequired?: boolean;
  amountZar?: number;
};
```

---

## 10. References in this repo

| File | Purpose |
|---|---|
| `docs/prototypes/tenant-support.html` | Problems tab · 12 frames · the source of truth for structure |
| `docs/prototypes/tenant-support.png` | Retina capture · 2.1 MB |
| `docs/prototypes/tenant-support-rationale.md` | Why the Problems tab is chat-centric |
| `docs/prototypes/tenant-calendar.html` | Calendar tab · 9 frames |
| `docs/prototypes/tenant-calendar.png` | Retina capture · 1.5 MB |
| `website/public/prototypes/*.png` | Public-hosted copies for embedding in marketing pages |
| `website/src/components/AISupport.astro` | The Problems story turned into a marketing-site section |
| `docs/prototypes/sales-tenant-app.html` | Landlord/agent sales pitch using this app as the asset |
| `docs/prototypes/sales-klikk-passport.html` | Tenant-facing pitch for the Passport credential (Frame 12 outcome) |
| `.claude/skills/klikk-design-standard/` | The admin design standard — tokens and conventions are shared |
| `CLAUDE.md` | Repo overview · SA context · skill index |

---

## 11. Success signals to aim for

These are the outcomes the design is tuned for. If the built app doesn't deliver them, the design has failed.

1. A tenant opens the app for the first time and the **empty Problems state** reads as an invitation, not a form.
2. 67%+ of tenant-originated "tickets" resolve inside the AI intake conversation **without a ticket being created**. Confirm with a feature flag that logs `intent_resolved_without_ticket` events.
3. The tenant can answer **"what's on fire?"** in < 3 seconds by scanning the Calendar or Problems list. This means status dots must be scannable without reading text.
4. Rating completion rate on resolved tickets is > 70%. This is only possible because the rate card is in the thread and the input bar is replaced — do not loosen this.
5. No tenant ever asks "where's the status of my ticket?" over chat to the agent. If they do, we've failed at sys-cards.

---

_End of brief. When you want updates (new frames, additional tabs), regenerate the relevant HTML prototype + PNG + append a section to this document rather than creating parallel docs._
