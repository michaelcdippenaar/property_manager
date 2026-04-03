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

You are enforcing the Klikk design standard for the Tremly property management admin app. This standard is derived from the Klikk Admin Console (the reference implementation) and codified from the comprehensive UX/UI audit at `admin/system_documentation/claude_opus_ux_ui_audit_2026-03-25.md`.

**Always read that audit document for detailed view-by-view findings before making design decisions.**

## Tech Stack

- **Framework**: Vue 3 + TypeScript (Composition API with `<script setup>`)
- **Styling**: Tailwind CSS v3 with custom component classes in `admin/src/assets/main.css`
- **Icons**: Lucide Vue Next (`lucide-vue-next`)
- **Font**: Inter (400, 500, 600, 700)
- **Config**: `admin/tailwind.config.js`

## Design Tokens

### Colors (from `tailwind.config.js`)
| Token | Hex | Usage |
|-------|-----|-------|
| `navy` | `#2B2D6E` | Primary brand, active states, primary buttons, sidebar active |
| `navy-dark` | `#23255a` | Hover on primary elements |
| `navy-light` | `#3b3e8f` | Subtle primary highlights |
| `accent` | `#FF3D7F` | Secondary CTA, accent highlights, logo dot |
| `accent-light` | `#FF6B9D` | Hover on accent elements |
| `accent-dark` | `#E02D6B` | Active on accent elements |
| `surface` | `#F5F5F8` | Page/body background |
| `surface-secondary` | `#F0EFF8` | Alternative background |
| `white` | `#FFFFFF` | Cards, content areas, sidebar |
| `gray-50` to `gray-400` | Tailwind defaults | Borders, muted text, placeholders, table headers |
| `success-*` | Green scale (50/100/500/600/700) | Success states, active badges |
| `warning-*` | Amber scale (50/100/500/600/700) | Warning states, medium priority |
| `danger-*` | Red scale (50/100/500/600/700) | Error states, high priority, destructive actions |
| `info-*` | Blue scale (50/100/500/600/700) | Info states, links |

**CRITICAL: Never use hardcoded hex values or raw Tailwind colors (e.g., `bg-emerald-50`, `bg-pink-brand/10`, `bg-[#e8eaed]`). Always use the defined tokens above.**

Known hardcoded color violations to fix (from audit):
- DashboardView stat icons use mixed `bg-navy/10`, `bg-pink-brand/10`, `bg-amber-50`, `bg-emerald-50` — should use consistent `bg-{semantic}-50`
- LeaseBuilderView preview uses `bg-[#e8eaed]` — should be `bg-surface` or `bg-gray-100`
- TemplateEditorView uses raw hex throughout (`#2B2D6E`, `#FF3D7F`, `#111111`, `#d1d5db`, `#f3f4f6`, `#e8eaed`) — must use tokens
- CalendarView event colors: 7 hardcoded color pairs — should be centralized
- ESigningPanel status colors: hardcoded per-status objects — should use tokens

### Typography
| Element | Classes | Notes |
|---------|---------|-------|
| Page title | `text-xl font-bold text-gray-900` | Top of every page |
| Page subtitle | `text-sm text-gray-500 mt-1` | Below page title |
| Section heading | `text-base font-semibold text-gray-900` | Within cards/sections |
| Card heading | `text-sm font-semibold text-gray-700` | Card titles |
| Body text | `text-sm text-gray-700` | Default content text |
| Muted text | `text-xs text-gray-400` | Timestamps, hints, secondary info |
| Table header | `text-xs font-semibold text-gray-500 uppercase tracking-wider` | Column headers |
| Sidebar section | `sidebar-section-label` class | Section headers in nav |
| Micro label | `text-micro` (11px, weight 500) | Tiny labels, stat card labels |
| Form label | `label` class (`text-sm font-medium text-gray-700 mb-1`) | Above inputs |

**Audit finding:** Typography is inconsistent across views. Always use these exact patterns — never mix `text-micro`, `text-xs`, `text-sm` arbitrarily.

### Spacing
| Context | Value | Notes |
|---------|-------|-------|
| Page padding | `p-6` (24px) | Content area |
| Card padding | `p-4` to `p-6` | Internal card content |
| Between sections | `space-y-6` | Vertical section gaps |
| Between form fields | `space-y-4` | Within forms |
| Between inline items | `gap-2` to `gap-4` | Flex/grid children |
| Table cell padding | `px-4 py-3` | Consistent table cells |

**Audit finding:** Spacing values vary arbitrarily (`gap-2/3/4`, `p-4/5/6`). Standardize within each context.

### Borders & Shadows
| Element | Classes |
|---------|---------|
| Card | `rounded-xl border border-gray-200 shadow-sm` |
| Input | `rounded-lg border border-gray-300` |
| Button | `rounded-lg` |
| Badge | `rounded-full` |
| Modal | `rounded-xl shadow-xl` |

## Component Classes (from `main.css`)

### Buttons (`.btn-*`)
```html
<button class="btn-primary">Save</button>           <!-- Navy bg, white text -->
<button class="btn-ghost">Cancel</button>            <!-- White bg, gray border -->
<button class="btn-danger">Delete</button>           <!-- Danger-50 bg, danger text -->
<button class="btn-success">Approve</button>         <!-- Success-600 bg, white text -->
<button class="btn-accent">Sign Up</button>          <!-- Accent bg, white text -->
<button class="btn-primary btn-sm">Small</button>    <!-- Smaller padding -->
<button class="btn-ghost btn-xs">XS</button>         <!-- Extra small -->

<!-- Outlined action button (for export-style actions, matching Admin Console) -->
<button class="btn-ghost text-navy border-navy hover:bg-navy/5">Export</button>
```

**All buttons MUST include `disabled:opacity-50 disabled:cursor-not-allowed` behavior** (already in `.btn` base class).

### Inputs (`.input`)
```html
<div>
  <label class="label">Field Label <span class="text-danger-500">*</span></label>
  <input class="input" type="text" placeholder="Enter value..." />
</div>

<!-- With validation error -->
<div>
  <label class="label">Email</label>
  <input class="input input-error" type="email" />
  <p class="input-error-msg">Please enter a valid email.</p>
</div>

<!-- With help text -->
<div>
  <label class="label">Username</label>
  <input class="input" type="text" />
  <p class="input-help">This will be your display name.</p>
</div>
```

**CRITICAL (from audit): The `.input-error` and `.input-error-msg` classes exist but were not being used. Every form MUST use field-level validation with these classes.** Use or create a `useFormValidation()` composable that validates on blur and submit, applies `.input-error`, and shows `.input-error-msg`.

### Cards (`.card`)
```html
<div class="card p-6">
  <h2 class="text-base font-semibold text-gray-900 mb-4">Section Title</h2>
  <!-- content -->
</div>

<!-- Stat card (dashboard style) -->
<div class="card p-6">
  <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Properties</p>
  <p class="text-2xl font-bold text-gray-900 mt-2">6</p>
</div>
```

### Badges (`.badge-*`)
```html
<span class="badge-green">Active</span>
<span class="badge-red">Overdue</span>
<span class="badge-amber">Pending</span>
<span class="badge-blue">Info</span>
<span class="badge-purple">Premium</span>
<span class="badge-gray">Draft</span>
```

**Audit finding:** Badge/status logic (`priorityBadge()`, `statusBadge()`) is duplicated in 5+ views. Always import from shared utils (`src/utils/formatters.ts` or `src/composables/useStatusBadges.ts`). Never redefine these functions in a view.

**Accessibility:** Badges must not rely on color alone. Always include a text label. Consider adding icons for critical statuses (e.g., `AlertTriangle` for urgent).

### Tables (`.table-wrap`)
```html
<div class="card p-0 overflow-hidden">
  <table class="table-wrap">
    <thead>
      <tr>
        <th scope="col">Name</th>
        <th scope="col">Status</th>
        <th scope="col" class="text-right">Actions</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="item in items" :key="item.id"
          class="cursor-pointer" @click="selectItem(item)">
        <td>
          <div class="font-medium text-gray-900">{{ item.name }}</div>
          <div class="text-xs text-gray-400">{{ item.subtitle }}</div>
        </td>
        <td><span class="badge-green">Active</span></td>
        <td class="text-right">
          <button class="btn-ghost btn-xs" aria-label="Edit item">Edit</button>
        </td>
      </tr>
    </tbody>
  </table>
</div>
```

**MUST include `scope="col"` on all `<th>` elements** (audit finding).

### Filter Pills (`.pill` / `.pill-active`)
```html
<div class="flex gap-2">
  <button :class="['pill', filter === 'all' && 'pill-active']"
          @click="filter = 'all'">All</button>
  <button :class="['pill', filter === 'active' && 'pill-active']"
          @click="filter = 'active'">Active</button>
</div>
```

Use the `FilterPills` component when available.

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
| `ConfirmDialog` | All destructive actions | **Never use `window.confirm()`** — use styled modal |

## Page Layout Pattern

Every page/view MUST follow this structure:

```vue
<template>
  <!-- Page header -->
  <div class="flex items-center justify-between mb-6">
    <div>
      <h1 class="text-xl font-bold text-gray-900">Page Title</h1>
      <p class="text-sm text-gray-500 mt-1">Brief description.</p>
    </div>
    <button class="btn-primary">
      <Plus :size="16" />
      Primary Action
    </button>
  </div>

  <!-- Content -->
  <div class="card p-0">
    <!-- Optional: search/filter bar -->
    <div class="p-4 border-b border-gray-200">
      <SearchInput v-model="search" placeholder="Search..." />
    </div>

    <!-- Data table -->
    <table class="table-wrap">...</table>

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

## Layout Structure

| Element | Spec |
|---------|------|
| **Header bar** | Fixed 56px height, white bg, page title |
| **Sidebar** | Collapsible: 224px expanded, 60px collapsed, white bg |
| **Content area** | `surface` (#F5F5F8) bg, `p-6` padding, scrollable |
| **Sidebar nav** | `sidebar-link` / `sidebar-link-active` / `sidebar-section-label` classes |
| **Nav icons** | Lucide 18px in sidebar, 16px in buttons |

## Accessibility Requirements (from audit — CRITICAL)

### ARIA Labels
Every icon-only button MUST have an `aria-label`:
```html
<button aria-label="Log out"><LogOut :size="18" /></button>
<button aria-label="Close dialog"><X :size="18" /></button>
<button aria-label="Collapse sidebar"><ChevronsLeft :size="18" /></button>
```

### Semantic HTML
- Modals: `role="dialog"`, `aria-modal="true"`, focus trapping
- Tables: `scope="col"` on all `<th>`
- Navigation: wrap in `<nav>` landmark
- Content: wrap in `<main>` landmark
- Toast/loading: `aria-live="polite"` regions
- Collapsibles: `aria-expanded` on toggle buttons
- Progress bars: `role="progressbar"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`
- Form labels: pair with `for`/`id` attributes

### Focus Management
- Define `:focus-visible` styling for all interactive elements
- Never suppress browser focus rings without replacement
- Trap focus within modals/drawers

### Color Independence
- Never use color alone to convey status — always include text labels
- Badges already have text labels (good) — consider adding status icons for critical items

## Error Handling Rules

**CRITICAL (from audit): Never silently swallow errors.**

```typescript
// BAD — found 12+ times in codebase
catch {}
catch { /* ignore */ }

// GOOD — always show error feedback
catch (err) {
  toast.error('Failed to load properties. Please try again.')
}
```

Every API call must have:
1. Loading state (use skeleton loaders, not "Loading..." text)
2. Error state with toast notification
3. Empty state with `EmptyState` component and action CTA

## Form Validation Rules

Every form MUST implement:
1. Required field indicators: `<span class="text-danger-500">*</span>` in labels
2. Field-level validation on blur AND submit
3. `.input-error` class on invalid fields
4. `.input-error-msg` message below invalid fields
5. Scroll to first error on submit
6. Disabled submit button while saving (with `opacity-50 cursor-not-allowed`)

Use `useFormValidation()` composable when available.

## Destructive Action Rules

- **Never use `window.confirm()`** — use styled `ConfirmDialog` component
- Destructive buttons use `btn-danger` styling
- Include clear description of what will be deleted/changed
- Consider undo support for reversible actions

## Unsaved Changes

Forms that accumulate changes MUST:
1. Track dirty state
2. Show `beforeRouteLeave` guard warning
3. Add `beforeunload` event listener
4. Visually indicate unsaved changes (e.g., dot indicator or "Unsaved changes" text)

## Shared Utilities — No Duplication

These functions must be imported from shared locations, never redefined in views:

| Function | Location | Views That Use It |
|----------|----------|-------------------|
| `formatDate()` | `src/utils/formatters.ts` | 6+ views |
| `initials()` | `src/utils/formatters.ts` | 4+ views |
| `priorityBadge()` | `src/composables/useStatusBadges.ts` | 4+ views |
| `statusBadge()` | `src/composables/useStatusBadges.ts` | 5+ views |

## Loading States

Use skeleton loaders (`animate-pulse`) that match the content layout:
```html
<!-- Table skeleton -->
<tr v-for="i in 5" :key="i">
  <td><div class="h-4 bg-gray-200 rounded animate-pulse w-3/4"></div></td>
  <td><div class="h-4 bg-gray-200 rounded animate-pulse w-1/2"></div></td>
</tr>

<!-- Card skeleton -->
<div class="card p-6">
  <div class="h-4 bg-gray-200 rounded animate-pulse w-1/3 mb-4"></div>
  <div class="h-8 bg-gray-200 rounded animate-pulse w-1/4"></div>
</div>
```

**Never use plain "Loading..." text** (audit finding: OwnerDashboard).

## Design Principles

1. **Whitespace**: Generous padding and margins. Never cram elements.
2. **Hierarchy**: Page title > section heading > card heading > body text. Use weight and size.
3. **Consistency**: Always use pre-defined component classes. Never create one-off styles.
4. **Tables for data**: Use `table-wrap` for listing items with multiple attributes. Cards for grouping content or stats.
5. **Actions placement**: Primary action top-right of page header. Secondary/inline actions as ghost buttons in table rows.
6. **Forms**: Labels above inputs, vertical stack with `space-y-4`. Group related fields in cards.
7. **Feedback**: Badges for status, toasts for actions, inline errors for validation. Never silent failures.
8. **Transitions**: 200-300ms for hover/focus. Use `transition-colors` on interactive elements.

## Anti-Patterns Checklist

When reviewing or creating UI, verify NONE of these are present:

- [ ] Hardcoded hex colors or raw Tailwind colors bypassing design tokens
- [ ] Missing `aria-label` on icon-only buttons
- [ ] `window.confirm()` instead of ConfirmDialog
- [ ] Silent `catch {}` blocks without user feedback
- [ ] Duplicated utility functions (formatDate, initials, badge logic)
- [ ] Missing `scope="col"` on table headers
- [ ] "Loading..." text instead of skeleton loaders
- [ ] Forms without field-level validation feedback
- [ ] Inconsistent border radius (cards=`rounded-xl`, inputs/buttons=`rounded-lg`, badges=`rounded-full`)
- [ ] Custom modal/drawer implementations instead of BaseModal/BaseDrawer
- [ ] Empty states without action CTA buttons
- [ ] Color-only status indication without text labels
- [ ] Missing unsaved changes warnings on form views
- [ ] Hardcoded widths that break responsiveness (e.g., `w-[400px]`)

## Key Files

| File | Purpose |
|------|---------|
| `admin/tailwind.config.js` | Color tokens, font config, custom sizes |
| `admin/src/assets/main.css` | All component classes (buttons, inputs, cards, badges, tables, nav) |
| `admin/src/components/AppLayout.vue` | Main layout shell (sidebar + header + content) |
| `admin/src/components/BaseModal.vue` | Standard modal dialog |
| `admin/src/components/BaseDrawer.vue` | Standard side-panel/drawer |
| `admin/src/components/EmptyState.vue` | Empty state placeholder with CTA |
| `admin/src/components/SearchInput.vue` | Reusable search input with icon |
| `admin/src/components/FilterPills.vue` | Filter toggle pills |
| `admin/src/components/ToastContainer.vue` | Toast notification system |
| `admin/system_documentation/claude_opus_ux_ui_audit_2026-03-25.md` | **Full UX/UI audit — read for view-specific findings** |

## New View Checklist

When creating a new page/view, verify all of:

- [ ] Page header with title, optional subtitle, and primary action button (top-right)
- [ ] Content wrapped in `card` components
- [ ] Data displayed in `table-wrap` tables with `scope="col"` headers
- [ ] Search/filter bar above table when applicable (use `SearchInput` / `FilterPills`)
- [ ] Empty state with `EmptyState` component and action CTA when no data
- [ ] Loading state with skeleton loaders (never "Loading..." text)
- [ ] Error handling with `toast.error()` on every API failure
- [ ] Status shown with `badge-*` classes (with text labels, not color-only)
- [ ] Forms use `label` + `input` pattern with `space-y-4` and field-level validation
- [ ] Buttons use `btn-*` classes (primary for main action, ghost for secondary)
- [ ] All icon-only buttons have `aria-label`
- [ ] Destructive actions use `ConfirmDialog` (never `window.confirm()`)
- [ ] Icons from Lucide at correct sizes (16px in buttons, 18px in nav)
- [ ] No hardcoded colors — all from design tokens
- [ ] Shared utilities imported, not redefined
- [ ] Responsive: content scrolls, no hardcoded widths that break on mobile
- [ ] Unsaved changes warning if form view
