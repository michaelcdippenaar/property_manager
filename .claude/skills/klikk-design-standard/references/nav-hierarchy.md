# 5-Layer Navigation Hierarchy (Xero-inspired)

Klikk's admin uses a five-layer nav stack so users always know where they are. Every layer has a defined home and shouldn't be reinvented per view.

| # | Layer | Lives in | Visual treatment |
|---|-------|----------|------------------|
| 1 | **Role pill** | `AppLayout.vue` logo cluster | `bg-accent/15 text-accent text-[10px] font-bold tracking-[0.12em] uppercase` chip next to the `Klikk.` wordmark. Shows the active dashboard (Agent / Owner / Supplier). |
| 2 | **Top-nav active state** | `AppLayout.vue` primary nav | Filled pill — `.header-nav-link-active` in `main.css`: white text on `rgba(255,255,255,0.12)` background. Only one section is "active" at a time, chosen by `isSectionActive()`. |
| 3 | **Dropdown sitemap** | `AppLayout.vue` per-section dropdown | `w-72` panel with `sublabel` intro, icon + label + description rows, optional footer link. Each section owns its subpages here, not in a secondary bar. |
| 4 | **Breadcrumb** | `PageHeader.vue` (via `crumbs` prop) → `Breadcrumb.vue` | Chevron-separated trail; last item is `aria-current="page"` and non-clickable. |
| 5 | **H1 + in-page filter tabs** | View template via `PageHeader` title and (optionally) an `<under-title>` tab row | H1 from `PageHeader`; tabs are either `FilterPills` or a `flex gap-1 border-b ... overflow-x-auto` tab strip driven by a `?tab=` query param. |

## Rules

- The role pill in the header is the **only** place we label the active portal. Don't duplicate that label inside views.
- Never paint a second active state on a top-nav link while inside a dropdown child — the parent stays active, and the dropdown itself shows the sub-active via `bg-navy/5` + `text-navy`.
- Dropdowns must be both hover- and click-openable (see `accessibility.md`). Mobile uses an entirely different slide-out accordion.
- Breadcrumbs start with the section landing page, not "Home". The final crumb is the current page's title (matches the H1).
- If a view has internal tabs (e.g. Property Detail → Overview / Leases / Agency), drive them from `?tab=<key>` with a `VALID_SECTIONS` whitelist — see [view-patterns.md](view-patterns.md).

## Filled-pill top nav

Defined in `admin/src/assets/main.css`:

```css
.header-nav-link {
  @apply flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium cursor-pointer;
  color: rgba(255, 255, 255, 0.55);
}
.header-nav-link-active {
  color: white !important;
  background: rgba(255, 255, 255, 0.12);
}
```

Apply with `:class="isActive ? 'header-nav-link-active' : ''"` on the `.header-nav-link` element. Do not restyle per-view.

## Pill-chip brand logo

The logo is a wordmark + role chip, not an image:

```html
<RouterLink :to="auth.homeRoute" class="flex items-center gap-2 mr-3" aria-label="Home">
  <span class="font-extrabold text-white text-lg tracking-tight leading-none">
    Klikk<span class="text-accent">.</span>
  </span>
  <span
    v-if="dashboardLabel"
    class="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded-md
           bg-accent/15 text-accent text-[10px] font-bold tracking-[0.12em] uppercase leading-none"
  >
    {{ dashboardLabel }}
  </span>
</RouterLink>
```

`dashboardLabel` comes from `useAuthStore()` and flips per portal. Keep the accent dot in `Klikk.` — it's the logomark.

## Content container

All authenticated views render inside a single centred max-width container in `AppLayout.vue`:

```html
<div class="max-w-[1400px] mx-auto p-4 sm:p-6">
  <RouterView />
</div>
```

**Never** add an outer `max-w-*` or `container` wrapper inside a view — the layout already handles it. Use full-width (`w-full`) and let the parent clamp.
