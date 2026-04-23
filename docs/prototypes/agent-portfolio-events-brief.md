# Portfolio → Events — Development Brief

_Build spec for the dev agent implementing the Events view in the admin SPA._

**Source prototype:** `docs/prototypes/agent-portfolio-Events.html` (run the Prototypes Index at `http://localhost:8006/`)
**Companion view:** `docs/prototypes/agent-portfolio-timeline.html` (the sibling "By property" tab, already briefed separately)
**Implementation target:** `admin/` — Vue 3 + TS + Tailwind SPA
**Design rules:** `klikk-design-standard` skill (`.claude/skills/klikk-design-standard/`)
**Route:** `/portfolio?view=events` (shares `/portfolio` with `?view=timeline`)

---

## 1. Purpose

The "By property" tab (timeline) answers **"what's happening with property X this quarter?"**
The Events tab answers the inverse question: **"across my whole portfolio, what needs doing _right now_, grouped by the kind of work it is?"**

An agent managing 60–500 properties does not want to scroll a timeline to hunt for red dots. They want to open one page, see "14 rent-overdue today, 3 move-outs this week, 1 vacancy," click the queue they're in the mood to clear, and batch through it.

This is the action inbox for a whole portfolio.

---

## 2. IA at a glance

```
┌──────────────────────────────────────────────────────────────────┐
│ AppLayout (admin shell — navy brand pill, nav, role chip)        │
├──────────────────────────────────────────────────────────────────┤
│ PageHeader                                                       │
│   crumbs: Home / Portfolio / Events                              │
│   title:  Portfolio                                              │
│   sub:    Greenwood Realty · 60 properties · action queue…       │
│   actions: [Tabs: By property | Events]  [Export]  [New action]  │
├──────────────────────────────────────────────────────────────────┤
│ KPI grid (4 cards)                                               │
│   Open actions │ Overdue (danger) │ Due today/tmrw (warning) │ This week │
├─────────────────────────────────────────┬────────────────────────┤
│ Section card · "Action Queue"           │ Section card           │
│ ┌───────────┬─────────────────────────┐ │ "Upcoming Tasks"       │
│ │ Left menu │ Right filtered list     │ │ sticky, chronological  │
│ │           │                         │ │                        │
│ │ Urgent    │ [when-pill] 14 Rhodes   │ │ [icon] [when] Type     │
│ │  Rent ov. │              R9 800 …   │ │        Address         │
│ │  Maint.   │              [Collect]  │ │                        │
│ │  Owner…   │ [when-pill] 7 Oak …     │ │ [icon] [when] Type     │
│ │  Deposit  │              [Refund]   │ │        Address         │
│ │ Turnaround│                         │ │                        │
│ │  Move-out │           …             │ │ (30 rows, scrollable)  │
│ │  Move-in  │                         │ │                        │
│ │  Sign …   │                         │ │                        │
│ │ Pipeline  │                         │ │                        │
│ │ Vacancy   │                         │ │                        │
│ └───────────┴─────────────────────────┘ │                        │
└─────────────────────────────────────────┴────────────────────────┘
```

Three panels, one page. The left menu scopes **what**; the middle list shows **which properties + when**; the right sidebar shows **everything in date order** so nothing is hidden by the filter.

---

## 3. Route & tab contract

- Both tabs share `/portfolio`. The tab is a query param per `klikk-design-standard` view-patterns:
  - `/portfolio` → default: `view=timeline`
  - `/portfolio?view=events` → this page
- Whitelist: `const VALID_VIEWS = ['timeline', 'events']` + `normaliseView()` alias helper (accept `list`, `actions` → `events`; `matrix`, `by-property` → `timeline`).
- Tab component: the existing admin `tabs / tab` pill-tray pattern (grey tray, active pill is white with navy text + soft shadow). Do NOT render as `view-tabs` CSS from the prototype — use the admin `Tabs.vue` component if it exists, else match the pattern in `PropertyDetailView.vue`.
- Deep-linking the selected queue: `?view=events&queue=rent-overdue`. Whitelist all 12 keys below.

---

## 4. Event-type catalog (single source of truth)

12 event types across 4 groups. **Wire this from the backend**, not hard-coded in the view. Suggested Django serializer shape:

```json
{
  "key": "rent-overdue",
  "label": "Rent overdue",
  "group": "urgent",
  "icon": "banknote",
  "action_label": "Collect",
  "action_intent": "primary",
  "count": 14,
  "overdue_count": 11
}
```

| Group | Key | Label | Action | Match rule (backend) | Icon (lucide) | Tone |
|---|---|---|---|---|---|---|
| **Urgent** | `rent-overdue` | Rent overdue | Collect | Active lease, invoice past due | `banknote` | danger |
| | `maintenance` | Maintenance | Dispatch | Ticket open & SLA breached/contractor late | `wrench` | warning |
| | `owner-approval` | Owner approval | Chase owner | Inspection/quote awaiting owner sign-off | `user-check` | warning |
| | `deposit-refund` | Deposit refund | Refund | Stage 15 or refund deadline approaching (RHA 7/14/21 days) | `undo-2` | warning |
| **Turnaround** | `move-out` | Move-out | Inspect | Stage 8 | `log-out` | accent (pink) |
| | `move-in` | Move-in | Inspect | Stage 10 | `log-in` | orange |
| | `sign-contract` | Sign contract | Send to sign | Stage 5, unsigned | `file-signature` | purple |
| **Pipeline** | `notice` | Notice | Acknowledge | Stage 1 (new notice) | `bell` | navy |
| | `viewings` | Viewings | Host | Stage 3, scheduled | `eye` | navy-light |
| | `screen` | Screen | Review | Stage 4, application submitted | `check-circle` | info |
| | `renewal-due` | Renewal due | Draft offer | Stage 14 or ≤80 business days to lease end | `refresh-ccw` | info |
| **Vacancy** | `no-contract` | No contract | List | Unit has no active lease | `home-off` | danger |

**Stage reference:** see `agent-app-development-brief.md` §2 for the 15-stage canonical list.

**Due-date math (backend, per event):** each event type has its own "when" calculation. Overdue is `days < 0`. `days = 0` is Today, `days = 1` is Tomorrow, `2-7` is "soon", `>7` is "future". The prototype fakes this with a seeded hash — replace with real dates from the domain (invoice `due_date`, lease `end_date - 80 business days`, stage-transition SLAs, etc.).

---

## 5. Components to build / reuse

| Component | Source | Notes |
|---|---|---|
| `PageHeader` | existing admin | Pass `title`, `subtitle`, `crumbs`, default-slot for tabs + actions |
| `Tabs` / tab-pills | existing admin pattern | Active pill white on grey tray, `?view=` sync |
| `KpiCard` | **new** | Props: `label`, `value`, `tone` (`navy` / `danger` / `warning` / `info`), `icon`. Background tile for the icon, 22px value |
| `SectionCard` | existing `.card` + standard header row | Header = lucide 14px icon (navy) + uppercase navy label + right-aligned muted subtitle |
| `EventQueueMenu` | **new** | Left column. Grouped list of `EventType` with icon tile, label, count pill. Selected item = white bg + navy left-rule + navy label |
| `EventList` | **new** | Virtualised list of `EventRow`. Header band shows active queue pill + summary |
| `EventRow` | **new** | Grid: `[when-pill] [address/ctx] [action button]`. Clicking the row selects property (drawer); clicking the button fires the action intent |
| `UpcomingTasksCard` | **new, sticky** | Right sidebar. Global chronological feed (30 rows). Clicking a row sets `selectedKey + selectedPropId` and scrolls top |
| `WhenPill` | **new, shared with timeline** | Variants: `overdue` (`danger-50/700`), `today` (`warning-50/700`), `soon` (`info-50/700`), `future` (`gray-100/600`). Used by both `EventRow` and `UpcomingTasksCard` |
| `PropertyActionDrawer` | existing `BaseDrawer` | Opens on row click; shows property summary, stage, timeline mini, and the same action button |

---

## 6. Data contract (API)

New endpoints under `/api/v1/portfolio/`:

### `GET /api/v1/portfolio/events/summary`
KPI header + queue counts in one call. Cached 60s per agent.

```json
{
  "open_actions": 78,
  "overdue": 11,
  "due_today_or_tomorrow": 6,
  "due_this_week": 23,
  "queues": [
    { "key": "rent-overdue", "group": "urgent", "label": "Rent overdue",
      "action_label": "Collect", "action_intent": "primary",
      "count": 14, "overdue_count": 11 },
    ...
  ]
}
```

### `GET /api/v1/portfolio/events?queue=rent-overdue&limit=50&cursor=…`
Paginated, sorted by `due_days ASC` (overdue first).

```json
{
  "results": [
    {
      "id": "evt_01HV…",
      "queue_key": "rent-overdue",
      "due_at": "2026-04-12T00:00:00Z",
      "due_days": -6,
      "property": { "id": "prp_…", "address": "14 Rhodes Street", "suburb": "Stellenbosch" },
      "tenant": { "name": "Nomvula D." },
      "context": "R9 800 unpaid · Nomvula D.",
      "action": { "label": "Collect", "endpoint": "/api/v1/leases/{id}/chase", "method": "POST" }
    }
  ],
  "next_cursor": "…"
}
```

### `GET /api/v1/portfolio/events/upcoming?limit=30`
Cross-queue chronological feed for the right sidebar. Same row shape, no queue filter.

### Action endpoints
Each queue's action dispatches a domain operation (issuing a chase letter, opening an inspection record, etc.). Define one endpoint per `queue_key` and return `{ status, next_event? }` so the row can be optimistically removed and the next event slotted in.

**POPIA note:** event payloads must not leak tenant personal data beyond what the agent is entitled to (see `klikk-legal-POPIA-RHA`). `tenant.name` is fine; ID numbers, credit scores, and screening payloads stay server-side.

---

## 7. State & URL sync

```ts
// route: /portfolio?view=events&queue=rent-overdue
const view = computed<'timeline'|'events'>(() => normaliseView(route.query.view))
const selectedQueue = ref<QueueKey>(normaliseQueue(route.query.queue) ?? 'rent-overdue')
const selectedPropertyId = ref<string | null>(null)  // drawer-only; not in URL
```

- Queue change → replace URL (no history push); refetch `GET /events?queue=…`.
- Property select → open `BaseDrawer` with property detail; don't navigate away.
- `Upcoming` row click → set `selectedQueue` + `selectedPropertyId`, smooth-scroll to top, open drawer.

---

## 8. Empty / error / loading

Per `klikk-design-standard` view-patterns:

- **Zero queues** (nothing in the whole portfolio needs action): KPI cards all 0; main panel shows `EmptyState` with navy check icon, title "All clear.", body "You've cleared every queue. The next event will appear here automatically."
- **Zero in selected queue**: right panel shows inline muted "Nothing in this queue — great work." Keep menu and sidebar visible.
- **Loading**: skeleton rows in `EventList` (5 placeholders); KPIs show `—` until `/summary` resolves.
- **Error**: red banner at top of card: "Couldn't load events. [Retry]". Don't blow up the whole page; keep shell + sidebar if it loaded.

---

## 9. Design-standard compliance checklist

Before PR, confirm:

- [ ] No hex literals. Colours come from `navy`, `accent`, `danger-*`, `warning-*`, `info-*`, `success-*`, `gray-*` tokens only.
- [ ] No `text-[10px]` / `text-[11px]` on user-readable text. Floor is `text-xs` (12px). The count pill and role chip are the only sanctioned micro exceptions.
- [ ] Every icon is `lucide-vue-next`. Stroke-width 1.75. Sizes: 14px in section-card headers, 16px in buttons, 18px in nav, 20px in KPI tiles.
- [ ] Page starts with `<PageHeader>`. No hand-rolled `<h1>` + breadcrumb.
- [ ] No outer `max-w-*` inside the view — `AppLayout` handles it.
- [ ] Every section is a `.card` with the standard header row (`px-5 py-3 border-b border-gray-100`).
- [ ] Cards are `p-5` default. `EventList` uses `p-0` + per-row padding because the rows are their own density context.
- [ ] Tabs use `?view=` with `VALID_VIEWS` whitelist + `normaliseView()` alias helper.
- [ ] Empty states split "no queue matches" vs "everything is done."
- [ ] Action buttons use `.btn-primary` / `.btn-ghost` — do not hand-roll. The pink hover ring is applied by the base class; don't add your own.
- [ ] `aria-label` on every icon-only button. `aria-live="polite"` on the KPI region so screen readers get count updates after an action is cleared.

---

## 10. What's _not_ in v1

Deferred so v1 can ship in a week:

- **Bulk actions** (select many, clear together). Add later with a sticky bottom bar pattern.
- **Custom queue filters** (by suburb, owner, stage). KPIs + 12 fixed queues only in v1.
- **Saved views** per agent.
- **Real-time updates** (websocket push). v1 polls `/summary` every 60s when the tab has focus.
- **Exports** — the `Export` button in the header is a stub; wire to CSV endpoint in v1.1.

---

## 11. Testing

- Snapshot test: default render with 78 actions / 11 overdue matches Figma.
- Interaction: click each of 12 queues → URL updates, list refetches, menu highlight moves.
- Interaction: click upcoming row → selected queue changes AND drawer opens.
- A11y: axe-core passes; tab order goes PageHeader actions → tabs → KPIs → queue menu → list rows → upcoming sidebar.
- Empty state: mock `count: 0` on every queue → shows "All clear." EmptyState.
- E2E (Playwright): overdue rent-chase flow — click queue, click row's `Collect`, confirm dialog, row disappears, KPI decrements.

---

## 12. Open questions for product

1. When "Collect" is fired, do we send the tenant a chase message immediately, or stage a draft for the agent to review? (Affects action endpoint shape.)
2. Does `renewal-due` respect the 80-business-day RHA s4A(2)(d) threshold, or a shorter agency default?
3. Should `no-contract` (vacancy) link out to the marketing/listing flow, or open a "set up listing" drawer in place?
4. Do we want a "Snooze" affordance on each row (push to tomorrow / next week), or is that encouraging bad behaviour?

Resolve before build kick-off.
