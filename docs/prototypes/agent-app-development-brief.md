# Klikk Agent — Development Brief

_Feeding the dev agent. Covers the agent/letting-agent admin dashboard end-to-end._

**Source prototype:**
- `docs/prototypes/agent-dashboard.html` (interactive, three-layer desktop web app)
- `docs/prototypes/agent-dashboard.png` — retina capture of the default **Tasks** layer
- PNG copy for web hosting: `website/public/prototypes/agent-dashboard.png`

**Implementation target:**
- `admin/` — the Vue 3 + TypeScript + Tailwind SPA in this monorepo
- Follows `klikk-design-standard` skill (`.claude/skills/klikk-design-standard/`)
- **Note on fonts**: the prototype uses Fraunces (display) + DM Sans (body) for editorial tone. The production admin spec uses **Inter** at base 15 px. Match production on fonts; keep the layout, hierarchy, and interaction patterns from the prototype.

---

## 1. What this is (and who it's for)

The Klikk Agent app is the **admin web SPA** that letting agents and principals at small-to-medium rental agencies (3–500 properties) use every day. Tenants get the mobile app; landlords get an owner portal (separate); this is for the people who actually run a property book.

The design premise is blunt: **an agent with 100 properties should not have to remember what needs to happen today.** The app knows the 15-stage rental lifecycle of every property. It surfaces the next action per property, prioritises across the whole portfolio, and lets the agent resolve most tasks from a single inline row without ever opening a detail page.

If a competing PMS (Payprop, ReLeased, Propertyware) asks the agent to file their own tickets, hunt through menus, and produce reports, this app goes the other way: **the app files the tasks; the agent clears them.**

---

## 2. The 15-stage lifecycle (single source of truth)

Every property in the system is at exactly one of these stages at any given time. Stage drives urgency, next action, colour coding, and task generation.

| # | Stage | Phase |
|---|---|---|
| 1 | Notice Given | Pre-tenancy |
| 2 | Marketing | Pre-tenancy |
| 3 | Viewings | Pre-tenancy |
| 4 | Screening | Pre-tenancy |
| 5 | Lease Execution | Pre-tenancy |
| 6 | Invoice Setup | Pre-tenancy |
| 7 | Deposit Payment | Pre-tenancy |
| 8 | Move-Out Inspection | Turnaround |
| 9 | Repairs & Cleaning | Turnaround |
| 10 | Move-In Inspection | Turnaround |
| 11 | Onboarding | Turnaround |
| 12 | Rent Collection | Active Tenancy |
| 13 | Maintenance | Active Tenancy |
| 14 | Renewal / Notice | Active Tenancy |
| 15 | Deposit Refund | Closeout |

**Phase colour mapping** (use consistently everywhere — phase bars, stage dots, task strips, phase badges):

| Phase | Token | Stages |
|---|---|---|
| Pre-tenancy | `navy` (#2B2D6E) | 1–7 |
| Turnaround | `warning-600` (#d97706) | 8–11 |
| Active Tenancy | `accent` (#FF3D7F) | 12–14 |
| Closeout | `danger-600` (#dc2626) | 15 |

Canonical source in this repo: `content/product/lifecycle.yaml`. The app must read stage definitions from there — do not hardcode.

---

## 3. Design system (quick reference)

### 3.1 Colour tokens (from `admin/tailwind.config.js`)

| Token | Value | Use |
|---|---|---|
| `navy` | `#2B2D6E` | Brand primary, active nav pill, primary CTAs, pre-tenancy phase |
| `navy-dark` | `#23255a` | Gradient ends, hover state for navy |
| `accent` | `#FF3D7F` | Klikk pink, accent button, active-tenancy phase |
| `success-600` | `#0d9488` | Completed task tick, success toasts |
| `warning-600` | `#d97706` | Turnaround phase, "due today" chip |
| `danger-600` | `#dc2626` | Closeout phase, "overdue" chip, revenue-at-risk |
| `info-600` | `#2563eb` | Informational banners only |
| `surface` | `#F5F5F8` | App background |
| `surface-secondary` | `#F0EFF8` | Card row backgrounds, inline detail panels |
| `gray-50..900` | standard | Text, borders, dividers |

**HARD RULE**: No hex literals, no arbitrary `bg-[#...]` values in admin code. Every colour is a token. Violations are a bug.

### 3.2 Typography

- **Production**: Inter 400/500/600/700, base 15 px (not 16).
- `.page-title` · 1.25 rem · 700 · gray-900
- `.page-description` · 0.867 rem · gray-500
- `.section-header` · 0.867 rem · 600 · gray-800
- `.label-upper` · 0.72 rem · 600 · uppercase · gray-500
- `.stat-value` · 1.75 rem · 700 · gray-900 (large number in KPI cards)
- `.text-micro` · 0.72 rem · gray-500 (metadata, supporting text)
- **Floor**: never go below `.text-micro` (12 px). The only exceptions are the role pill in `AppLayout` and nav badge counters.

### 3.3 Icons

**Lucide only** (`lucide-vue-next`). Phosphor is banned (removed April 2026). Stroke-width `1.75`. Sizes: 16 px in buttons, 18 px in nav, 14 px in section-card headers.

### 3.4 Shadows / radii / spacing

| Token | Value |
|---|---|
| `shadow-soft` | `0 1px 2px rgba(15,17,57,.04), 0 2px 6px rgba(15,17,57,.04)` — cards at rest |
| `shadow-lifted` | `0 4px 12px rgba(15,17,57,.06), 0 12px 24px rgba(15,17,57,.04)` — hover, modals |
| `shadow-floating` | `0 12px 32px rgba(15,17,57,.08), 0 24px 48px rgba(43,45,110,.08)` — toast, dropdowns |
| Radii | 10 px chips · 12 px cards · 14 px modals · 999 px pills |
| Container | `max-w-[1400px]` in `AppLayout`. **Never add another `max-w-*` inside a view.** |

### 3.5 Mandatory shell components (already built)

Every view starts with these. Do not hand-roll equivalents.

- `PageHeader` — H1 + breadcrumb + right-side action slot
- `Breadcrumb` — driven via `PageHeader.crumbs`
- `BaseModal`, `BaseDrawer` — dialogs and side panels
- `EmptyState` — empty lists
- `SearchInput`, `FilterPills` — list controls
- `ConfirmDialog` — destructive actions

---

## 4. Top-level IA — 3 layers, not a sitemap

Most PMS apps give you a tree of 40+ menu items. This app gives you **three nav buttons** in the header, because that's all a working agent needs:

| Layer | Purpose | "Where am I?" |
|---|---|---|
| **Tasks** | The actions that need resolving right now, across the whole portfolio | "What do I do next?" |
| **Board** | Portfolio-level health — occupancy, pipeline, revenue at risk | "How's my business?" |
| **Properties** | The 100-property grid + drill-down into any one property's timeline | "Where is property X?" |

Everything else — tenants, suppliers, documents, settings — is reachable from a property detail page or from a sitemap dropdown. The top-level IA is locked at three.

### 4.1 Header nav

Glassmorphism top bar (`.header-nav` in `admin/src/assets/main.css`):
- Left: `klikk.` logotype in Fraunces (or the admin brand mark)
- Centre: the three layer buttons, active one rendered as a **filled navy pill** with white text
- Right: agent name + 32 px circular avatar with initials

**Role pill**: immediately left of the avatar, a small tinted capsule shows the current role (`Agent`, `Owner`, `Supplier`, `Principal`). This is a multi-role app — the pill tells you which lens you're looking through.

---

## 5. Layer 1 — Tasks (the default view)

This is what the agent sees when they open the app. It is the heart of the product.

### 5.1 Layout

1. **Greeting strip** (top)
   - Left: `Good morning, Michael` (Fraunces serif, 1.4 rem) + dated subcopy `Wednesday, 16 April 2026`
   - Right: three **urgency chips** — `2 overdue · 3 due today · 2 this week`. Each chip is a filled pill in its semantic colour (`danger-50` bg + `danger-700` text for overdue, `warning-50` / `warning-700` for today, `navy` 5% / navy for week).

2. **Urgent banner** (only rendered if `overdue > 0`)
   - Full-width pink-tinted strip with a pulsing dot: `2 properties need immediate action — deposit refund deadlines approaching`.
   - This is the only time the app raises its voice. Reserve for POPIA-level legal deadlines.

3. **Task list** (the main content)
   - A single card containing a vertical stack of task rows. Each row is inline-resolvable.
   - Ordered by urgency: overdue → today → this week. Secondary sort by phase (closeout > turnaround > pre-tenancy > active) so the painful ones stay at the top.

4. **Progress footer**
   - Left: `Completed today: 0 / 7` with the count in `success-600`.
   - Right: **progress dots** — one dot per task, grey → navy (current) → success-green (done). The pink box-shadow on the current dot is the visual anchor for "your next move".

### 5.2 Task row anatomy

Left to right:

| Element | Spec |
|---|---|
| **Phase strip** | 4-px vertical bar on the far left, coloured by the property's phase (navy / amber / pink / red). |
| **Stage number** | 24 px square, rounded, filled with the phase colour, white digit inside (e.g. `15` for deposit refund). |
| **Task main** | Two lines. Line 1 = task title (`"Process deposit refund"`) + inline urgency chip at the end. Line 2 = `property · tenant · rent/mo` in gray-500 11 px. |
| **Task action button** | Right-aligned, filled navy pill, icon + label (e.g. `"Generate Refund Statement"`). **This is the point** — most tasks are resolvable in one click from this row. |
| **More menu** | 3-dot icon that opens the expanded detail panel below the row. |

### 5.3 Inline detail panel (on "more" click)

Smooth-animated expansion below the row (`max-height` transition, ~280 ms). Contains:
- **Detail text** — one or two sentences of context
- **Meta chips** — calendar icon + due label (`"Legal deadline passed"`) + phase badge
- **Secondary links** — `View timeline · Snooze · Reassign`. These open the property detail or trigger modals.

The detail panel matters because it lets the agent make a judgement call without leaving the task stack.

### 5.4 Empty state

When `tasks.filter(notCompleted).length === 0`:

- Large centred "All caught up" message
- Subcopy: `"No more actions needed today. Great work."`
- No confetti, no icon stack — this is a daily professional app, not a game. Understated is the point.

### 5.5 Task data contract

```ts
type Task = {
  id: string;
  property: string;         // "44 Church St, Unit 2"
  propertyId: number;
  title: string;            // "Process deposit refund"
  detail: string;           // One-sentence context
  stage: number;            // 1–15
  phase: 'pre' | 'turnaround' | 'active' | 'closeout';
  urgency: 'overdue' | 'today' | 'week';
  urgencyLabel: string;     // "Overdue — 9 days"
  dueLabel: string;         // "Legal deadline passed"
  tenant: string;
  rent: string;             // "R12,000"
  btnLabel: string;         // "Generate Refund Statement"
  btnIcon: string;          // Lucide icon name (NOT emoji)
  completedAt?: string;     // ISO once done
};
```

**Backend contract**: tasks are derived, not stored. A Django job runs hourly across all properties, applies stage-specific rules (e.g. stage 15 → task "Process deposit refund" if `inspection_completed_at` is set and `refund_processed_at` is null), and materialises a task queue keyed per agent. Completing the task fires the real backend action (generate refund PDF, send e-signing link, dispatch contractor) — the UI is a thin shell on top.

---

## 6. Layer 2 — Board

Portfolio health at a glance. No drill-down interactions on this screen — it's a read-only dashboard that tells the agent whether the business is OK.

### 6.1 Layout (top to bottom)

1. **Title strip**: `Portfolio Health` (H1) + `100 properties under management`
2. **KPI grid** — 4 cards, evenly spaced, 2-up on mobile / 4-up ≥ 1024 px
3. **Pipeline card** — horizontal stacked bar
4. **Revenue-at-risk card** — thin progress bar
5. **Two-column grid** — `This Week` (left) + `Needs Attention` (right)

### 6.2 KPI cards (4)

Each card: label-upper at top, large `stat-value` number, delta line below.

| Card | Value shown | Delta |
|---|---|---|
| **Occupancy** | `92%` | `↑ 2% vs last month` (positive green) |
| **In Turnaround** | `5` | `Avg 4.2 days vacant` (warning amber) |
| **Revenue at Risk** | `R36K` in `danger-600` | `3 vacant > 7 days` (negative red) |
| **Collection Rate** | `97%` | `3 late payments` (positive green) |

Delta tone rules:
- **Positive delta** (occupancy up, collection up): `success-600`
- **Warning delta** (vacancy time, minor late): `warning-600`
- **Negative delta** (revenue at risk): `danger-600`

### 6.3 Pipeline bar

A single horizontal stacked bar showing the distribution across the 4 phases:

- Pre-tenancy (8) · navy
- Turnaround (5) · warning-amber
- Active (85) · accent-pink
- Closeout (2) · danger-red

Each segment's flex-basis is its count. Below the bar, a legend row with 8-px phase dots and counts.

### 6.4 Revenue at risk

Title: `Revenue at Risk` · right-aligned micro-label `R36,000 / R1,200,000 portfolio`.
Below: a 6-px track with a `danger-600` fill sized to the at-risk percentage (3% in the prototype). Under the bar, two lines: `3 vacant units × avg R12,000/mo` and `3% at risk` in danger-600.

### 6.5 This Week (left column)

A card with a stacked list of agenda rows — one per weekday. Each row:
- 3-letter day abbreviation (`Mon`, `Tue`, ...)
- Inline badge stack: `2 viewings`, `1 inspection`, `Move-out 7 Dorp St`, `2 deposit refunds`, etc.

Today's row gets a subtle amber-tinted background (`warning-50`) + a `Today` badge to anchor the agent. Rows are purely informational — no click-through.

### 6.6 Needs Attention (right column)

A card with up to 5 property rows sorted by severity. Each row:
- 🏠 house thumb (32 px placeholder — later: real property photo)
- `prop-name` + `prop-detail` (one-line reason)
- Severity badge (`Overdue` red, `Urgent` amber, `Today` amber, `3 days` amber)

Clicking a row deep-links to the property's detail timeline (Layer 3 → detail view).

---

## 7. Layer 3 — Properties

Two states: the **list view** (default) and the **detail timeline** (clicked into).

### 7.1 List view

- Title: `Properties` · H1
- Right of title: horizontally scrollable filter pills — `All (100) · Pre-tenancy (8) · Turnaround (5) · Active (85) · Closeout (2)`. Active pill is `.pill-active` (filled navy).
- Below: a single card containing 30 of N property rows (the prototype caps the DOM at 30 for perf; production uses virtual scroll).

Each property row (left → right):
- House thumb (32 px)
- **Prop-name**: `44 Church St, Unit 2`
- **Prop-detail**: `Lindiwe Dlamini · R12,000/mo`
- **Phase badge** (Active Tenancy / Pre-tenancy / Turnaround / Closeout) in its phase colour
- **15 stage dots** — a horizontal row of tiny coloured dots showing where on the lifecycle this property is. Completed stages filled in their phase colour, the current stage slightly larger (6 px) with a pink glow ring. Unfilled stages stay `gray-200`.

Row sort: `turnaround → closeout → pre-tenancy → active` (the ones that need work first, healthy ones last).

### 7.2 Property detail (clicked into)

Back button at the top (`← Back to properties`).

Then three cards in order:

**Card 1 — Header**
- 56 × 56 thumb, serif address, suburb + tenant + rent line, right-aligned phase badge `Stage 13 · Active Tenancy`
- Full-width **phase progress bar** — 15 equal segments, each filled or empty based on `i <= currentStage`, coloured by phase. Below the bar: 4 phase labels distributed left-to-right (`Pre-tenancy · Turnaround · Active · Closeout`).

**Card 2 — Next Action** (with 4-px accent-pink left border)
- Eyebrow: `Next Action` in accent pink
- Title: the current stage name in Fraunces serif
- Body: one-sentence instruction (from `content/product/lifecycle.yaml`)
- Primary button: **"Execute [Stage Name] →"** — this is the single action the agent needs to take next. Clicking it triggers the backend workflow for that stage.

**Card 3 — Full Timeline**
- Section header: `Full Timeline` with a clock icon
- Vertical stepper, one row per stage (1–15):
  - **Completed**: check-tick dot in phase colour, full-colour text
  - **Current**: filled pink/phase dot with number inside, full-colour text, **"Execute →" button** inline
  - **Future**: outlined gray dot with number, muted text

This screen is where a new agent learns the rental lifecycle by scrolling it, and where an experienced agent goes to sanity-check a weird property. It replaces the "notes field + tabs" pattern every other PMS uses.

---

## 8. Cross-cutting systems

### 8.1 Urgency chips

Three variants. Used on: task rows, urgency summary strip, needs-attention rows.

| Chip | Bg | Text |
|---|---|---|
| `urgency-overdue` | `danger-50` | `danger-700` |
| `urgency-today` | `warning-50` | `warning-700` |
| `urgency-week` | `navy` at 8% | `navy` |

### 8.2 Phase badges

Used on: property rows, property detail header, task detail meta. One per phase.

| Badge | Bg | Text |
|---|---|---|
| `badge-navy` (pre) | `navy` at 10% | `navy` |
| `badge-amber` (turnaround) | `warning-100` | `warning-700` |
| `badge-green` (active) | `success-100` | `success-700` |
| `badge-red` (closeout) | `danger-100` | `danger-700` |

### 8.3 Toast

Shown after any task completion. Bottom-right, `shadow-floating`, 16-px success-500 tick icon on the left, message on the right. Auto-dismisses after 2.5 s.

### 8.4 Tab state + URL

Each layer is a route, not a client-only toggle:
- `/` → Tasks (also `/?tab=tasks`)
- `/?tab=board` → Board
- `/?tab=properties` → Properties list
- `/properties/:id` → Property detail timeline

Use the project's standard `?tab=` + `VALID_SECTIONS` whitelist pattern (see `admin/src/views/properties/PropertyDetailView.vue` as canonical).

---

## 9. Build order

### Phase 0 — Shell (≈ 1 day)

1. Install the admin shell components if not already present (`PageHeader`, `AppLayout` with header nav, role pill, avatar, `max-w-[1400px]` container).
2. Wire the three-button header nav (`Tasks · Board · Properties`) into Vue Router with `?tab=` pattern.
3. Confirm the theme — Inter 15 px base, design tokens from `tailwind.config.js`, Lucide icons wired.

### Phase 1 — Tasks layer (≈ 3–4 days)

1. **Backend**: build the task-derivation service. Cron job or signal-based. For each property, check current stage against rules and materialise one task if needed. Store in `tasks` table with `agent_id`, `property_id`, `stage`, `urgency`, `due_at`, `resolved_at`.
2. **API**: `GET /api/v1/agent/tasks` returning the shape in §5.5. Sort server-side.
3. **Frontend**:
   - `UrgencySummaryStrip.vue` — three chips with counts
   - `UrgentBanner.vue` — conditional pink strip
   - `TaskRow.vue` — the inline row including phase strip, stage number, action button, more menu
   - `TaskDetailPanel.vue` — expanded detail with meta chips + secondary links
   - `TaskProgressDots.vue` — per-task completion dots
   - `TasksView.vue` — composes the above, owns the task list state
4. **Action wiring**: each `btnLabel` maps to a concrete handler — generate refund PDF (calls `/api/v1/leases/{id}/refund-statement`), resend signing link (`/api/v1/esigning/{id}/resend`), etc. Handlers show optimistic completion + a toast on success + rollback on error.
5. **Empty state**: `"All caught up"` when no tasks remain.

### Phase 2 — Board layer (≈ 2 days)

1. **API**: `GET /api/v1/agent/portfolio-health` returning `{ occupancy, in_turnaround, revenue_at_risk_zar, collection_rate, pipeline: { pre, turnaround, active, closeout }, this_week: [...], needs_attention: [...] }`. All aggregations done server-side.
2. **Frontend**:
   - `KpiCard.vue` with label + `stat-value` + delta line (supports positive/warning/negative tones)
   - `PipelineBar.vue` — stacked horizontal bar with legend
   - `RevenueAtRiskCard.vue`
   - `WeekAgendaCard.vue` — day rows with inline badges
   - `NeedsAttentionCard.vue` — property rows deep-linked to §7.2
   - `BoardView.vue` — composes everything

### Phase 3 — Properties layer (≈ 3 days)

1. **API**: `GET /api/v1/properties?phase=active&page=1` — paginated, sorted, filterable by phase.
2. **Frontend**:
   - `StageDotRow.vue` — the 15-tiny-dot stage row (used in list + detail header)
   - `PropertyListRow.vue` — thumb + name + tenant/rent + phase badge + stage dots
   - `PropertyFilterPills.vue` — reuses `FilterPills`
   - `PropertiesView.vue` — list + filter + virtual scroll (use `vue-virtual-scroller` for 100+ rows)
   - `PropertyDetailView.vue` (already exists — extend it):
     - `PropertyDetailHeader.vue` — header card with full phase progress bar
     - `NextActionCard.vue` — accent-pink left border, single CTA
     - `FullTimelineStepper.vue` — 15 stepper rows (completed / current / future)
3. Deep-link `NeedsAttentionCard` rows and task `View timeline` links to `/properties/:id`.

### Phase 4 — Workflow execution (≈ 5 days, per stage)

Each of the 15 stages needs its "Execute →" handler wired to a real workflow. Start with the highest-volume tasks first:
- Stage 12 (Rent Collection) — recurring, touches every active property
- Stage 15 (Deposit Refund) — legal deadline, highest cost of failure
- Stage 3 (Viewings) — highest-touch during pre-tenancy
- Stage 8 + 10 (Inspections) — already partially built in `admin/src/views/inspections/`
- Stage 5 (Lease Execution) — wire to the existing e-signing flow

Do not try to do all 15 at once. Ship them one stage at a time with a feature flag per stage.

### Phase 5 — Cross-layer plumbing

- Task row → property timeline deep-link
- Board "Needs Attention" → property timeline deep-link
- Property timeline "Execute" → opens the relevant workflow modal in-context (not a new page)
- URL state synced to layer + filter + property id so the agent can bookmark/share

---

## 10. What this replaces (and what it doesn't)

### Replaces
- **The "Dashboard" page** in legacy PMS apps (a meaningless collection of widgets). The Tasks layer is the new dashboard, because it gives the agent something to do, not something to look at.
- **Per-property "status" dropdowns** scattered across menus. Now property status = stage number + phase colour, visible everywhere.
- **Reminders and "follow-up" tags**. The task-derivation service knows what needs doing; the agent doesn't have to remember.

### Does NOT replace
- Accounting / trust-account reconciliation (separate view, not in this brief)
- Tenant app (separate app — see `tenant-app-development-brief.md`)
- Owner portal (separate surface with the same tokens but a read-only lens)
- Supplier portal (separate surface)

---

## 11. Anti-patterns (don't do these)

- **Do not** add a 4th nav button. Three is the IA. If you're tempted to add "Reports", add it to the Board layer as a subsection.
- **Do not** hand-roll `<h1>` + breadcrumb markup. Use `PageHeader` with `crumbs`.
- **Do not** wrap a view in another `max-w-*`. `AppLayout` already clamps at 1400 px.
- **Do not** use emoji for icons. The prototype uses 🏠 and 💰 as placeholders — production uses Lucide (`home`, `banknote`).
- **Do not** build a monthly-grid calendar here. Scheduling is the tenant's concern; the agent sees week agenda (Board) and per-property timeline (Properties).
- **Do not** build a ticket or email inbox inside the agent app. Tickets live in the tenant's Problems tab and surface to the agent as chat threads (reuse the chat infrastructure; see `tenant-support-rationale.md`).
- **Do not** introduce a second "overdue" tone. The red+pink urgent banner is strong enough. Multiple urgency systems train the agent to ignore them.

---

## 12. Success signals

These are the outcomes the design is tuned for. If the built app doesn't hit them, the design has failed.

1. **Time-to-first-action under 30 seconds** from app open to completing the first task.
2. **> 70% of daily tasks resolved inline** from the task row's primary action button, without opening a detail page.
3. **Agents can articulate the 15-stage lifecycle** after one day of use. If they can't, the phase colours and stage numbers aren't doing their job.
4. **Deposit refund overdue rate drops to zero** within 30 days of rollout. Stage 15 has a legal deadline and the app's job is to not let it slip.
5. **No request for a "dashboard customisation" feature** in the first 90 days. If agents ask for it, the default dashboard isn't answering the right question.

---

## 13. Data contracts

```ts
type Phase = 'pre' | 'turnaround' | 'active' | 'closeout';
type Stage = 1|2|3|4|5|6|7|8|9|10|11|12|13|14|15;
type Urgency = 'overdue' | 'today' | 'week';

type Property = {
  id: number;
  address: string;
  suburb: string;
  tenantName?: string;        // null if vacant
  rentZarMonthly?: number;
  currentStage: Stage;
  phase: Phase;
  stageTitle: string;         // from lifecycle.yaml
  thumbUrl?: string;
};

type PortfolioHealth = {
  occupancyPct: number;       // 0–100
  inTurnaround: number;
  revenueAtRiskZar: number;
  revenueAtRiskPct: number;
  collectionRatePct: number;
  pipeline: Record<Phase, number>;
  thisWeek: Array<{ dayAbbrev: string; items: Array<{ label: string; tone: 'navy'|'amber'|'green'|'red' }> }>;
  needsAttention: Array<{
    propertyId: number;
    propertyName: string;
    reason: string;
    severity: 'overdue' | 'urgent' | 'today' | 'upcoming';
    daysLabel: string;
  }>;
};

// Task contract: see §5.5 above
```

---

## 14. References in this repo

| File | Purpose |
|---|---|
| `docs/prototypes/agent-dashboard.html` | Interactive prototype · three layers · source of truth for structure |
| `docs/prototypes/agent-dashboard.png` | Retina capture of the default Tasks layer · 333 KB |
| `docs/prototypes/tenant-app-development-brief.md` | Sister brief · same stack, tenant-facing |
| `docs/stitch-references/agent/` | Earlier mobile-reference PNGs (stitch-generated); not canonical but useful for mobile-agent variants |
| `content/product/lifecycle.yaml` | The 15-stage lifecycle authority |
| `content/product/features.yaml` | Feature status authority — check before writing "Execute" handlers |
| `admin/src/assets/main.css` | Component classes (`.card`, `.btn`, `.badge-*`, `.header-nav-link-active`, `.pill`, `.label-upper`, `.stat-value`, `.text-micro`) |
| `admin/tailwind.config.js` | Colour tokens, font stack |
| `admin/src/components/AppLayout.vue` | Shell — header nav, role pill, container clamp |
| `admin/src/components/PageHeader.vue` | Required top-of-view component |
| `admin/src/views/properties/PropertyDetailView.vue` | Canonical `?tab=` + section-card pattern |
| `admin/system_documentation/claude_opus_ux_ui_audit_2026-03-25.md` | Full UX/UI audit — read for view-specific findings before design decisions |
| `.claude/skills/klikk-design-standard/` | Design standard skill — enforce on every PR |
| `CLAUDE.md` | Repo overview, SA context, skill index |

---

## 15. Process (as a whole)

End-to-end flow for shipping the agent app, assuming a fresh team:

1. **Week 1**: Stand up the shell (Phase 0) + ship the Tasks layer with 3 working stages (Phase 1 + a partial Phase 4). Target: an agent can log in, see their deposit refunds overdue, click one button, and a real PDF refund statement is generated.

2. **Week 2**: Ship the Board layer (Phase 2). Target: an agent opens the Board and the numbers match their accountant's dashboard to within 1%.

3. **Week 3**: Ship the Properties layer (Phase 3). Target: every property in the agent's book is listed, filterable, and drills into a timeline view.

4. **Weeks 4–8**: Wire the remaining 12 stage workflows (Phase 4). Ship one stage per day, feature-flagged, with backend + frontend + QA + rollout in the same commit.

5. **Week 9**: Cross-layer plumbing (Phase 5) + polish. Delete the old admin dashboard. Remove the sitemap dropdown links to any legacy pages that this app replaces.

6. **Week 10+**: Watch the success signals in §12. If agents aren't completing > 70% of tasks inline, the action buttons are wrong — not the layout.

The brief's strongest opinion: **the Tasks layer is the product.** The Board is reassurance, Properties is a reference. If you have to cut scope, keep Tasks and ship the others later. An agent with Tasks alone is more productive than an agent with every PMS feature in Payprop.

---

_End of brief. When the UI evolves, update `agent-dashboard.html` first, regenerate the PNG, then append to this document. Do not fork into parallel docs._
