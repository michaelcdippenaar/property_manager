---
name: klikk-design-standard
description: >
  Enforce the Klikk design standard when building or modifying UI components in the admin Vue 3 app.
  Trigger for: "design standard", "UI standard", "follow the design", "match the design", "style this",
  "new page", "new view", "new component", "build a form", "build a table", "add a page", "create view",
  "UI consistency", "design system", "klikk design", or any task that involves creating or restyling
  Vue components in the admin app.
---

# Klikk Design Standard

Enforces the Klikk admin design system. Derived from the UX/UI audit at `admin/system_documentation/claude_opus_ux_ui_audit_2026-03-25.md` plus patterns codified in the polishing sessions of Q1–Q2 2026.

**Always read the audit document for view-specific findings before making design decisions.**

## Tech Stack

- **Framework:** Vue 3 + TypeScript (Composition API `<script setup>`)
- **Styling:** Tailwind CSS v3 + custom component classes in `admin/src/assets/main.css`
- **Icons:** **`lucide-vue-next` only** — Phosphor is banned (removed April 2026). Global stroke-width 1.75.
- **Font:** Inter (400, 500, 600, 700). **Base size 15px**, not 16px.
- **Config:** `admin/tailwind.config.js`

## Top rules (read first)

1. **No hardcoded tokens — ever.** (HARD RULE)
   - **Colors:** always use Tailwind tokens from `admin/tailwind.config.js` (`navy`, `accent`, `success-*`, `danger-*`, `warning-*`, `info-*`, `surface`, `gray-*`). NEVER hex literals (`#2B2D6E`), arbitrary values (`bg-[#2B2D6E]`, `text-[#333]`), or raw Tailwind palette names that bypass the brand tokens (use `bg-navy`, not `bg-indigo-900`; use `text-danger-600`, not `text-red-600`).
   - **Font-sizes:** always use Tailwind size utilities (`text-xs`, `text-sm`, `text-base`, `text-lg`, `text-xl`, ...) or the component classes in `admin/src/assets/main.css` (`.text-micro`, `.text-muted`, `.page-title`, `.stat-value`, `.label-upper`). NEVER arbitrary values like `text-[10px]`, `text-[11px]`, `text-[13px]`.
   - **Shadows / spacing / radii:** prefer tokens — `shadow-soft` / `shadow-lifted` / `shadow-floating` CSS vars, standard Tailwind spacing (`p-4`, `gap-3`, `space-y-6`) and radii (`rounded-lg`, `rounded-xl`, `rounded-full`). Arbitrary values only when no token fits, and a comment must justify it.
2. **Every view starts with `<PageHeader>`** — never hand-roll `<h1>` + breadcrumb markup.
3. **No outer `max-w-*` / container inside a view** — `AppLayout` clamps to `max-w-[1400px]`.
4. **Lucide only.** 16px in buttons, 18px in nav, 14px in section-card headers.
5. **Group content in section-cards** (`<section class="card overflow-hidden">` + standard header row).
6. **Tabs use `?tab=<key>`** with a `VALID_SECTIONS` whitelist + `normaliseTab()` alias helper.
7. **Empty states split** "no matches" (Clear filters) vs "no items" (Add CTA) on filtered lists.
8. **Dropdowns:** `aria-haspopup`, `aria-expanded`, click-toggle, Escape + outside-click handlers.
9. **Floor for readable text is `text-xs` (12px)** — never `text-[10px]`/`text-[11px]` for real content. The only sanctioned exceptions are the role-pill chip and nav badge counters (decorative micro-labels).

## When to use this vs related skills

| Instead of | Use this when |
|------------|---------------|
| `klikk-design-mobile-ux` | Building admin Vue 3 components, not Quasar mobile |
| `klikk-design-frontend-taste` | Enforcing specific component conventions, not architecture review |

---

## Reference Index

| Topic | File |
|-------|------|
| `PageHeader`, `Breadcrumb`, `BaseModal`, `BaseDrawer`, `EmptyState`, `SearchInput`, `FilterPills`, `ConfirmDialog` APIs | [shared-components.md](references/shared-components.md) |
| 5-layer nav hierarchy (role pill → top-nav active pill → dropdown sitemap → breadcrumb → H1/tabs), filled-pill active state, pill-chip brand logo, `max-w-[1400px]` container | [nav-hierarchy.md](references/nav-hierarchy.md) |
| Section-card pattern, `?tab=` query param + `VALID_SECTIONS` / `normaliseTab()`, empty-state split, dropdown a11y baseline | [view-patterns.md](references/view-patterns.md) |
| Lucide-only policy, stroke-width 1.75, size chart per context | [icons.md](references/icons.md) |
| Color tokens, typography (base 15px, `text-micro` floor), spacing, borders, buttons, inputs, cards, badges, tables, filter pills | [design-tokens.md](references/design-tokens.md) |
| Page layout pattern (PageHeader-first), content container, mobile responsive rules | [layout-patterns.md](references/layout-patterns.md) |
| ARIA labels, semantic HTML, focus management, form validation, destructive actions, loading states | [accessibility.md](references/accessibility.md) |
| Required components, shared utilities, new view checklist, design principles | [new-view-checklist.md](references/new-view-checklist.md) |
| Anti-patterns checklist (Phosphor, `text-[10px]`, hover-only dropdowns, bare h1/breadcrumbs, extra max-w wrappers, etc.) | [anti-patterns.md](references/anti-patterns.md) |

---

## Key Files

| File | Purpose |
|------|---------|
| `admin/tailwind.config.js` | Color tokens, font config |
| `admin/src/assets/main.css` | Component classes (buttons, inputs, cards, badges, tables, `.header-nav-link-active`, `.lucide` stroke-width) |
| `admin/src/components/AppLayout.vue` | Layout shell — header nav, role pill, `max-w-[1400px]` container, dropdown a11y reference |
| `admin/src/components/PageHeader.vue` | **Every top-level view uses this** |
| `admin/src/components/Breadcrumb.vue` | Breadcrumb rendering (usually via `PageHeader.crumbs`) |
| `admin/src/components/BaseModal.vue` | Standard modal dialog |
| `admin/src/components/BaseDrawer.vue` | Standard side-panel/drawer |
| `admin/src/components/EmptyState.vue` | Empty state with CTA |
| `admin/src/components/SearchInput.vue` | Reusable search input |
| `admin/src/components/FilterPills.vue` | Filter toggle pills |
| `admin/src/views/properties/PropertyDetailView.vue` | Canonical example: `?tab=` pattern, section-card pattern |
| `admin/src/views/properties/PropertiesView.vue` | Canonical example: empty-state split |
| `admin/system_documentation/claude_opus_ux_ui_audit_2026-03-25.md` | Full UX/UI audit |
