# Vue Admin App (klikk-admin) — UI/UX Deep Audit

**Auditor:** Claude Opus 4.6
**Date:** 2026-03-25
**Scope:** Visual consistency, interaction design, user flows, accessibility, and design system gaps across all admin views.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Design System Assessment](#2-design-system-assessment)
3. [Layout & Navigation Audit](#3-layout--navigation-audit)
4. [View-by-View UX Audit](#4-view-by-view-ux-audit)
5. [Cross-Screen Consistency Analysis](#5-cross-screen-consistency-analysis)
6. [Accessibility Audit](#6-accessibility-audit)
7. [Responsive Design Audit](#7-responsive-design-audit)
8. [Interaction Design Issues](#8-interaction-design-issues)
9. [UX Anti-Patterns & Friction Points](#9-ux-anti-patterns--friction-points)
10. [Recommendations Priority Matrix](#10-recommendations-priority-matrix)

---

## 1. Executive Summary

The Klikk Admin app has a solid visual foundation — a navy/accent palette, a collapsible sidebar, consistent card-based layouts, and recently extracted shared components (BaseModal, BaseDrawer, EmptyState, FilterPills, SearchInput, ToastContainer). The design system (`main.css`) defines `.btn-*`, `.input`, `.card`, `.badge-*`, `.pill`, `.table-wrap`, and `.sidebar-link` classes, giving it a stronger baseline than most early-stage admin apps.

However, a detailed screen-by-screen audit reveals **systematic gaps in UX execution** that undermine the design system's intent. The issues cluster into five themes:

### Severity Breakdown

| Severity | Count | Theme |
|----------|-------|-------|
| **Critical** | 4 | No form validation feedback, missing ARIA labels on all icon buttons, TemplateEditorView is unusable below 1200px, color-only status indication throughout |
| **High** | 11 | Silent error swallowing (12+ catch blocks), badge/status logic duplicated across 5+ views, inconsistent modal vs Teleport patterns, SuppliersView duplicated with DirectoryView, no keyboard focus indicators, TemplateEditorView uses deprecated `execCommand`, disabled buttons lack visual feedback, no unsaved changes warnings, `window.confirm()` used for destructive actions, no undo for deletes, dispatch flow confusing terminology |
| **Medium** | 14 | Typography scale inconsistent (text-micro vs text-xs vs text-sm), spacing values vary (gap-2/3/4, p-4/5/6), hardcoded colors bypass design tokens, skeleton loaders don't match content, search implementations inconsistent, filter state not persisted in URL, no table sorting, OwnerDashboard too sparse, detail panels inconsistent, no date-range filtering, no relative timestamps, no onboarding for TemplateEditor autocomplete, AI chat can silently update documents, modals can overlap in TemplateEditor |
| **Low** | 8 | No breadcrumbs on deep routes, no page title updates per route, email addresses not clickable, empty state CTAs inconsistent, stat cards not clickable, occupancy bars too thin, field palette too cramped at 270px, color picker swatches don't match design tokens |

---

## 2. Design System Assessment

### 2.1 What Exists (Good Foundation)

**`main.css` (87 lines) — Custom Component Layer:**

| Token | Variants | Status |
|-------|----------|--------|
| `.btn` | primary, ghost, danger, success, accent + sizes (sm, xs) | Good — covers most needs |
| `.input` | default, error, success + `.input-help`, `.input-error-msg` | Good — validation states defined |
| `.label` | single style | Minimal |
| `.card` | single style | Good |
| `.badge` | green, red, amber, blue, purple, gray | Good |
| `.pill` | default + active | Good |
| `.table-wrap` | striped rows, hover | Good |
| `.sidebar-link` | default + active | Good |

**`tailwind.config.js` — Extended Palette:**

| Token | Values | Notes |
|-------|--------|-------|
| Navy | DEFAULT, dark, light | Primary brand — well-used |
| Accent | DEFAULT (#FF3D7F), light, dark | Underused — mostly logo dot only |
| Surface | DEFAULT (#F5F5F8), secondary (#F0EFF8) | Background tokens |
| Success | 50/100/500/600/700 | Semantic — well-defined |
| Warning | 50/100/500/600/700 | Semantic — well-defined |
| Danger | 50/100/500/600/700 | Semantic — well-defined |
| Info | 50/100/500/600/700 | Semantic — well-defined |
| Font `micro` | 11px, line-height 16px, weight 500 | Custom small size |

**Composable: `useToast.ts`** — Global toast system with success/error/info/warning variants. Well-designed.

### 2.2 What's Missing

| Gap | Impact | Notes |
|-----|--------|-------|
| **No typography tokens** | Views define their own heading/label/body styles | Need `.heading-1`, `.heading-2`, `.section-label`, `.body-sm` |
| **No spacing tokens** | gap/padding values vary arbitrarily | Need defined scale (tight/default/loose) |
| **Badge logic not centralized** | `priorityBadge()` / `statusBadge()` duplicated in 5+ views | Need `utils/badges.ts` |
| **`formatDate()` duplicated** | Identical function in 6+ views | Need `utils/formatters.ts` |
| **`initials()` duplicated** | Same function in 4 files | Same fix |
| **No loading component** | Each view builds its own skeleton | Need `SkeletonLoader.vue` with variants |
| **No confirmation modal** | Uses native `window.confirm()` | Need `ConfirmDialog.vue` |
| **No form validation pattern** | `.input-error` class exists but no view uses it | Need validation composable |

### 2.3 Design Token Bypass — Hardcoded Colors

Despite a well-defined palette, many views bypass design tokens with raw Tailwind/hex values:

| Location | Hardcoded | Should Be |
|----------|-----------|-----------|
| DashboardView stat icons | `bg-navy/10`, `bg-pink-brand/10`, `bg-amber-50`, `bg-emerald-50` | Consistent `bg-{semantic}-50` |
| LeaseBuilderView preview | `bg-[#e8eaed]` | `bg-surface` or `bg-gray-100` |
| TemplateEditorView (throughout) | `#2B2D6E`, `#FF3D7F`, `#111111`, `#d1d5db`, `#f3f4f6`, `#e8eaed` | Design tokens |
| TemplateEditorView drag ghost | `background:#0d9488` (teal) | `bg-navy` or accent |
| TemplateEditorView merge fields | `background:#0d9488;color:#fff` | Design token |
| LeaseBuilderView left panel | `w-[400px]` hardcoded width | Responsive token |
| LeaseBuilderView preview page | `w-[680px]` hardcoded | Responsive token |
| CalendarView event colors | 7 hardcoded color pairs | Centralized event color map |
| ESigningPanel status colors | Hardcoded per-status objects | Design tokens |

---

## 3. Layout & Navigation Audit

### 3.1 Sidebar (AppLayout.vue — 231 lines)

**Strengths:**
- Collapsible between 60px (icons-only with tooltips) and 224px
- Grouped navigation sections (Main, Leases, Maintenance, Life Cycle, Setup)
- Active link detection with `.sidebar-link-active`
- User info + logout at bottom
- Smooth collapse transition

**Issues:**

| Issue | Severity | Detail |
|-------|----------|--------|
| No mobile hamburger | Medium | Sidebar assumes desktop viewport — no overlay mode for mobile |
| Collapse state not persisted | Low | Resets on page reload; should save to localStorage |
| Section grouping is static | Low | No collapsible section groups — all items visible at once |
| No notification badges | Low | Nav items don't show counts (e.g., "Issues (3)") |

### 3.2 Supplier & Owner Layouts

**SupplierLayout.vue (70 lines)** and **OwnerLayout.vue (70 lines)** use a top-nav pattern (horizontal nav items in navy header). These are clean and appropriate for their simpler feature sets but:

| Issue | Severity |
|-------|----------|
| Duplicated layout structure (header, logo, nav, initials, logout) — should extract `BaseLayout.vue` | Medium |
| No active link underline animation | Low |
| User initials avatar is hardcoded navy — no hash-based color variation | Low |

### 3.3 Page Title & Breadcrumbs

- Page title auto-updates from route meta in top bar — good
- **No breadcrumbs** on deep routes (e.g., `/leases/templates/5/edit`) — user has no trail
- **No page-level `<title>` updates** — browser tab always shows "Klikk Admin"

---

## 4. View-by-View UX Audit

### 4.1 LoginView.vue (94 lines)

**Rating: 7/10 — Functional but basic**

| Aspect | Finding | Severity |
|--------|---------|----------|
| Layout | Clean centered card on lavender background, max-w-sm | Good |
| Form fields | Email + password with visibility toggle | Good |
| Validation | None — only HTML5 `required` attribute, no inline error feedback | High |
| Error display | Inline error card appears — but no transition/animation, appears abruptly | Medium |
| Autocomplete | Missing `autocomplete="email"` and `autocomplete="current-password"` | Medium |
| Disabled state | `opacity-50` too subtle — button looks the same | Medium |
| Password toggle | No `aria-label` ("Show password" / "Hide password") | High |
| Color tokens | Logo hardcodes `#2B2D6E` and `#FF3D7F` — should use `text-navy`, `text-accent` | Low |
| Empty | No "forgot password" link | Low |

### 4.2 DashboardView.vue (130 lines)

**Rating: 7.5/10 — Good overview, missing interactivity**

| Aspect | Finding | Severity |
|--------|---------|----------|
| Stat cards | 4-card grid with icons, labels, values — clean | Good |
| Stat icon colors | Mix of `navy/10`, `pink-brand/10`, `amber-50`, `emerald-50` — inconsistent saturation | Medium |
| Stat values | Different `valueColor` per stat (navy vs gray-900) — inconsistent visual weight | Low |
| Loading | Skeleton loaders match layout — good | Good |
| Error state | **None** — API failures silently set `loading = false`, user sees empty data | High |
| Table | Recent maintenance with priority/status badges — clean | Good |
| Table interactivity | No row click, no sort, no "view all" link | Medium |
| Occupancy bars | `h-2` is too thin — hard to see changes, no hover tooltip | Low |
| Progress bar a11y | Missing `aria-valuenow`, `aria-valuemin`, `aria-valuemax` | High |
| Stat cards | Not clickable — should link to respective list views | Low |

### 4.3 PropertiesView.vue (166 lines)

**Rating: 7/10 — Solid CRUD, weak validation**

| Aspect | Finding | Severity |
|--------|---------|----------|
| Layout | Header + search + table + empty state — clear hierarchy | Good |
| Add Property modal | BaseModal with 7-field form, 2-column grid | Good |
| Form validation | **Only checks `name` is truthy** — no field-level errors despite `.input-error` existing in CSS | High |
| Required indicators | Uses `<span class="text-danger-500">*</span>` — correct pattern | Good |
| Search | Real-time filtering on name/city — works for small datasets | Good |
| Occupancy bar | In table row, `min-w-[120px]` — no label explaining "% of what" | Low |
| Empty state | EmptyState with icon + CTA button — good | Good |
| Toast feedback | Success/error on create — good | Good |

### 4.4 TenantsView.vue (95 lines)

**Rating: 6/10 — Read-only, no actions**

| Aspect | Finding | Severity |
|--------|---------|----------|
| Layout | Search + table — standard | Good |
| Interactivity | **No actions at all** — no edit, add, deactivate, or click-to-detail | High |
| Email | Not a clickable `mailto:` link — missed affordance | Low |
| Empty state | Message says "Tenants will appear here once added to a property" — no action button (unlike PropertiesView) | Medium |
| Avatar | All tenants use `bg-navy` — no hash-based color variation for visual distinction | Low |
| PII | ID numbers displayed in full — POPIA concern (should mask by default) | Medium |
| Status badge | Color-only indication (green=active, red=inactive) — needs text or icon | Medium |

### 4.5 LeasesView.vue (613 lines)

**Rating: 7.5/10 — Smart grouping, complex but functional**

| Aspect | Finding | Severity |
|--------|---------|----------|
| Property grouping | Collapsible groups with chevron rotation — intuitive | Good |
| Expanded detail | 2-column layout (details + actions) when row expanded | Good |
| Status/priority badges | Uses computed `statusBadge()` / `priorityBadge()` — but duplicated from DashboardView | Medium |
| Document badges | Absolute positioned count badges on icon — fragile for different icon sizes | Low |
| Timeline dates | `tabular-nums` for alignment — good attention to detail | Good |
| Actions | Edit (drawer), delete, renew, import — comprehensive | Good |
| Delete | Uses `confirm()` — should use styled ConfirmDialog | Medium |
| Loading | Skeleton rows — good | Good |
| Empty | EmptyState with "Add Lease" and "Import Lease" CTAs | Good |
| Responsive | Expanded detail grid uses `grid-cols-4` — no mobile layout | Medium |

### 4.6 LeaseCalendarView.vue (239 lines)

**Rating: 7/10 — Clean calendar, limited event density**

| Aspect | Finding | Severity |
|--------|---------|----------|
| Calendar grid | 7-column with proper month boundaries | Good |
| Filter pills | Color-coded type toggles — clear | Good |
| Event display | Max 3 per day + "+X more" — acceptable | Good |
| Event colors | 7 hardcoded color pairs — should be centralized | Medium |
| Color tokens | `eventColor()` duplicates filter color definitions — DRY violation | Medium |
| Day detail | Side panel on day click — good | Good |
| "Mark complete" | Text link instead of button — should be `<button>` for a11y | Medium |
| Cell height | `min-h-[100px]` hardcoded — not responsive | Low |
| Today badge | `w-6 h-6` hardcoded — brittle | Low |

### 4.7 LeaseTemplatesView.vue (227 lines)

**Rating: 7/10 — Clean grid, good multi-step modal**

| Aspect | Finding | Severity |
|--------|---------|----------|
| Template cards | Grid with status, version, field count — scannable | Good |
| Multi-step modal | "Choose source" → "Details" progression — clear | Good |
| Card hover | `border-navy/40 shadow-sm` — subtle but appropriate | Good |
| Template name | `truncate` class but no `title` attribute — can't see full name | Low |
| Version + province | Same line in `text-micro` — hard to scan, should stack vertically | Low |
| File upload | Dashed border dropzone — consistent with ImportLeaseWizard | Good |
| Skeleton | `h-28` doesn't match actual card height | Low |

### 4.8 LeaseBuilderView.vue (689 lines)

**Rating: 6.5/10 — Powerful but not responsive**

| Aspect | Finding | Severity |
|--------|---------|----------|
| Split panel | Form left + live preview right — powerful pattern | Good |
| Merge field highlighting | Color-coded filled vs. empty fields in preview | Good |
| Inline sub-components | SectionLabel, PersonBlock — reduce duplication | Good |
| Left panel width | `w-[400px]` hardcoded — **not responsive below 1024px** | High |
| Preview width | `w-[680px]` hardcoded — breaks on smaller screens | High |
| Preview background | `bg-[#e8eaed]` hardcoded — should be `bg-surface` | Low |
| Form validation | **No validation for required fields** — error only at top of form | High |
| Section labels | Uppercase with wide letter-spacing — inconsistent weight across files | Medium |
| Mobile | **No layout switching** — should stack vertically on mobile | High |

### 4.9 EditLeaseDrawer.vue (715 lines)

**Rating: 7/10 — Comprehensive but overwhelming**

| Aspect | Finding | Severity |
|--------|---------|----------|
| Full-viewport Teleport | Good focus management — sidebar hidden | Good |
| Sections | Property, details, terms, tenants, occupants, guarantors, docs, e-signing | Good |
| Dynamic lists | Add/remove tenants, occupants, guarantors with inline forms | Good |
| Tenant cards | Navy/10 background with numbered badges — clear | Good |
| Unsaved changes | **No indicator** — user may close drawer and lose work | High |
| Form validation | **No validation feedback** despite `.input-error` CSS existing | High |
| Document upload | File input styling inconsistent with LeasesView upload | Medium |
| E-signing section | Embedded panel takes space — should be collapsible or tabbed | Medium |
| Primary tenant | No way to change after creation — missing affordance | Medium |
| Spacing | `gap-4` vs `gap-3` inconsistent between sections | Low |

### 4.10 ImportLeaseWizard.vue (684 lines)

**Rating: 7.5/10 — Smart AI features, good UX flow**

| Aspect | Finding | Severity |
|--------|---------|----------|
| Multi-step | Upload → Review → Done — clear progression | Good |
| Draft persistence | localStorage auto-save with resume prompt — excellent | Good |
| PDF preview | Inline on desktop (52% split) — aids verification | Good |
| Step indicator | Visible in header — good | Good |
| Mobile PDF | **Hidden on mobile** — user can't verify data against original | High |
| Draft banner | `bg-amber-50` with clear actions — good affordance | Good |
| Loading animation | Sparkles animation during AI parsing — nice polish | Good |
| Lavender background | Uses `bg-lavender` — undefined in design tokens | Medium |
| Dropzone | Click handler for file input — but no drag feedback animation | Low |
| Age display | "d ago" format is informal — inconsistent with other date formatting | Low |

### 4.11 ESigningPanel.vue (418 lines)

**Rating: 6.5/10 — Functional, cluttered detail**

| Aspect | Finding | Severity |
|--------|---------|----------|
| Submission list | Status icons + colors per signer — clear at a glance | Good |
| Auto-population | Tenant names pre-fill signer fields — good | Good |
| Missing email | Amber border indicator — visible affordance | Good |
| Status badges | Hardcoded color objects — should use design tokens | Medium |
| Error position | Top of modal — may be missed if user scrolls | Medium |
| Resend button | Only visible conditionally — affordance unclear | Medium |
| Checkboxes | Per-signer options (send email, save to record) — small hit targets | Low |
| Spacing | `space-y-3` tighter than typical list items | Low |

### 4.12 MaintenanceView.vue (97 lines) & RequestsView.vue (402 lines)

**Rating: 7.5/10 — Strong master-detail, complex dispatch**

| Aspect | Finding | Severity |
|--------|---------|----------|
| Master-detail | Left list + right sticky detail panel — effective pattern | Good |
| Priority color coding | Left border `border-l-4` — clear visual signal | Good |
| Filter pills | FilterPills component — consistent | Good |
| Dispatch flow | Click "Get Quotes" → modal → select suppliers → send → award | Acceptable |
| Dispatch terminology | "Get Quotes" vs modal title "Dispatch to Suppliers" — confusing | Medium |
| Status change | Silently updates with no toast confirmation | Medium |
| Badge logic | `priorityBadge()` / `statusBadge()` — **duplicated from Dashboard** | High |
| Detail panel loading | No loading skeleton when selecting new request | Medium |
| Supplier loading error | `catch { /* ignore */ }` — silent failure breaks dispatch | High |

### 4.13 SuppliersView.vue (778 lines) & DirectoryView.vue (796 lines)

**Rating: 6/10 — Major duplication problem**

| Aspect | Finding | Severity |
|--------|---------|----------|
| **Duplicate views** | **Two near-identical supplier management UIs** — SuppliersView under /maintenance, DirectoryView under /suppliers | **Critical** |
| Modal patterns | SuppliersView uses BaseModal; DirectoryView uses custom Teleport modals | High |
| Form validation | **None** — no field-level errors, disabled button logic is only `!form.name \|\| !form.phone` | High |
| Delete | Uses `window.confirm()` — should be styled modal | Medium |
| File upload | No drag-and-drop, no preview, no progress indicator | Medium |
| Detail drawer | SuppliersView uses BaseDrawer; DirectoryView uses Teleport — inconsistent | Medium |
| Property groups | Hidden in supplier detail — should be first-class feature | Low |
| Import result | Banner with close button but no retry CTA if import fails | Low |

### 4.14 SkillLibraryView.vue (119 lines)

**Rating: 6/10 — Bare, feature hidden**

| Aspect | Finding | Severity |
|--------|---------|----------|
| Skills list | Simple list with `space-y-1` — cramped | Medium |
| AI chat | Single-turn only — no conversation history | Medium |
| Discoverability | Not linked from MaintenanceView — user might not find it | Medium |
| Error handling | Good error messages with specific context | Good |
| Client truncation | `skills.slice(0, 200)` — should paginate server-side | Low |
| Code tags | Inline `<code>` styling — should use design token | Low |

### 4.15 Supplier Portal: JobsListView.vue (246 lines) & CalendarView.vue (117 lines) & SupplierProfileView.vue (204 lines)

**Rating: 7/10 — Clean, consistent within portal**

| Aspect | Finding | Severity |
|--------|---------|----------|
| JobsListView | Master-detail like RequestsView — consistent pattern | Good |
| Stats row | 4 stat cards (new/quoted/awarded/completed) — clear | Good |
| Quote submission | Inline form with amount + note — streamlined | Good |
| CalendarView | Simple grid with event dots — minimal but functional | Good |
| ProfileView | Form sections (personal, banking, trades, docs) — organized | Good |
| Bank details | **Displayed in plain text** — sensitive financial data with no masking | Medium |
| Unsaved changes | **No warning** when navigating away with edits | Medium |
| Trades toggle | Pill-style buttons for trade selection — nice UI | Good |
| File upload | Same bare pattern as admin views — no preview/progress | Medium |

### 4.16 Owner Portal: OwnerDashboard.vue (37 lines) & OwnerPropertiesView.vue (39 lines)

**Rating: 5.5/10 — Too minimal**

| Aspect | Finding | Severity |
|--------|---------|----------|
| Dashboard | Only 4 stat cards with loading text fallback | Medium |
| Error state | `catch { /* ignore */ }` — if API fails, shows "Loading..." forever | High |
| Loading skeleton | Plain "Loading..." text instead of skeleton loaders | Medium |
| Properties | Card grid — clean but not clickable to detail | Medium |
| No secondary content | No recent activity, alerts, or quick actions | Low |
| No guidance | No empty states with CTAs | Low |

### 4.17 TemplateEditorView.vue (2,414 lines)

**Rating: 6/10 — Ambitious feature, significant UX gaps**

This is the most complex view in the codebase and warrants detailed analysis.

#### Layout Structure
- Three-panel: collapsible AI chat (left) + editor (center) + field palette (right, 270px)
- Smart responsive collapse at 1200px for chat sidebar
- **No tablet/mobile layout below 1200px — completely unusable on smaller screens**

#### Editor (contenteditable)
| Issue | Severity |
|-------|----------|
| Uses deprecated `document.execCommand` API — unreliable across browsers | High |
| Manual page break calculation (`updatePageBreaks`) is fragile — depends on accurate height measurement | Medium |
| Tab key hijacked for indent — violates expectation that Tab moves focus | Medium |
| Font sizing uses inline `pt` units mixed with CSS `rem/px` — produces dirty HTML output | Medium |
| `execCommand('foreColor')` generates `<font>` tags (deprecated HTML) | Medium |
| No undo/redo beyond browser-level — loses page-break state | Medium |
| Recommendation: **Migrate to TipTap (ProseMirror-based)** for structured document model | — |

#### AI Chat Sidebar
| Issue | Severity |
|-------|----------|
| Can submit during `chatThinking` state — no input disabled state | Medium |
| AI can silently update document via `document_update.html` response — user might not notice | Medium |
| No message timestamps | Low |
| No way to clear chat history (except localStorage manipulation) | Low |
| Collapse state not persisted across sessions | Low |

#### Recipient/Actor Management
| Issue | Severity |
|-------|----------|
| 4-step hidden workflow: expand recipients → add actor → select actor → now field palette works | High |
| No visual indication that fields are actor-specific until an actor is selected | High |
| Delete actor requires hover to reveal button — low discoverability | Medium |
| No undo/confirmation on actor deletion | Medium |
| Should disable field buttons when no actor selected (currently shows toast after click) | Medium |

#### Field Palette (Right Sidebar)
| Issue | Severity |
|-------|----------|
| 5 major sections stacked in 270px width — severely cramped | Medium |
| Field buttons 2-column grid at ~110px each — hard for touch targets | Medium |
| "Drag or click to insert" only in title attributes — not discoverable | Medium |
| No visual feedback during drag beyond ring outline — no hover states on drop targets | Low |

#### Hardcoded Values
| Value | Location | Should Be |
|-------|----------|-----------|
| `A4_PAGE_HEIGHT = 1061px` | Constant | Good — documented |
| `w-[270px]` sidebar | Template | Design token |
| `max-w-[680px]` document | Template | Design token |
| `#2B2D6E`, `#FF3D7F`, `#111111` | Throughout | Design tokens |
| `background:#0d9488` drag ghost | JavaScript | Design token |
| `font-size:11px` merge field chips | Inline style | `text-micro` class |
| 16 color swatches | Color picker | Should match palette |

#### Step Indicator
- Shows 5 dots but only 2 labeled steps — visual mismatch
- Dots 1-3 filled, 4-5 empty — progression unclear
- Not clickable — just decoration
- Should either show full workflow or simplify to progress bar

#### Modal/Panel Issues
- 4+ panels can overlap: color picker, bg color picker, heading styles, field picker
- No backdrop dimming on panels — can click through to editor
- No escape key to close panels
- Heading color picker nested 2 levels deep — z-index chaos potential

---

## 5. Cross-Screen Consistency Analysis

### 5.1 Badge & Status Logic Duplication

The following functions are **copy-pasted** across views:

| Function | Duplicated In | Times |
|----------|--------------|-------|
| `priorityBadge(p)` | DashboardView, MaintenanceView, RequestsView, JobsListView | 4+ |
| `statusBadge(s)` | DashboardView, MaintenanceView, RequestsView, LeaseCalendarView, LeasesView | 5+ |
| `formatDate(iso)` | DashboardView, TenantsView, RequestsView, LeaseCalendarView, JobsListView, LeasesView | 6+ |
| `initials(name)` | AppLayout, SupplierLayout, OwnerLayout, TenantsView | 4 |

**Fix:** Extract to `src/utils/formatters.ts` and `src/composables/useStatusBadges.ts`.

### 5.2 Modal Pattern Inconsistency

| View | Pattern | Component |
|------|---------|-----------|
| PropertiesView | BaseModal | Consistent |
| SuppliersView | BaseModal | Consistent |
| DirectoryView | **Custom Teleport with manual z-index** | Inconsistent |
| EditLeaseDrawer | Teleport full-viewport | Custom |
| ImportLeaseWizard | Teleport full-viewport | Custom |
| TemplateEditorView | Absolute-positioned panels | Custom |

**Fix:** Standardize on BaseModal + BaseDrawer for all overlays.

### 5.3 Empty State CTAs

| View | Has Empty State | Has Action Button |
|------|----------------|-------------------|
| PropertiesView | Yes | Yes ("Add Property") |
| TenantsView | Yes | **No** — inconsistent |
| LeasesView | Yes | Yes ("Add Lease", "Import") |
| RequestsView | Yes | No (appropriate — issues come from tenants) |
| SuppliersView | Yes | Yes |
| OwnerDashboard | **No** — shows "Loading..." forever on error | — |

### 5.4 Search Implementation

| View | Component | Pattern |
|------|-----------|---------|
| PropertiesView | SearchInput | Good |
| TenantsView | SearchInput | Good |
| SuppliersView | SearchInput | Good |
| DirectoryView | **Custom inline search** | Inconsistent |
| RequestsView | **None** — filter pills only | Missing |
| JobsListView | **None** — filter pills only | Acceptable |

### 5.5 Error Handling

| Pattern | Count | Views |
|---------|-------|-------|
| `useToast()` on API error | ~6 | PropertiesView, SuppliersView, RequestsView, etc. |
| Silent `catch {}` | **12+** | OwnerDashboard, LeaseTemplatesView, LeaseCalendarView, SuppliersView, etc. |
| Inline error card | 1 | LoginView only |

**Problem:** About half the codebase silently swallows errors. Users see empty data with no explanation.

### 5.6 Loading State Patterns

| View | Pattern | Skeleton Count |
|------|---------|---------------|
| DashboardView | `animate-pulse` cards + table rows | 4 cards + 5 rows |
| PropertiesView | `animate-pulse` table rows | 4 rows |
| TenantsView | `animate-pulse` table rows | 5 rows |
| RequestsView | `animate-pulse` card placeholders | 6 cards |
| SuppliersView | `animate-pulse` rows | 5 rows |
| OwnerDashboard | **Plain "Loading..." text** | None — inconsistent |
| TemplateEditorView | `animate-pulse` document area | Good |

---

## 6. Accessibility Audit

### 6.1 Critical: No ARIA Labels on Icon Buttons

Every icon-only button in the app lacks `aria-label`. Examples:

| Component | Button | Missing |
|-----------|--------|---------|
| All layouts | Logout button (LogOut icon only) | `aria-label="Log out"` |
| AppLayout | Sidebar collapse toggle | `aria-label="Collapse sidebar"` |
| BaseModal | Close X button | `aria-label="Close dialog"` |
| BaseDrawer | Close X button | `aria-label="Close panel"` |
| LeasesView | Document count button | `aria-label="View documents"` |
| RequestsView | Close detail button | `aria-label="Close details"` |
| LoginView | Password toggle | `aria-label="Show password"` |

### 6.2 Critical: Color-Only Status Indication

Badges throughout the app use color alone to convey status:
- Red = urgent/closed, Amber = high/in-progress, Green = active/resolved, Blue = medium/info
- Users with color vision deficiency cannot distinguish these
- **Fix:** Add text labels (already present) AND icons (missing) — e.g., exclamation for urgent, clock for in-progress

### 6.3 High: Missing Semantic HTML

| Issue | Where |
|-------|-------|
| No `role="dialog"` / `aria-modal="true"` | BaseModal, BaseDrawer |
| No `scope="col"` on table headers | All table-wrap tables |
| No `<nav>` landmark | Sidebar navigation |
| No `<main>` landmark | Content area |
| No `aria-live` regions | Toast notifications, loading states |
| No `aria-expanded` | Collapsible sections, dropdowns |
| No focus trapping in modals | All modals/drawers |
| Form labels not associated | `<label>` exists but no `for`/`id` pairing |

### 6.4 High: No Keyboard Focus Indicators

- Default browser focus rings are suppressed or too subtle
- No `:focus-visible` styling defined
- Tab order unclear in complex forms (SuppliersView modal has multiple grid columns)
- TemplateEditorView hijacks Tab key for indent — breaks expected keyboard navigation

### 6.5 Medium: Progress Bars Lack ARIA

DashboardView occupancy bars and PropertiesView occupancy columns:
- Missing `role="progressbar"`
- Missing `aria-valuenow`, `aria-valuemin`, `aria-valuemax`
- Missing `aria-label` describing what the bar represents

---

## 7. Responsive Design Audit

### 7.1 Critical: TemplateEditorView

- **Unusable below 1200px** — three-panel layout with hardcoded widths
- No tablet layout (1024px)
- No mobile layout at all
- Right sidebar 270px + editor + chat = minimum ~900px needed
- Field palette buttons too small for touch (110px × ~32px)

### 7.2 High: LeaseBuilderView

- Left panel `w-[400px]` + right preview `w-[680px]` = 1080px minimum
- No responsive breakpoints — no layout stacking on mobile
- Should switch to vertical (form on top, preview below) on tablet

### 7.3 Medium: Tables on Mobile

- All `table-wrap` tables lack horizontal scroll wrapper
- On screens below 768px, columns will overflow or compress
- No column hiding or responsive table patterns
- Occupancy column's `min-w-[120px]` forces scroll on small screens

### 7.4 Medium: Modals on Small Screens

- BaseModal uses `max-w-md` / `max-w-lg` but content may exceed viewport height
- No `max-h-[90vh]` constraint visible
- SuppliersView create form (15+ fields) definitely overflows on mobile
- No mobile-optimized form layouts (always grid-cols-2)

### 7.5 Sidebar Responsive Behavior

- Sidebar collapses to 60px but doesn't overlay on mobile
- No touch gesture (swipe) to open/close
- Content area doesn't reclaim space effectively below 1024px

---

## 8. Interaction Design Issues

### 8.1 Form Validation Feedback

**Problem:** The design system defines `.input-error`, `.input-error-msg`, and `.input-help` classes, but **no view uses them**.

| View | Validation Approach | Issue |
|------|-------------------|-------|
| LoginView | HTML5 `required` only | No inline error messages |
| PropertiesView | `!form.name` disables submit | No field highlighting |
| SuppliersView | `!form.name \|\| !form.phone` disables submit | No indication which field is wrong |
| EditLeaseDrawer | None visible | No validation at all |
| LeaseBuilderView | Error message at top of form | Field-level errors missing |
| ESigningPanel | Amber border for missing email | Partial — good start |

**Recommendation:** Create a `useFormValidation(rules)` composable that:
1. Validates on blur and submit
2. Applies `.input-error` class to invalid fields
3. Shows `.input-error-msg` below each field
4. Scrolls to first error on submit

### 8.2 Destructive Actions

| View | Action | Pattern | Issue |
|------|--------|---------|-------|
| LeasesView | Delete lease | `window.confirm()` | Should use styled ConfirmDialog |
| SuppliersView | Delete supplier | `window.confirm()` | Same |
| RequestsView | Award quote | `window.confirm()` | Same |
| EditLeaseDrawer | Remove tenant/occupant | Immediate — no confirmation | Should confirm or support undo |

**Recommendation:** Create `ConfirmDialog.vue` — styled modal with title, message, destructive action button in `btn-danger`, and cancel.

### 8.3 Disabled Button States

Multiple views disable buttons with `:disabled` but no visual change:
- `opacity-50` not applied in several cases
- No `cursor-not-allowed`
- No tooltip explaining why the button is disabled

**Fix:** Add to `.btn` base class:
```css
.btn:disabled { @apply opacity-50 cursor-not-allowed; }
```

### 8.4 Success Feedback

| View | Action | Feedback |
|------|--------|----------|
| PropertiesView | Create property | Toast — good |
| SuppliersView | Create supplier | Toast — good |
| RequestsView | Change status | **None** — silently updates |
| RequestsView | Send dispatch | Toast — good |
| EditLeaseDrawer | Save changes | Toast — good |
| SupplierProfileView | Save profile | Toast — good |
| LeaseCalendarView | Mark complete | **None** — silently marks |

### 8.5 Hover States & Micro-interactions

| Element | Current | Improvement |
|---------|---------|-------------|
| Table rows | `hover:bg-gray-50` | Add `transition-colors duration-150` if missing |
| Card items | `hover:bg-gray-50` (some only) | Standardize across all clickable items |
| Buttons | Color change only | Add subtle `active:scale-[0.98]` for tactile feedback |
| Modals | Scale from 95% to 100% | Good — already implemented |
| Sidebar links | Background change | Good |
| Stat cards | **None** — not interactive | Add hover if making clickable |

---

## 9. UX Anti-Patterns & Friction Points

### 9.1 Silent Failures

**The most impactful UX issue in the app.** At least 12 instances of `catch {}` or `catch { /* ignore */ }`:

| File | Context | User Impact |
|------|---------|-------------|
| OwnerDashboard | Stats loading | Shows "Loading..." forever |
| LeaseTemplatesView | Template list | Shows empty grid, no error |
| LeaseCalendarView | Event loading | Shows empty calendar |
| LeaseCalendarView | Mark complete | Silently fails, no feedback |
| SuppliersView | Document upload | File "uploaded" but nothing happens |
| SuppliersView | Supplier loading | Empty table, no explanation |
| SupplierProfileView | Profile load | Blank form |

**Fix:** Replace every silent catch with `toast.error('Failed to load X. Please try again.')` and add retry affordance where appropriate.

### 9.2 Two Supplier Management Views

SuppliersView (under /maintenance/suppliers) and DirectoryView (under /suppliers) are **near-identical** interfaces managing the same data. This creates:
- User confusion about which is the "real" one
- Code duplication (same form logic, same table, same CRUD)
- Inconsistent patterns (BaseModal vs Teleport modals)

**Fix:** Merge into a single canonical view. If different permission levels are needed, use conditional rendering within one component.

### 9.3 TemplateEditor Actor Selection Flow

The recipient → field palette workflow is powerful but has a steep learning curve:
1. User must expand recipients section (if collapsed by scroll)
2. Add an actor (Landlord/Tenant/Occupant)
3. Click the actor to select them
4. Only then does the field palette become functional

**No onboarding, no guidance, no progressive disclosure.** A first-time user will click field buttons, see a toast error, and not understand why.

**Fix:** Either disable field buttons with a tooltip ("Select a recipient first") or add a guided first-use overlay.

### 9.4 Dispatch Terminology Confusion

RequestsView uses "Get Quotes" as the CTA button, but the modal is titled "Dispatch to Suppliers" and the process is about "dispatching" quote requests. Users may not understand:
- "Get Quotes" sounds like it will show existing quotes
- "Dispatch" is internal jargon
- The actual action is "Request quotes from suppliers"

**Fix:** Rename to "Request Quotes" with modal title "Select Suppliers for Quote Request".

### 9.5 No Unsaved Changes Warning

EditLeaseDrawer, SupplierProfileView, and TemplateEditorView all have forms that can accumulate changes, but **none warn before navigating away**. Users can lose work by:
- Clicking sidebar nav
- Browser back button
- Closing the drawer accidentally

**Fix:** Add `beforeRouteLeave` guard and `beforeunload` event listener when form is dirty.

### 9.6 Inferred vs. Explicit Validation

Several forms use disabled-button-as-validation:
```html
:disabled="saving || !form.name || !form.phone"
```

The user sees a grayed-out button but doesn't know **why** it's disabled. There are no inline error messages, no red borders, no "* required" indicators beyond the occasional asterisk.

**Fix:** Always show inline validation feedback. The design system already has `.input-error` and `.input-error-msg` — use them.

---

## 10. Recommendations Priority Matrix

### Immediate (Before Next Deploy)

| # | Finding | Severity | Effort | Impact |
|---|---------|----------|--------|--------|
| 1 | Replace all 12+ silent `catch {}` blocks with toast error messages | High | Low | Users finally know when things fail |
| 2 | Add `aria-label` to all icon-only buttons (logout, close, toggle, etc.) | Critical | Low | Screen reader users can navigate |
| 3 | Extract `formatDate()`, `initials()`, badge functions to shared utils | High | Low | Eliminates 20+ duplicate functions |
| 4 | Add `disabled:opacity-50 disabled:cursor-not-allowed` to `.btn` base | High | Trivial | Disabled buttons visible |
| 5 | Fix OwnerDashboard error state (shows "Loading..." forever) | High | Trivial | Functional error handling |

### Short-Term (Next 2 Sprints)

| # | Finding | Severity | Effort | Impact |
|---|---------|----------|--------|--------|
| 6 | Create `useFormValidation()` composable — apply `.input-error` on blur/submit | Critical | Medium | All forms get consistent validation |
| 7 | Replace `window.confirm()` with styled `ConfirmDialog.vue` | High | Low | Consistent with design system |
| 8 | Merge SuppliersView and DirectoryView into single canonical view | Critical | Medium | Eliminates ~800 lines of duplication |
| 9 | Standardize DirectoryView modals to use BaseModal/BaseDrawer | High | Medium | Consistent overlay patterns |
| 10 | Add unsaved changes warning to EditLeaseDrawer and TemplateEditorView | High | Medium | Prevents data loss |
| 11 | Add `role="dialog"`, `aria-modal`, focus trapping to BaseModal/BaseDrawer | High | Medium | Accessible modal interactions |
| 12 | Add `scope="col"` to all table headers | Medium | Trivial | Table accessibility |
| 13 | Create `SkeletonLoader.vue` variants (table row, card, stat) | Medium | Low | Consistent loading states |
| 14 | Add success toast to RequestsView status change and CalendarView mark complete | Medium | Trivial | Feedback for user actions |

### Medium-Term (Next Quarter)

| # | Finding | Severity | Effort | Impact |
|---|---------|----------|--------|--------|
| 15 | Make TemplateEditorView responsive (tablet layout, mobile fallback) | Critical | High | 2nd most-used feature becomes usable on tablets |
| 16 | Make LeaseBuilderView responsive (stack panels vertically on mobile) | High | Medium | Mobile-usable lease creation |
| 17 | Migrate TemplateEditor from `execCommand` to TipTap/ProseMirror | High | High | Modern, reliable editor |
| 18 | Add keyboard focus indicators (`:focus-visible` styling) | High | Medium | Keyboard users can navigate |
| 19 | Centralize all hardcoded colors into design tokens | Medium | Medium | Maintainable theming |
| 20 | Add TemplateEditor onboarding (actor selection guide, autocomplete hint) | Medium | Medium | Reduces learning curve |
| 21 | Add table sorting to PropertiesView, TenantsView, SuppliersView | Medium | Medium | Better data exploration |
| 22 | Add search to RequestsView | Medium | Low | Find specific requests |
| 23 | Add filter state persistence in URL query params | Medium | Medium | Shareable/bookmarkable views |
| 24 | Add responsive table patterns (horizontal scroll or column hiding) | Medium | Medium | Mobile-usable tables |
| 25 | Enrich OwnerDashboard with activity feed and quick actions | Medium | Medium | Better owner experience |

### Long-Term (Backlog)

| # | Finding | Severity | Effort | Impact |
|---|---------|----------|--------|--------|
| 26 | Add breadcrumb navigation for deep routes | Low | Medium | Clearer wayfinding |
| 27 | Add route-based page `<title>` updates | Low | Low | Better browser tab identification |
| 28 | Make email addresses clickable `mailto:` links in TenantsView | Low | Trivial | Quick contact |
| 29 | Hash-based avatar colors for tenant/user initials | Low | Low | Visual distinction |
| 30 | Add stat card click-through to list views on Dashboard | Low | Low | Dashboard → detail flow |
| 31 | Widen occupancy bars from `h-2` to `h-3` with hover tooltips | Low | Trivial | Better visibility |
| 32 | Add sidebar collapse state persistence to localStorage | Low | Trivial | Consistent layout preference |
| 33 | Extract BaseLayout from AppLayout/SupplierLayout/OwnerLayout | Low | Medium | DRY layout code |
| 34 | Add mobile hamburger overlay for sidebar | Medium | Medium | Mobile navigation |
| 35 | Add dark mode support | Low | High | User preference |

---

## Appendix A: Component Usage Map

| Component | Used By | Notes |
|-----------|---------|-------|
| BaseModal | PropertiesView, SuppliersView, RequestsView, LeaseTemplatesView, ESigningPanel | Well-adopted |
| BaseDrawer | SuppliersView, EditLeaseDrawer | Good — should replace Teleport drawers |
| EmptyState | PropertiesView, TenantsView, LeasesView, RequestsView, SuppliersView | Missing: OwnerDashboard, CalendarView |
| FilterPills | MaintenanceView, RequestsView, SuppliersView, JobsListView | Consistent |
| SearchInput | PropertiesView, TenantsView, SuppliersView | Missing: DirectoryView (uses custom), RequestsView |
| ToastContainer | AppLayout (global) | Used via `useToast()` composable |
| KlikkLogo | LoginView, AppLayout, SupplierLayout, OwnerLayout | Consistent |

## Appendix B: View Complexity & Risk Assessment

| View | Lines | Complexity | UX Risk | Priority |
|------|-------|------------|---------|----------|
| TemplateEditorView | 2,414 | Very High | High — unusable on mobile, deprecated APIs | P0 |
| SuppliersView | 778 | High | High — duplicated with DirectoryView | P0 |
| DirectoryView | 796 | High | High — duplicated with SuppliersView | P0 |
| EditLeaseDrawer | 715 | High | Medium — no unsaved warning, no validation | P1 |
| LeaseBuilderView | 689 | High | High — not responsive | P1 |
| ImportLeaseWizard | 684 | High | Low — well-designed UX flow | P2 |
| LeasesView | 613 | Medium | Low — good grouping pattern | P3 |
| ESigningPanel | 418 | Medium | Medium — cluttered, validation gaps | P2 |
| RequestsView | 402 | Medium | Medium — dispatch terminology confusion | P2 |
| All other views | <250 | Low | Low-Medium | P3 |

---

*End of UI/UX audit. This document should be reviewed alongside the technical audit (claude_opus_audit_2026-03-25.md) for a complete picture of the admin application's state.*
