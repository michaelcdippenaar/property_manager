# Shared Components

Top-level shared components every new view must use instead of ad-hoc markup.

---

## `PageHeader` — `admin/src/components/PageHeader.vue`

**Use on every top-level view.** Replaces ad-hoc `<h1>` + breadcrumb markup.

### Props

| Prop | Type | Purpose |
|------|------|---------|
| `title` | `string` | H1 text (or use the `title` slot) |
| `subtitle` | `string` | Muted line below title (or `subtitle` slot) |
| `crumbs` | `BreadcrumbItem[]` | Rendered via `Breadcrumb` above title |
| `back` | `boolean` | Shows a left-chevron back button that calls `router.back()` |

### Slots

| Slot | Purpose |
|------|---------|
| `title` | Override title content |
| `title-adornment` | Inline chip/badge next to the H1 (e.g. status pill) |
| `subtitle` | Override subtitle content |
| `under-title` | Arbitrary content below the subtitle (tabs, meta row) |
| `actions` | Right-aligned action buttons (primary CTA, overflow menu) |

### Example

```vue
<PageHeader
  :title="property.address"
  :subtitle="property.complex"
  :crumbs="[
    { label: 'Properties', to: { name: 'properties' } },
    { label: property.address }
  ]"
  back
>
  <template #title-adornment>
    <span class="badge-green">Active</span>
  </template>
  <template #actions>
    <button class="btn-primary"><Pencil :size="16" /> Edit</button>
  </template>
</PageHeader>
```

**Never** hand-roll `<h1 class="text-xl font-bold...">` + Breadcrumb blocks at the top of a view. Use `PageHeader`.

---

## `Breadcrumb` — `admin/src/components/Breadcrumb.vue`

Renders `<nav aria-label="Breadcrumb">` with a chevron-separated ordered list.

```ts
export interface BreadcrumbItem {
  label: string
  to?: RouteLocationRaw   // last crumb omits `to` and becomes the current page
}
```

- Last item is rendered non-clickable with `aria-current="page"` and `font-semibold text-gray-700`.
- Inner chevrons are Lucide `ChevronRight` at 12px, `text-gray-300`, `aria-hidden`.
- Almost always used via `PageHeader`'s `crumbs` prop — only render directly for exotic layouts.

---

## Other shared components (keep using)

| Component | Usage | Notes |
|-----------|-------|-------|
| `BaseModal` | All modal dialogs | `role="dialog"`, `aria-modal="true"`, focus trapping |
| `BaseDrawer` | Side panels, detail views | `role="dialog"`, `aria-modal="true"` |
| `EmptyState` | Zero-data states | Always include an action CTA button |
| `SearchInput` | All search bars | Never inline custom search inputs |
| `FilterPills` | Filter toggles | Consistent pill styling |
| `ConfirmDialog` | Destructive actions | **Never** `window.confirm()` |
| `ToastContainer` | Via `useToast()` | Global; already mounted in AppLayout |
