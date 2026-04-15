# Layout Patterns & Mobile Responsive Design

---

## Content container

`AppLayout.vue` renders every authenticated view inside:

```html
<div class="max-w-[1400px] mx-auto p-4 sm:p-6">
  <RouterView />
</div>
```

**Do not add another outer `max-w-*`, `container`, or padding wrapper inside a view.** Use `w-full` and let the shell clamp. Extra wrappers cause double-padding and misaligned section-cards.

---

## Page Layout Pattern

Every page/view MUST start with `PageHeader` (see [shared-components.md](shared-components.md)). Do not hand-roll the header markup.

```vue
<template>
  <PageHeader
    title="Properties"
    subtitle="Manage your rental portfolio."
    :crumbs="[{ label: 'Properties' }]"
  >
    <template #actions>
      <button class="btn-primary flex-shrink-0">
        <Plus :size="16" /> Add Property
      </button>
    </template>
  </PageHeader>

  <!-- Content -->
  <div class="card p-0">
    <!-- Optional: search/filter bar -->
    <div class="p-4 border-b border-gray-200">
      <SearchInput v-model="search" placeholder="Search..." />
    </div>

    <!-- Data table — always wrapped for mobile scroll -->
    <div class="table-scroll">
      <table class="table-wrap">...</table>
    </div>

    <!-- Or empty state -->
    <EmptyState v-if="!items.length && !loading"
      icon="FileText"
      title="No items found"
      description="Create your first item to get started.">
      <button class="btn-primary" @click="create">Create Item</button>
    </EmptyState>
  </div>
</template>
```

---

## Layout Structure

| Element | Spec |
|---------|------|
| **Header bar** | Fixed 64px height (`h-16`), glassmorphism navy bg, horizontal nav (desktop) |
| **Mobile nav** | Hamburger (`sm:hidden`), slide-out panel with accordion sections |
| **Content area** | `surface` (#F5F5F8) bg, `p-4 sm:p-6` padding, scrollable |
| **Nav links** | `header-nav-link` / `header-nav-link-active` classes (desktop) |
| **Sidebar nav** | `sidebar-link` / `sidebar-link-active` / `sidebar-section-label` (mobile nav panel) |
| **Nav icons** | Lucide 16px in nav and buttons |
| **AI FAB** | `fixed bottom-4 right-4 sm:bottom-6 sm:right-6` |

---

## Mobile Responsive Design

**Approach:** mobile-first with `sm:` (640px) as primary breakpoint.

### Navigation

- **Desktop (≥640px):** Horizontal top nav with hover+click dropdown menus
- **Mobile (<640px):** Hamburger + slide-out nav panel (`w-72`) with accordion sections
- Desktop nav hidden on mobile: `hidden sm:flex`
- Mobile menu auto-closes on route navigation via `watch(route.path)`
- Dropdowns support both hover (desktop) and click/tap (touch)

### Responsive Patterns

**Page headers — stack vertically on mobile:**
```html
<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
```

**Tab bars — horizontally scrollable on mobile:**
```html
<div class="flex gap-1 border-b border-gray-200 overflow-x-auto">
```

**Grids — reduce columns on mobile:**
```html
<!-- Dashboard pipeline: 2→3→5 columns -->
<div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">

<!-- Stat cards: 2→4 columns -->
<div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
```

**Modals/Drawers — full-width on mobile:**
- Use `sm:max-w-md` (not `max-w-md`) — fills screen on mobile
- Reduced internal padding: `px-4 py-3 sm:px-6 sm:py-4`

**Buttons — touch-friendly:**
- `.btn` has `min-height: 44px` on mobile (Apple HIG)
- `.btn-sm` has `min-height: 38px` on mobile

---

## Rules for New Views

1. **Never** use `flex items-center justify-between` for page headers — always `flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3`
2. **Never** use hardcoded `grid-cols-N` — start with mobile: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-N`
3. **Always** wrap tables with `<div class="table-scroll">`
4. **Never** use hover-only interactions — always pair with click/tap handlers
5. **Use** `p-4 sm:p-6` for content padding
6. **Use** `hidden sm:block` to hide non-essential elements on mobile
7. **Tab/filter bars** must have `overflow-x-auto`
