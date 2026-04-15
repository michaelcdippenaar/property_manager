# New View Checklist & Shared Utilities

---

## Required Components

Always use these shared components — never create one-off alternatives:

| Component | Usage | Notes |
|-----------|-------|-------|
| `BaseModal` | All modal dialogs | Must include `role="dialog"`, `aria-modal="true"`, focus trapping |
| `BaseDrawer` | Side panels, detail views | Must include `role="dialog"`, `aria-modal="true"` |
| `EmptyState` | Zero-data states | Always include an action CTA button |
| `SearchInput` | All search bars | Never use custom inline search inputs |
| `FilterPills` | All filter toggles | Consistent pill styling |
| `ToastContainer` | Via `useToast()` composable | Global — already in AppLayout |
| `ConfirmDialog` | All destructive actions | **Never use `window.confirm()`** |

---

## Shared Utilities — No Duplication

Always import from these locations, never redefine in views:

| Function | Location | Used By |
|----------|----------|---------|
| `formatDate()` | `src/utils/formatters.ts` | 6+ views |
| `initials()` | `src/utils/formatters.ts` | 4+ views |
| `priorityBadge()` | `src/composables/useStatusBadges.ts` | 4+ views |
| `statusBadge()` | `src/composables/useStatusBadges.ts` | 5+ views |

---

## New View Checklist

When creating a new page/view, verify all of:

- [ ] Uses **`PageHeader`** component (never hand-rolls `<h1>` + Breadcrumb) with `title`, `subtitle`, `crumbs`, and `#actions` slot as needed
- [ ] No outer `max-w-*` / container wrapper — relies on `AppLayout`'s `max-w-[1400px]`
- [ ] Content grouped in section-cards (`<section class="card overflow-hidden">` with `px-5 py-3 border-b border-gray-100` header row) where appropriate — see [view-patterns.md](view-patterns.md)
- [ ] Internal tabs driven by `?tab=<key>` + `VALID_SECTIONS` + `normaliseTab()` — see [view-patterns.md](view-patterns.md)
- [ ] Empty states split "no matches" (Clear filters CTA) vs "no items" (primary Add CTA) for filtered lists
- [ ] Content wrapped in `card` components
- [ ] Data displayed in `table-wrap` tables with `scope="col"` headers
- [ ] Search/filter bar above table when applicable (`SearchInput` / `FilterPills`)
- [ ] Empty state with `EmptyState` component and action CTA when no data
- [ ] Loading state with skeleton loaders (never "Loading..." text)
- [ ] Error handling with `toast.error()` on every API failure
- [ ] Status shown with `badge-*` classes (text labels, not color-only)
- [ ] Forms use `label` + `input` pattern with `space-y-4` and field-level validation
- [ ] Buttons use `btn-*` classes (primary for main action, ghost for secondary)
- [ ] All icon-only buttons have `aria-label`
- [ ] Destructive actions use `ConfirmDialog` (never `window.confirm()`)
- [ ] Icons from **Lucide only** (`lucide-vue-next`) — never Phosphor — at correct sizes (16px in buttons, 18px in nav, 14px in section-card headers). Global stroke-width 1.75.
- [ ] Dropdowns have `aria-haspopup`, `aria-expanded`, click-toggle (not hover-only), Escape + outside-click handlers
- [ ] No hardcoded colors — all from design tokens
- [ ] Shared utilities imported, not redefined
- [ ] Page header uses `flex flex-col sm:flex-row` stacking pattern
- [ ] Tables wrapped with `<div class="table-scroll">`
- [ ] Grids use mobile-first breakpoints (`grid-cols-1 sm:grid-cols-2 lg:grid-cols-N`)
- [ ] Tab/filter bars have `overflow-x-auto` for mobile scroll
- [ ] No hardcoded widths — use `w-full sm:w-[Npx]` pattern
- [ ] No hover-only interactions — click/tap handlers included
- [ ] Unsaved changes warning if form view

---

## Design Principles

1. **Whitespace** — generous padding and margins; never cram elements
2. **Hierarchy** — page title > section heading > card heading > body text; use weight and size
3. **Consistency** — always use pre-defined component classes; never create one-off styles
4. **Tables for data** — `table-wrap` for listing items; cards for grouping content or stats
5. **Actions placement** — primary action top-right of page header; secondary as ghost buttons in rows
6. **Forms** — labels above inputs, vertical stack with `space-y-4`; group related fields in cards
7. **Feedback** — badges for status, toasts for actions, inline errors for validation; no silent failures
8. **Transitions** — 200-300ms for hover/focus; use `transition-colors` on interactive elements
