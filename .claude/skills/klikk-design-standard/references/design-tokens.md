# Design Tokens & Component Classes

---

## Color Tokens (`tailwind.config.js`)

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

**CRITICAL: Never use hardcoded hex values or raw Tailwind colors (`bg-emerald-50`, `bg-pink-brand/10`, `bg-[#e8eaed]`). Always use the defined tokens.**

Known violations to fix:
- DashboardView stat icons use mixed `bg-navy/10`, `bg-pink-brand/10`, `bg-amber-50`, `bg-emerald-50`
- LeaseBuilderView preview uses `bg-[#e8eaed]` → use `bg-surface` or `bg-gray-100`
- TemplateEditorView uses raw hex throughout → must use tokens
- CalendarView event colors: 7 hardcoded color pairs → centralize
- ESigningPanel status colors: hardcoded per-status objects → use tokens

---

## Typography

**Base font size is 15px** (not Tailwind's default 16px) — set globally on `html`/`body` in `main.css`. Every Tailwind size class therefore scales down slightly (e.g. `text-sm` ≈ 13.1px, `text-xs` = 12px).

**Floor for user-readable text is `text-xs` (12px) or the `text-micro` component class (11px / weight 500).** Do not use arbitrary `text-[10px]` or `text-[11px]` for anything a user actually needs to read — those are reserved for decorative micro-labels (the role-pill chip, nav badge counters).

| Element | Classes | Notes |
|---------|---------|-------|
| Page title | `text-xl font-bold text-gray-900 tracking-tight` | Rendered via `PageHeader` — don't hand-roll |
| Page subtitle | `text-sm text-gray-500 mt-1` | Below page title |
| Section heading | `text-base font-semibold text-gray-900` | Within cards/sections |
| Card heading | `text-sm font-semibold text-gray-700` | Card titles |
| Body text | `text-sm text-gray-700` | Default content text |
| Muted text | `text-xs text-gray-400` | Timestamps, hints, secondary info |
| Table header | `text-xs font-semibold text-gray-500 uppercase tracking-wider` | Column headers |
| Sidebar section | `sidebar-section-label` class | Section headers in nav |
| Micro label | `text-micro` (11px, weight 500) | Tiny labels, stat card labels |
| Form label | `label` class (`text-sm font-medium text-gray-700 mb-1`) | Above inputs |

**Audit finding:** Typography is inconsistent across views. Use these exact patterns — never mix `text-micro`, `text-xs`, `text-sm` arbitrarily.

---

## Spacing

| Context | Value | Notes |
|---------|-------|-------|
| Page padding | `p-4 sm:p-6` | Content area (tighter on mobile) |
| Card padding | `p-5` (default) | Internal card content |
| Between sections | `space-y-5` | Vertical section gaps (top-level) |
| Between form fields | `space-y-4` | Within forms |
| Between inline items | `gap-2` to `gap-4` | Flex/grid children |
| Table cell padding | `px-4 py-3` | Consistent table cells |

**Audit finding:** Spacing values vary arbitrarily. Standardize within each context.

---

## Spacing scale (standardised)

Ratified as the Klikk admin defaults — **do not re-debate case-by-case**.

### Card padding

| Token | Use for | Rationale |
|-------|---------|-----------|
| **`card p-5`** (default) | Top-level page cards, section cards, form cards, stat cards | Balanced; most common in the codebase |
| `card p-4` | Dense list-row cards, compact badge/pill cards, nested cards inside larger cards | Reserved for tight-density contexts where `p-5` feels airy |
| `card p-6` | Hero cards, full-page empty states, modal/drawer body cards | Reserved for marquee/hero content |

Any `p-4` or `p-6` card that is **not** in one of the exception buckets above should be `p-5`. Document justified exceptions with an inline comment.

### Section-card header pattern

Inside a section card, the header row is **always**:

```html
<div class="px-5 py-3 border-b border-gray-100 flex items-center gap-2">
  <Icon :size="14" class="text-navy" />
  <span class="text-xs font-semibold uppercase tracking-wide text-navy">Heading</span>
</div>
<div class="p-5">
  <!-- body -->
</div>
```

Matches the card-body `p-5` default so the header-to-body rhythm is consistent.

### Vertical section spacing

| Token | Use for |
|-------|---------|
| **`space-y-5`** (default) | Top-level page content — the outermost `<div class="space-y-*">` that separates major page sections |
| `space-y-4` | Groups inside a card (e.g. a stack of form fields, a list of rows inside a card body) |
| `space-y-3` | Dense inline stacks (e.g. label+value rows, small metadata lists) |
| `space-y-6` | Only when a view has very tall hero sections that need extra breathing room — justify inline |

**Rule:** the root `<div>` of any view template uses `space-y-5`. Nested spacing is chosen by density, not personal preference.

---

## Borders & Shadows

| Element | Classes |
|---------|---------|
| Card | `rounded-xl border border-gray-200 shadow-sm` |
| Input | `rounded-lg border border-gray-300` |
| Button | `rounded-lg` |
| Badge | `rounded-full` |
| Modal | `rounded-xl shadow-xl` |

---

## Component Classes (`admin/src/assets/main.css`)

### Buttons (`.btn-*`)

```html
<button class="btn-primary">Save</button>           <!-- Navy bg, white text -->
<button class="btn-ghost">Cancel</button>            <!-- White bg, gray border -->
<button class="btn-danger">Delete</button>           <!-- Danger-50 bg, danger text -->
<button class="btn-success">Approve</button>         <!-- Success-600 bg, white text -->
<button class="btn-accent">Sign Up</button>          <!-- Accent bg, white text -->
<button class="btn-primary btn-sm">Small</button>
<button class="btn-ghost btn-xs">XS</button>

<!-- Outlined action button -->
<button class="btn-ghost text-navy border-navy hover:bg-navy/5">Export</button>
```

**All buttons MUST include `disabled:opacity-50 disabled:cursor-not-allowed`** (already in `.btn` base class).

#### Accent-pink hover ring

`.btn-primary`, `.btn-ghost`, `.btn-success`, and `.btn-accent` render a **2px accent-pink ring** (`rgba(255, 61, 127, 0.35)`) on hover via `box-shadow`. This is layout-shift free (no border/size change) and is defined once in `main.css`:

```css
.btn-primary:hover:not(:disabled),
.btn-ghost:hover:not(:disabled),
.btn-success:hover:not(:disabled),
.btn-accent:hover:not(:disabled) {
  box-shadow: 0 0 0 2px rgba(255, 61, 127, 0.35);
}
```

- Applies automatically — never hand-roll a ring on a button.
- **`.btn-danger` is deliberately excluded** (pink-on-red clashes; the danger variant keeps its own red hover treatment).
- Selectors are listed explicitly because Tailwind `@apply` hoists `.btn` into each variant, so a bare `.btn:hover` rule only lands on `.btn-primary`.
- Disabled buttons do not ring (`:not(:disabled)`).

### Inputs (`.input`)

```html
<div>
  <label class="label">Field Label <span class="text-danger-500">*</span></label>
  <input class="input" type="text" placeholder="Enter value..." />
</div>

<!-- Validation error -->
<div>
  <label class="label">Email</label>
  <input class="input input-error" type="email" />
  <p class="input-error-msg">Please enter a valid email.</p>
</div>

<!-- Help text -->
<div>
  <label class="label">Username</label>
  <input class="input" type="text" />
  <p class="input-help">This will be your display name.</p>
</div>
```

**CRITICAL:** `.input-error` and `.input-error-msg` classes exist but were not being used. Every form MUST use field-level validation with these classes.

### Cards (`.card`)

```html
<div class="card p-6">
  <h2 class="text-base font-semibold text-gray-900 mb-4">Section Title</h2>
</div>

<!-- Stat card -->
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

**Audit finding:** Badge logic (`priorityBadge()`, `statusBadge()`) is duplicated in 5+ views. Always import from `src/composables/useStatusBadges.ts`.

**Accessibility:** Never use color alone. Always include text label.

### Tables (`.table-wrap` + `.table-scroll`)

```html
<div class="card p-0 overflow-hidden">
  <div class="table-scroll">
    <table class="table-wrap">
      <thead>
        <tr>
          <th scope="col">Name</th>
          <th scope="col" class="text-right">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.id" class="cursor-pointer" @click="selectItem(item)">
          <td>
            <div class="font-medium text-gray-900">{{ item.name }}</div>
            <div class="text-xs text-gray-400">{{ item.subtitle }}</div>
          </td>
          <td class="text-right">
            <button class="btn-ghost btn-xs" aria-label="Edit item">Edit</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
```

- **MUST wrap every `<table>` with `<div class="table-scroll">`** for mobile scrolling
- **MUST include `scope="col"` on all `<th>` elements**
- Place `v-if`/`v-else` on the `<div class="table-scroll">` wrapper, NOT on `<table>`

### Filter Pills (`.pill` / `.pill-active`)

```html
<div class="flex gap-2">
  <button :class="['pill', filter === 'all' && 'pill-active']" @click="filter = 'all'">All</button>
  <button :class="['pill', filter === 'active' && 'pill-active']" @click="filter = 'active'">Active</button>
</div>
```

Use the `FilterPills` component when available.
