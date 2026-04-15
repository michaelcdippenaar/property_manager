# View-Level Patterns

Patterns that apply to whole views (tabs, empty states, section grouping).

---

## Section-card pattern

Within a tab/view, group related content in a `<section>` using the card + header-row pattern. Canonical example: the **Agency** tab in `admin/src/views/properties/PropertyDetailView.vue`.

```html
<section class="card overflow-hidden">
  <div class="px-5 py-3 border-b border-gray-100 flex items-center gap-2">
    <FileSignature :size="14" class="text-navy" />
    <h3 class="text-xs font-semibold uppercase tracking-wide text-navy">Mandate</h3>
  </div>
  <div class="p-5">
    <!-- section body -->
  </div>
</section>
```

Rules:
- Always `card overflow-hidden` (the border-b on the header needs to butt against the card edge).
- Header row: `px-5 py-3 border-b border-gray-100 flex items-center gap-2`.
- Icon: **Lucide, 14px, `text-navy`**. No Phosphor.
- Label: `text-xs font-semibold uppercase tracking-wide text-navy`.
- Body: `p-5` (match the horizontal padding of the header).
- If the header has a trailing action, swap `gap-2` for `flex items-center justify-between gap-3` and put the action (usually `btn-ghost btn-sm text-navy`) on the right.
- Stack multiple section-cards in a tab with `space-y-6`.

---

## Tab query-param pattern

For views with internal tabs (Property Detail, Landlord Detail, etc.), drive the active tab from `?tab=<key>` rather than local state only. This keeps tabs linkable, back-button friendly, and backward-compatible when renamed.

Reference: `admin/src/views/properties/PropertyDetailView.vue`.

```ts
const VALID_SECTIONS = [
  'overview', 'information', 'leases', 'tenants',
  'agency', 'inventory', 'maintenance', 'advertising', 'documentation',
] as const
type SectionKey = typeof VALID_SECTIONS[number]

function normaliseTab(t: unknown): SectionKey | null {
  const raw = typeof t === 'string' ? t : ''
  // Backward-compat alias: ?tab=mandate → agency
  const aliased = raw === 'mandate' ? 'agency' : raw
  return (VALID_SECTIONS as readonly string[]).includes(aliased)
    ? (aliased as SectionKey)
    : null
}

const activeSection = ref<SectionKey>(normaliseTab(route.query.tab) ?? 'overview')

function setSection(key: SectionKey) {
  activeSection.value = key
  router.replace({ query: { ...route.query, tab: key } })
}

watch(() => route.query.tab, (t) => {
  const k = normaliseTab(t)
  if (k) activeSection.value = k
})
```

Rules:
- Define a `VALID_SECTIONS` `as const` tuple — used both as the runtime whitelist and the TS type source.
- Unknown/missing values fall through to the default section, never crash.
- Renames must land a backward-compat alias in `normaliseTab()` so existing deep links keep working (e.g. `mandate` → `agency`).
- Use `router.replace`, not `push` — tab switches shouldn't pollute history.
- Spread `...route.query` so the pattern composes with other query params.

---

## Empty state split

List views that have filters must distinguish **no matches for current filter** from **no items yet**. Reference: `admin/src/views/properties/PropertiesView.vue`.

```vue
<EmptyState
  v-else-if="hasActiveFilters"
  title="No matches"
  description="No properties match your current filters. Try clearing them to see everything."
  :icon="Building2"
>
  <button class="btn-secondary btn-sm" @click="clearFilters">Clear filters</button>
</EmptyState>

<EmptyState
  v-else
  title="No properties found"
  description="Add your first property to get started managing your portfolio."
  :icon="Building2"
>
  <button class="btn-primary btn-sm" @click="openAddModal">
    <Plus :size="14" /> Add Property
  </button>
</EmptyState>
```

Rules:
- `hasActiveFilters` is a computed that's true when *any* filter (search, pill, dropdown) is non-default.
- "No matches" offers **Clear filters** (secondary style) — never "Add".
- "No items yet" offers the **primary create CTA**.
- Use the same icon across both so the visual anchor stays consistent.

---

## Dropdown menu a11y baseline

Every clickable dropdown (user menu, nav dropdowns, row action menus) must meet this baseline. Reference implementation: `AppLayout.vue` section dropdowns.

Checklist:
- Trigger button has `:aria-haspopup="true"` and `:aria-expanded="openDropdown === key"`.
- Opens on **click**, not hover-only. Hover may *also* open on desktop, but keyboard/tap must work.
- `Escape` closes: register a `document` `keydown` listener in `onMounted`.
- Outside-click closes: register a `document` `click` listener that checks `target.closest('.dropdown-root')`.
- Both listeners are removed in `onUnmounted`.
- Mark the root with a class (`.dropdown-root`) or `data-*` attribute so the outside-click check is reliable.

```ts
function handleDocumentKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') openDropdown.value = null
}
function handleDocumentClick(e: MouseEvent) {
  if (openDropdown.value === null) return
  const target = e.target as HTMLElement | null
  if (!target || target.closest('.dropdown-root')) return
  openDropdown.value = null
}
onMounted(() => {
  document.addEventListener('keydown', handleDocumentKeydown)
  document.addEventListener('click', handleDocumentClick)
})
onUnmounted(() => {
  document.removeEventListener('keydown', handleDocumentKeydown)
  document.removeEventListener('click', handleDocumentClick)
})
```
