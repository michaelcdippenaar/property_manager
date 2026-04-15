# Anti-Patterns Checklist

## HARD RULE — No hardcoded tokens

Colors, font-sizes, shadows, spacing, and radii **must** come from the design tokens. Arbitrary values (`text-[11px]`, `bg-[#2B2D6E]`, `shadow-[0_4px_12px_rgba(0,0,0,0.08)]`) or raw Tailwind palette names that bypass the brand tokens (`bg-indigo-900`, `text-red-600`) are banned. Arbitrary values are only acceptable when no token fits **and** a comment justifies it.

### Colors — bad → good

| Bad | Good | Why |
|-----|------|-----|
| `style="color: #2B2D6E"` | `class="text-navy"` | Hex literal — use token |
| `bg-[#2B2D6E]` | `bg-navy` | Arbitrary value — use token |
| `bg-[#e8eaed]` | `bg-surface` or `bg-gray-100` | Arbitrary value — use token |
| `bg-indigo-900` | `bg-navy` | Raw palette bypasses brand token |
| `text-red-600` | `text-danger-600` | Raw palette bypasses semantic scale |
| `bg-emerald-50` | `bg-success-50` | Raw palette bypasses semantic scale |
| `border-[#FF3D7F]` | `border-accent` | Arbitrary value — use token |
| `bg-pink-brand/10` | `bg-accent/10` | Non-standard alias — use token |

### Font-sizes — bad → good

| Bad | Good | Why |
|-----|------|-----|
| `text-[10px]` | `text-xs` (or `text-micro` if decorative) | Arbitrary value below readable floor |
| `text-[11px]` | `text-micro` | Use the component class |
| `text-[11px] font-medium text-gray-500` | `.text-micro` | Use the component class |
| `text-[13px]` | `text-sm` | Arbitrary value — use utility |
| `text-[15px]` | `text-base` | Base is already 15px globally |
| Hand-rolled `text-xl font-bold text-gray-900 tracking-tight` H1 | `<PageHeader>` (or `.page-title`) | Use the component class |
| Ad-hoc `text-2xl font-bold` stat | `.stat-value` | Use the component class |
| `text-xs font-semibold uppercase tracking-wider` label | `.label-upper` | Use the component class |

### Buttons — always use `.btn-*` component classes

Always use the `.btn-primary` / `.btn-ghost` / `.btn-danger` / `.btn-success` / `.btn-accent` classes (optionally with `.btn-sm` / `.btn-xs`). **Never hand-roll button styles with raw Tailwind utilities** — doing so silently drops the accent-pink hover ring, keyboard focus-visible ring, `active:scale` press feedback, standard 150ms transitions, mobile 44px touch target, and `disabled:` states.

| Bad | Good | Why |
|-----|------|-----|
| `<button class="bg-navy text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-navy-dark">Save</button>` | `<button class="btn-primary">Save</button>` | Raw utilities miss hover ring, active-scale, focus styles, touch target |
| `<button class="bg-white border border-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50">Cancel</button>` | `<button class="btn-ghost">Cancel</button>` | Same reasons — use the component class |
| `<button class="bg-accent text-white px-3 py-1.5 rounded-lg text-xs">New</button>` | `<button class="btn-accent btn-sm">New</button>` | Use `.btn-sm` for small variants, not ad-hoc padding/text-size |

If you need a one-off tweak, compose on top of the class (e.g. `class="btn-ghost text-navy border-navy hover:bg-navy/5"`) — never replace it.

### Shadows / spacing / radii — bad → good

| Bad | Good | Why |
|-----|------|-----|
| `shadow-[0_4px_12px_rgba(0,0,0,0.08)]` | `shadow-soft` / `shadow-lifted` / `shadow-floating` | Use shadow tokens |
| `p-[13px]` | `p-3` or `p-4` | Non-standard spacing |
| `rounded-[9px]` | `rounded-lg` (cards → `rounded-xl`, badges → `rounded-full`) | Non-standard radius |
| `gap-[7px]` | `gap-2` | Non-standard spacing |
| `<div class="card p-4">` top-level page card | `<div class="card p-5">` | `p-5` is the default; `p-4` is only for dense list-row / compact cards |
| `<div class="card p-6">` ordinary section card | `<div class="card p-5">` | `p-6` is reserved for hero / empty-state / modal-body cards |
| Root view `<div class="space-y-3">` / `space-y-4` | `<div class="space-y-5">` | Top-level page sections use `space-y-5`; smaller values are for inside-card stacks |

---

When reviewing or creating UI, verify NONE of these are present:

- [ ] **Phosphor icons** (`@phosphor-icons/vue`) — banned, removed April 2026. Lucide only.
- [ ] Hand-rolled `<h1 class="text-xl...">` + Breadcrumb at top of a view — use **`PageHeader`** instead
- [ ] Arbitrary font-size values like `text-[10px]` / `text-[11px]` / `text-[13px]` — use Tailwind utilities or the component classes (`.text-micro`, `.text-muted`, `.page-title`, `.stat-value`, `.label-upper`). Floor for readable text is `text-xs` (12px); `text-micro` (11px) is decorative only.
- [ ] Hover-only dropdowns — must also open via click, have `aria-haspopup` / `aria-expanded`, and close on Escape + outside-click
- [ ] Extra `max-w-*` / `container` wrapper inside a view — `AppLayout` already clamps to `max-w-[1400px]`
- [ ] Internal tabs driven by local state only — must use `?tab=<key>` + `VALID_SECTIONS` whitelist + `normaliseTab()` alias map
- [ ] Single "no data" empty state on a filtered list — split into "no matches" (Clear filters) vs "no items" (Add CTA)
- [ ] Section-card using a non-standard header row — must be `px-5 py-3 border-b border-gray-100 flex items-center gap-2` with a 14px `text-navy` Lucide icon and `text-xs font-semibold uppercase tracking-wide text-navy` label
- [ ] Overriding the global Lucide stroke-width (1.75) without a documented reason
- [ ] Hardcoded hex colors (`#2B2D6E`), arbitrary color values (`bg-[#2B2D6E]`), or raw Tailwind palette names that bypass brand tokens (`bg-indigo-900` → `bg-navy`, `text-red-600` → `text-danger-600`, `bg-emerald-50` → `bg-success-50`)
- [ ] Arbitrary shadow / spacing / radius values (`shadow-[0_4px_12px_...]`, `p-[13px]`, `rounded-[9px]`) — use `shadow-soft`/`shadow-lifted`/`shadow-floating` and standard Tailwind spacing/radii
- [ ] Missing `aria-label` on icon-only buttons
- [ ] `window.confirm()` instead of ConfirmDialog
- [ ] Silent `catch {}` blocks without user feedback
- [ ] Duplicated utility functions (`formatDate`, `initials`, badge logic)
- [ ] Missing `scope="col"` on table headers
- [ ] "Loading..." text instead of skeleton loaders
- [ ] Forms without field-level validation feedback
- [ ] Inconsistent border radius (cards=`rounded-xl`, inputs/buttons=`rounded-lg`, badges=`rounded-full`)
- [ ] Custom modal/drawer implementations instead of `BaseModal`/`BaseDrawer`
- [ ] Empty states without action CTA buttons
- [ ] Color-only status indication without text labels
- [ ] Missing unsaved changes warnings on form views
- [ ] Hardcoded widths that break responsiveness (`w-[400px]` → use `w-full sm:w-[400px]`)
- [ ] Tables without `<div class="table-scroll">` wrapper
- [ ] Page headers using `flex items-center justify-between` without `flex-col sm:flex-row` stacking
- [ ] Hardcoded `grid-cols-N` without mobile-first breakpoints
- [ ] Hover-only interactions without click/tap alternative
- [ ] Tab/filter bars without `overflow-x-auto`
