# Agent preview — design standard audit (2026-04-18)

Audited by: Claude (klikk-design-standard skill, April 2026 edition)

Files reviewed:
- `admin/src/components/AgentPreviewLayout.vue`
- `admin/src/assets/agent-shell.css`
- 15 views: `admin/src/views/agent-preview/Agent*.vue`
- `admin/src/router/index.ts` (lines 153–179)
- `admin/tailwind.config.js`
- Skill references: design-tokens.md, icons.md, anti-patterns.md, accessibility.md, view-patterns.md, nav-hierarchy.md

---

## Executive summary

- The agent preview is a **deliberate parallel shell** (own CSS tokens, own chrome, own fonts) ported 1:1 from the `admin-shell` prototype. Its divergence from the main admin design system is architecturally intentional — it is not a broken port of the main app.
- The single **hardest violation** is the icon library: the agent preview loads Phosphor Icons via CDN and uses `<i class="ph ph-*">` throughout, directly contradicting the design standard's April 2026 ban on Phosphor in the admin SPA.
- Accessibility is thin across the board: no `scope="col"` on any table header, no `aria-label` on icon-only action buttons, tabs driven by local state with no `?tab=` query param, and icon-only status cells (POPIA/FICA columns) rely on color + icon with no text label.
- Color tokens are well-implemented inside the `agent-shell` CSS scope — the hex values mirror the main Tailwind config. However, hardcoded hex literals (`#8B5CF6`, `#D97706`, `#14B8A6`, `#EA580C`, `#7C3AED`, `#DCF8C6`, `#334`, `#556`) appear in several views, bypassing even the agent-shell's own CSS variables.
- The `font-size:10px` label on photo thumbnails violates the readable-text floor. This is a consistent pattern across `AgentPropertyView` and `AgentMaintenanceTicketView`.

---

## Compliance matrix

| Area | Standard says | Agent preview does | Verdict |
|------|---------------|--------------------|---------|
| Icon library | `lucide-vue-next` only; Phosphor banned April 2026 | Phosphor web font loaded via CDN (`@phosphor-icons/web@2.1.1`); zero Lucide imports | **FAIL** |
| Color tokens | Tailwind tokens (`bg-navy`, `text-danger-600`); no hex literals | CSS vars inside `.agent-shell` scope match token values; but raw hex (`#8B5CF6`, `#D97706`, `#7C3AED`, `#DCF8C6`) used inline across 6 views | **PARTIAL** |
| Typography — font | Inter 15px base | DM Sans 14px base (agent-shell.css L36–39) — parallel shell, by design | **ACCEPTABLE DIVERGENCE** |
| Typography — display headers | — | Fraunces for h1–h4 in agent-shell; consistent; DM Sans for body | **ACCEPTABLE DIVERGENCE** |
| Typography — text floor | `text-xs` (12px) minimum for readable text | `font-size:10px` used on photo thumbnail labels (AgentPropertyView L236–241, AgentMaintenanceTicketView L127–132) | **FAIL** |
| Buttons | `.btn-*` component classes | Agent-shell defines `.btn`, `.btn.primary`, `.btn.ghost`, `.btn.accent` — own system, scoped; consistent within shell | **ACCEPTABLE DIVERGENCE** |
| Button focus ring | accent-pink ring on hover via main.css | `.btn:focus-visible` defined in agent-shell.css with `outline: 2px solid var(--navy)` — works, different color | **ACCEPTABLE DIVERGENCE** |
| Tables | `<div class="table-scroll">` wrapper + `scope="col"` on all `<th>` | No `table-scroll` wrapper (uses `.table-wrap` div instead); zero `scope="col"` attributes on any `<th>` | **FAIL** |
| Tab navigation | `?tab=<key>` + `VALID_SECTIONS` + `normaliseTab()` | Local `ref<Tab>` state only; no query param syncing in any of 4 tabbed views (AgentPropertyView, AgentMaintenanceTicketView, AgentOverviewView, AgentSettingsView) | **FAIL** |
| PageHeader component | Every view uses `<PageHeader>` — no hand-rolled h1 | Hand-rolled `.page-header` div with `<h1>` in every view; `<PageHeader>` component never used | **FAIL** (by design — parallel shell) |
| Empty states | `EmptyState` component with action CTA; split no-match vs no-items | Ad-hoc `.empty` class with `<i>` (Phosphor) + `<h2>`; no EmptyState component; no split pattern; only 1 empty state implemented (AgentMaintenanceTicketView invoice tab) | **FAIL** |
| Accessibility — ARIA | `aria-label` on icon-only buttons; `aria-expanded` on dropdowns | `aria-expanded` present on avatar button only; zero `aria-label` on icon-only buttons (`icon-btn` class); no `aria-haspopup` on agency switcher or nav items | **FAIL** |
| Accessibility — tables | `scope="col"` on all `<th>` | None found in any of the 15 views | **FAIL** |
| Accessibility — color independence | Text + icon for status; never color alone | POPIA/FICA columns in AgentContactsView use icon-only (no text label): `<i class="ph ph-check-circle">` with no visible text | **FAIL** |
| Dropdown a11y | click toggle + Escape + outside-click + `aria-haspopup` | Avatar menu: click toggle ✓, Escape ✓, outside-click ✓, `aria-expanded` ✓; missing `aria-haspopup="true"` on avatar button; agency switcher is a plain `<button>` with no a11y attributes and no open/close behavior | **PARTIAL** |
| Spacing tokens | Tailwind standard spacing; no arbitrary values | All spacing is in CSS via `agent-shell.css` CSS properties (px values); not Tailwind utilities — expected for the CSS-module approach of this shell | **ACCEPTABLE DIVERGENCE** |
| Section-card headers | Lucide 14px `text-navy` icon + uppercase label pattern | `.pcard h3` uses Phosphor `<i>` + text; no equivalent standardized header-row atom | **FAIL** (icon library issue) |
| Responsive | Mobile-first; `grid-cols-N` with breakpoints | `@media (max-width:900px)` stub hides sidebar, keeps board-cols wide; board and kanban use `min-width` (hardcoded to 2200px / 1400px); no tablet breakpoints | **PARTIAL** |
| Shadow tokens | `shadow-soft` / `shadow-lifted` / `shadow-floating` | Agent shell defines `--shadow` CSS var (matches `klikk-soft` value exactly) | **ACCEPTABLE DIVERGENCE** |
| Radius tokens | `rounded-xl` cards, `rounded-lg` inputs, `rounded-full` badges | `--radius:10px`, `--radius-lg:14px` — match `klikk` and `klikk-lg` Tailwind tokens in `tailwind.config.js` | **ACCEPTABLE DIVERGENCE** |
| Unsaved changes warning | `beforeRouteLeave` guard + dirty state | Not applicable — all views are read-only mockup data; no forms with real saves | N/A |
| Loading states | Skeleton loaders; no "Loading…" text | No loading states at all (static mock data) | N/A (preview only) |
| Error handling | Toast on API failure | No API calls (static mock) | N/A (preview only) |

---

## Findings by severity

### Must fix

**F-01 — Phosphor Icons loaded and used throughout (ALL files)**

Phosphor was removed from the admin app in April 2026 and is banned. The agent preview:
1. Injects the Phosphor web font at runtime via `document.createElement('script')` (`AgentPreviewLayout.vue` L97–103, `src='https://unpkg.com/@phosphor-icons/web@2.1.1'`).
2. Uses `<i class="ph ph-*">` in every single file — the layout, all 15 view SFCs.

This is not a minor drift — it is the entire icon implementation. Every `<i class="ph ph-*">` must be replaced with a Lucide SVG component (`lucide-vue-next`) before this shell can graduate out of "prototype" status.

Files: all 15 views + `AgentPreviewLayout.vue`.

---

**F-02 — Zero `scope="col"` on table headers (ALL tabular views)**

Every `<th>` in every data table omits `scope="col"`, violating both the design standard and WCAG 2.1 Success Criterion 1.3.1. Affects:

- `AgentOverviewView.vue` — list-view table L530–531
- `AgentPropertiesView.vue` — L127
- `AgentLeasesView.vue` — L66
- `AgentDepositsView.vue` — L53
- `AgentMaintenanceView.vue` — table view L182
- `AgentContactsView.vue` — L93
- `AgentVaultView.vue` — L68
- `AgentSuppliersView.vue` — L81
- `AgentSalesView.vue` — L80
- `AgentInspectionsView.vue` — L95
- `AgentPropertyView.vue` — 5 nested data tables (lease clauses, tenants, prev tenants, inspections, maintenance, documents)
- `AgentMaintenanceTicketView.vue` — quote line-item table L178

Fix: add `scope="col"` to every `<th>` element.

---

**F-03 — Tabs use local state only — no `?tab=` query param (`AgentPropertyView`, `AgentMaintenanceTicketView`)**

Both detail-view SFCs have multi-tab interfaces driven by `const tab = ref<Tab>('overview')` with no URL sync. The design standard requires `?tab=<key>` + `VALID_SECTIONS` + `normaliseTab()` so tabs are linkable and back-button friendly.

- `AgentPropertyView.vue` L11: `const tab = ref<Tab>('overview')` — 9 tabs, no router sync
- `AgentMaintenanceTicketView.vue` L11: `const tab = ref<Tab>('overview')` — 7 tabs, no router sync

`AgentOverviewView` (`view` toggle Events/Board/List) and `AgentSettingsView` (`active` section) are also local-only but are view-selectors rather than deep-linkable detail tabs, making them lower priority.

Fix: Implement `?tab=` pattern with `VALID_SECTIONS` + `normaliseTab()` in both detail views.

---

**F-04 — Color-only status indication in `AgentContactsView` (WCAG failure)**

The POPIA and FICA columns (`AgentContactsView.vue` L106–108) render icon-only status:

```html
<i :class="`ph ${statusIcon(r.popia)}`" :style="`color:${statusColor(r.popia)}`" />
```

There is no visible text label. A screen reader receives a bare `<i>` with no `aria-label`. Two violations in one: Phosphor icon + color-only indication.

Fix: Add text label (e.g. "Verified" / "Needs attention" / "Pending") alongside the icon, or add `aria-label` to the icon element.

---

**F-05 — Icon-only action buttons with no `aria-label`**

The topbar in `AgentPreviewLayout.vue` renders icon-only buttons for Help and Notifications (L152–156):

```html
<button class="icon-btn" title="Help" type="button"><i class="ph ph-question" /></button>
<button class="icon-btn" title="Notifications" type="button">
  <i class="ph ph-bell" />
```

`title` attributes are not accessible on touch devices and are not announced reliably by screen readers. Both need `aria-label`.

Also across the views, inline `<button class="btn ghost">` with only an `<i>` child and no text appear in multiple places (e.g. `AgentPropertyView` messages tab "→" buttons at L335; `AgentMessagingView` "God view" button only has text, but `AgentSuppliersView` has inline table-action buttons).

Fix: Add `aria-label` to every icon-only button.

---

### Should fix

**F-06 — Hardcoded hex literals in view scripts/templates (6 views)**

The agent-shell CSS vars exist for all standard colors. These views bypass them and use raw hex:

| File | Location | Value | Should be |
|------|----------|-------|-----------|
| `AgentOverviewView.vue` | L130, L198, L204 | `#8B5CF6`, `#D97706`, `#14B8A6`, `#EA580C` | No CSS var defined — needs `--purple` or `--indigo` token |
| `AgentContactsView.vue` | L44, L51 | `#7C3AED` (role badge style) | Same — missing purple token |
| `AgentMaintenanceTicketView.vue` | L109, L203, L337 | `#7C3AED`, `#F3E8FF` | Missing purple token |
| `AgentMaintenanceView.vue` | L97, L206 | `var(--warn)` (border-color inline), `#7C3AED`, `#F3E8FF` | Missing purple token |
| `AgentMessagingView.vue` | inline style L339 | `#DCF8C6` (WhatsApp green bubble) | Intentional product color — document it |
| `AgentBiView.vue` | L103 | Passes `a.color` which contains `var(--ok)`, `var(--warn)`, `var(--danger)` as strings | These are `style` bindings using valid CSS vars — acceptable |

The purple/violet color for Gate status (`#7C3AED`, `#8B5CF6`) is a genuine product semantic color not yet in the agent-shell token set. It should be added as `--gate: #7C3AED; --gate-soft: #F3E8FF;` to `agent-shell.css` and referenced consistently.

---

**F-07 — `font-size:10px` below readable-text floor on photo thumbnail labels**

- `AgentPropertyView.vue` L236–241: 6 photo grid labels use `font-size:10px`
- `AgentMaintenanceTicketView.vue` L127–132: 3 overview tab photo labels use `font-size:10px`

The standard's floor for readable content is `text-xs` (12px) or `text-micro` (11px) for decorative. Photo room labels ("Kitchen", "Bathroom", "Element") are readable content. They should be `font-size:11px` minimum (matching `.text-micro` equivalent in the agent shell).

---

**F-08 — Missing `aria-haspopup` on avatar button; no a11y on agency switcher**

`AgentPreviewLayout.vue`:
- Avatar button (L160–164): has `aria-expanded` but is missing `aria-haspopup="menu"`.
- Agency switcher button (L141–145): a plain `<button>` with Phosphor icons and static text. It has no open/close behavior, no `aria-expanded`, no `aria-haspopup`. Either implement the dropdown or remove the chevron affordance to avoid false affordance.

---

**F-09 — `href="#"` and `javascript:void(0)` links in 4 views**

- `AgentPropertyView.vue` L21–22: `href="javascript:void(0)"` for breadcrumb navigation (should be `<RouterLink>` or `<button>`)
- `AgentSuppliersView.vue` L55: same breadcrumb pattern
- `AgentMaintenanceTicketView.vue` L19: same
- `AgentPropertyView.vue` L225, L226 (inspection tab): `<a href="#">` links with no target — these are static mock links, but they will cause keyboard/screen-reader confusion (anchor with `href="#"` scrolls to top)

Fix: Replace `javascript:void(0)` breadcrumbs with `<RouterLink>` or `@click.prevent`. Replace placeholder `href="#"` with `type="button"` buttons or remove the `<a>` wrapper until wired.

---

**F-10 — Empty state pattern is incomplete across all list views**

Only `AgentMaintenanceTicketView.vue` (invoice tab) has an empty state at all. Every other list view (`AgentLeasesView`, `AgentDepositsView`, `AgentPropertiesView`, etc.) has a bare `<table class="data">` with no v-if/v-else empty state branch. The design standard requires:
1. A "no items yet" empty state with a create CTA.
2. A "no matches" empty state when filters are active.

This is a preview limitation (static data always populates) but the pattern should be scaffolded before wiring real data.

---

**F-11 — View-toggle and settings navigation use local state (`AgentSettingsView`, `AgentMaintenanceView`)**

`AgentSettingsView.vue` L41: `const active = ref('profile')` — the settings panel switcher does not sync to the URL. A user linking directly to `/agent/settings?section=popia` would land on the Profile panel, not POPIA.

`AgentMaintenanceView.vue` L10: `const view = ref<'kanban' | 'table' | 'calendar'>('kanban')` — view state lost on navigation. Not as critical as the detail tabs (F-03) but should be wired.

---

**F-12 — `.nav-item` in `AgentSettingsView` has overriding inline styles that strip border-radius**

`AgentSettingsView.vue` L82: `style="border-radius:0;margin:0;padding:10px 16px"` overrides the `.nav-item` global radius via inline style. This produces flat square corners on the settings nav buttons while all other nav items round correctly. The settings nav has its own `.settings-nav` container with `border-radius: var(--radius-lg) 0 0 var(--radius-lg)`, so the intent is to have edge-flush items — but the override should live in `.agent-shell .settings-nav .nav-item` CSS rather than inline.

---

### Nice to have

**F-13 — `AgentBiView` bar labels use `font-size:10px`**

`AgentBiView.vue` CSS (L134): `.bi-bar-labels { font-size: 10px }`. These are chart axis labels (month abbreviations), which are closer to decorative micro-labels than readable content. The distinction is borderline — upgrade to 11px (`text-micro` equivalent) if any bar label needs to be read independently.

---

**F-14 — `AgentOverviewView` view-toggle is not keyboard accessible**

The Events/Board/List segmented control (`AgentOverviewView.vue` L239–247) uses `<button>` elements correctly, but the active state is conveyed only by the `.active` CSS class (background flip). There is no `aria-pressed="true/false"` on the toggle buttons. Users navigating by keyboard cannot determine which view is selected.

Fix: Add `:aria-pressed="view === 'events'"` etc. to each toggle button.

---

**F-15 — Inline `style="margin-top:14px"` and similar one-off spacing on `.pcard` stacking**

Across `AgentPropertyView.vue` and `AgentMaintenanceTicketView.vue`, adjacent `.pcard` elements use `style="margin-top:14px"` inline rather than wrapping in a `space-y-*` or `gap` container. This is a maintenance concern rather than a standards violation (the agent shell doesn't use Tailwind utilities for layout), but it makes the stacking rhythm inconsistent — some gaps are 14px, others are 20px.

---

**F-16 — `AgentMessagingView` chat pane: WhatsApp-green bubble color (`#DCF8C6`) is hardcoded**

`AgentMessagingView.vue` CSS L205: `.bubble.in { background: #DCF8C6 }`. This is an intentional product color (WhatsApp brand green for inbound messages). It should be documented as intentional with a comment, and ideally extracted to a CSS var (`--channel-whatsapp: #DCF8C6`) so it can be theme-toggled in dark mode later.

---

**F-17 — No `<nav>` landmark on the sidebar**

`AgentPreviewLayout.vue` L219: `<nav class="sidebar">` — this is correct and already uses a `<nav>` element. However, there is no `aria-label` distinguishing it from other potential nav landmarks on the page (e.g. breadcrumb navigation inside views). Add `aria-label="Main navigation"` to the sidebar `<nav>`.

---

**F-18 — `AgentOverviewView` board view kanban cards have no `role` or keyboard interaction**

The kanban cards in the Board view (`AgentOverviewView.vue` L380–519) use `<div class="card" @click="gotoProperty">` — a div with a click handler but no `role="button"`, no `tabindex="0"`, and no keyboard event handler. They are completely inaccessible via keyboard.

Fix: Use `<button>` elements or add `role="button"` + `tabindex="0"` + `@keydown.enter="gotoProperty"` + `@keydown.space.prevent="gotoProperty"`.

---

### Acceptable divergence (by design)

The following are intentional differences between the agent-preview shell and the main admin design system. They reflect the `agent-shell` being a **parallel UI layer**, not a broken port.

| # | What | Why it's acceptable |
|---|------|---------------------|
| D-01 | **DM Sans 14px base** vs Inter 15px in main app | Agent shell is its own product concept with a distinct visual personality. DM Sans 14px is a deliberate design choice for the operations console. The agent shell CSS is self-contained under `.agent-shell`. |
| D-02 | **Fraunces for headings** | Fraunces (display serif) is used for h1–h4 in the agent shell, consistent with the prototype origin and the brand font stack in `tailwind.config.js`. This is not available in the main admin (Inter-only), but it is within the brand. |
| D-03 | **Own `.btn` classes** vs main `.btn-primary` / `.btn-ghost` | The agent shell defines `.btn`, `.btn.primary`, `.btn.ghost`, `.btn.accent` scoped under `.agent-shell`. These have equivalent semantics and are consistently applied. The main app's `btn-*` classes are Tailwind-based and would collide if used here without the Tailwind compiler. |
| D-04 | **Own `.card`, `.badge`, `.table-wrap` etc.** | Same rationale — CSS-module approach scoped to `.agent-shell`. Values (radii, shadow, border) are derived from the same brand tokens. |
| D-05 | **`PageHeader` component not used** | The agent preview has its own `.page-header` HTML structure (breadcrumb + h1 row + actions row) that matches the visual pattern of `PageHeader.vue`. This is intentional and consistent across all 15 views. |
| D-06 | **JetBrains Mono for data/code** | Used for monetary values, timestamps, audit log entries, and hash codes — appropriate for an operations console that surfaces financial and technical data. |
| D-07 | **Shadow token via CSS var** | `--shadow: 0 1px 2px rgba(26,26,46,.04), 0 2px 8px rgba(26,26,46,.04)` matches `klikk-soft` in `tailwind.config.js` exactly. Token-equivalent. |
| D-08 | **`--radius: 10px` / `--radius-lg: 14px`** | Matches `klikk` and `klikk-lg` in `tailwind.config.js`. Token-equivalent. |
| D-09 | **Static mock data, no Pinia stores** | Expected for a preview — wiring to real data is post-preview work. Loading/error states are therefore not required now. |
| D-10 | **Grid layout without `max-w-[1400px]` wrapper** | `AppLayout` is not in scope here. The agent shell renders its own full-viewport `grid(248px 1fr)`. An inner `max-w-[1400px]` container would be wrong for this layout. |
| D-11 | **Alert strip pattern** | `.alert-strip` and `.alert-strip.danger` are patterns not in the main admin. They are semantically appropriate (they fill the role of a toast/banner) and are consistently styled against the agent-shell tokens. They should be considered for promotion into the shared component library. |

---

## Recommendations

### Priority 1 — Before this shell can go to users

1. **Replace all Phosphor icons with Lucide.** This is the single largest change but is mechanical — map each `ph-*` icon to its Lucide equivalent and replace `<i class="ph ph-*">` with `<IconName :size="18" />`. A mapping table is available in the Lucide docs. Estimated scope: ~150–200 icon usages across 16 files.

2. **Add `scope="col"` to all `<th>` elements.** Grep-and-fix — every `<th>` in the agent-preview views needs `scope="col"`. Roughly 60 `<th>` tags across 12 files.

3. **Add `aria-label` to icon-only buttons.** Search for `class="icon-btn"` and any `<button>` containing only an `<i>` child. Add `aria-label="[action]"` to each.

4. **Fix the POPIA/FICA icon-only columns in `AgentContactsView`.** Add a visually hidden label or combine icon + short text.

5. **Wire `?tab=` in `AgentPropertyView` and `AgentMaintenanceTicketView`.** Use the `VALID_SECTIONS` / `normaliseTab()` pattern from `PropertyDetailView.vue` as the template.

### Priority 2 — Before this shell replaces the current admin for agents

6. **Define `--gate` / `--gate-soft` CSS vars** in `agent-shell.css` for the purple Gate status color and replace all `#7C3AED` / `#F3E8FF` / `#8B5CF6` literals with the variable.

7. **Scaffold empty state branches** in all list views. The `EmptyState` component can be used or the agent-shell `.empty` pattern can be extended — just ensure each list has a `v-else` branch with a CTA.

8. **Replace `javascript:void(0)` breadcrumb patterns** with `<RouterLink>` or `@click.prevent` handlers in `AgentPropertyView`, `AgentSuppliersView`, `AgentMaintenanceTicketView`.

9. **Bump photo thumbnail label `font-size` to 11px** (`AgentPropertyView` L236–241, `AgentMaintenanceTicketView` L127–132).

10. **Add `aria-pressed` to view-toggle buttons** in `AgentOverviewView` and `AgentMaintenanceView`.

### Priority 3 — Nice to have / before formal design review

11. Add `aria-label="Main navigation"` to sidebar `<nav>` in `AgentPreviewLayout.vue`.
12. Add `aria-haspopup="menu"` to the avatar button.
13. Make kanban card divs keyboard-accessible (role + tabindex + keydown handlers) in the Board view.
14. Extract `#DCF8C6` WhatsApp bubble color to a CSS var with a comment.
15. Move the `.nav-item` style override in `AgentSettingsView` from inline to `.agent-shell .settings-nav .nav-item` CSS rule.
16. Consider promoting the `.alert-strip` pattern to the shared design system — it fills a gap the main admin currently addresses only with toast notifications.
