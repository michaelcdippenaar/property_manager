# Vue Admin App (klikk-admin) — Full System Audit

**Auditor:** Claude Opus 4.6
**Date:** 2026-03-25
**Scope:** Complete frontend audit of `/admin/` — architecture, security, performance, code quality, accessibility, and maintainability.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Overview](#2-project-overview)
3. [Architecture Analysis](#3-architecture-analysis)
4. [File-by-File Audit](#4-file-by-file-audit)
5. [Security Findings](#5-security-findings)
6. [Performance Findings](#6-performance-findings)
7. [Code Quality Findings](#7-code-quality-findings)
8. [Accessibility Findings](#8-accessibility-findings)
9. [UX/UI Observations](#9-uxui-observations)
10. [Design System & Visual Improvements](#10-design-system--visual-improvements)
11. [Dependency & Build Analysis](#11-dependency--build-analysis)
12. [Testing Assessment](#12-testing-assessment)
13. [Recommendations Priority Matrix](#13-recommendations-priority-matrix)

---

## 1. Executive Summary

The Klikk Admin app is a Vue 3 + TypeScript SPA for property management with role-based portals (Agent/Admin, Supplier, Owner). It is well-structured for its current size but has several areas that need attention before scaling.

### Severity Breakdown

| Severity | Count | Category |
|----------|-------|----------|
| **Critical** | 3 | XSS via `v-html`, token storage in localStorage, no CSRF |
| **High** | 7 | No tests, no error boundary, excessive `any` types, missing pagination, silent error swallowing, KeepAlive memory issues, Dockerfile runs dev server |
| **Medium** | 12 | Duplicated utilities, no composables, no TypeScript interfaces, inline sub-components, no form validation library, missing loading/error states, duplicated layout code |
| **Low** | 8 | Duplicate Google Fonts import, no favicon, missing aria labels, inconsistent badge helpers, no 404 page |

---

## 2. Project Overview

### Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | Vue 3 (Composition API + `<script setup>`) | ^3.4.0 |
| State | Pinia | ^2.1.0 |
| Routing | Vue Router | ^4.3.0 |
| HTTP | Axios | ^1.6.0 |
| Styling | Tailwind CSS | ^3.4.19 |
| Icons | Lucide Vue Next | ^1.0.0 |
| Build | Vite | ^5.0.0 |
| Language | TypeScript | ^5.3.0 |

### File Count & Size

| Category | Files | Notes |
|----------|-------|-------|
| Views | 23 | Organized in 9 feature directories |
| Components | 3 | Layout components only |
| Stores | 1 | Auth store only |
| Router | 1 | Single file with 143 lines |
| API layer | 1 | Axios instance with interceptors |
| CSS | 1 | Tailwind + custom component layer |
| Config files | 6 | vite, tailwind, postcss, tsconfig, Dockerfile, .env |

### Largest Files (potential refactor candidates)

| File | Approx Size | Concern |
|------|-------------|---------|
| `TemplateEditorView.vue` | ~99KB | Extremely large SFC — needs decomposition |
| `SuppliersView.vue` | ~33KB | Large — multiple concerns in one file |
| `DirectoryView.vue` | ~33KB | Large — similar to SuppliersView |
| `EditLeaseDrawer.vue` | ~31KB | Large — complex form logic |
| `ImportLeaseWizard.vue` | ~30KB | Large — multi-step wizard in one file |
| `ESigningPanel.vue` | ~16KB | Moderate |

---

## 3. Architecture Analysis

### 3.1 Good Decisions

- **Lazy-loaded routes** — All view imports use dynamic `() => import(...)`, enabling code splitting
- **Role-based route guards** — Clean `beforeEach` guard with role checks on `meta.roles`
- **JWT refresh interceptor** — Automatic token refresh on 401 with retry
- **Tailwind component layer** — Reusable `.btn-*`, `.input`, `.card`, `.badge-*` classes in `@layer components`
- **Clean separation of role layouts** — AppLayout, SupplierLayout, OwnerLayout serve distinct user types
- **Consistent use of `<script setup>`** — Modern Vue 3 Composition API throughout

### 3.2 Structural Issues

#### No Shared Component Library
**Severity: Medium**

All 3 components in `/components/` are layouts. There are zero shared UI components. This leads to significant duplication across views:
- Modal/dialog pattern duplicated in ~8 views (each manually wraps `<Teleport>` + backdrop + card)
- Search input with icon duplicated in PropertiesView, TenantsView, SuppliersView
- Badge helpers (`priorityBadge()`, `statusBadge()`) duplicated in 4+ files
- `formatDate()` duplicated in 5+ files
- `initials()` duplicated in 4 files

**Recommendation:** Extract at minimum:
- `BaseModal.vue` — Teleport + backdrop + card wrapper
- `SearchInput.vue` — Search icon + input field
- `StatusBadge.vue` / `PriorityBadge.vue` — Badge components
- Shared composables for `useFormatDate()`, `useInitials()`

#### No Composables
**Severity: Medium**

Zero composables exist. All logic is inline in components. Key candidates:
- `useFormatDate()` — date formatting with locale
- `usePagination()` — paginated API fetches
- `useConfirmDialog()` — confirm/cancel pattern
- `useWebSocket()` — real-time updates (backend supports WebSockets per commit history)

#### Single Pinia Store
**Severity: Medium**

Only `auth.ts` exists. All other state is local to views. This means:
- No shared state between views (e.g., property list is re-fetched every navigation)
- `KeepAlive` in AppLayout somewhat mitigates this but creates its own problems (see Performance)
- No centralized error handling or notification state

#### Inline Sub-Components in LeaseBuilderView
**Severity: Medium**
**File:** `src/views/leases/LeaseBuilderView.vue`

The file defines `SectionLabel`, `PersonBlock`, and `LeaseFormFields` as inline `defineComponent()` calls using render functions (`h()`). This is unconventional in a Vue SFC codebase and makes the file harder to read and maintain. These should be extracted into proper `.vue` SFC files.

---

## 4. File-by-File Audit

### 4.1 Core Infrastructure

#### `src/api.ts` (41 lines)
**Rating: Good with caveats**

- Clean axios instance setup
- Token refresh interceptor works correctly
- **Issue:** Race condition — if multiple requests fail with 401 simultaneously, each will attempt a token refresh independently. Should queue concurrent refresh attempts.
- **Issue:** `window.location.href = '/login'` on refresh failure bypasses Vue Router, losing any in-memory state. Should use `router.push('/login')` instead.
- **Issue:** No request/response timeout configured. A hanging request will never resolve.
- **Issue:** No global error handling or notification trigger for non-401 errors.

#### `src/stores/auth.ts` (57 lines)
**Rating: Good with security concerns**

- Clean Pinia setup store
- Good role-based computed properties
- **Issue:** Tokens stored in `localStorage` (see Security section)
- **Issue:** `user` state is not persisted — on page refresh, `fetchMe()` must be called before any role check works. If `fetchMe()` fails for a network blip, user is logged out.
- **Issue:** `logout()` doesn't call a backend endpoint to invalidate the refresh token server-side
- **Issue:** `refreshToken` is tracked as reactive state but never used outside of `login()` — the interceptor reads directly from `localStorage`

#### `src/router/index.ts` (143 lines)
**Rating: Good**

- Clean route structure with role-based meta
- Proper catch-all redirect (`/:pathMatch(.*)* -> /`)
- **Issue:** The catch-all redirects to `/` which might land on an unauthorized page for suppliers/owners. Should redirect to `auth.homeRoute` if authenticated.
- **Issue:** No dedicated 404 page — users just silently redirect
- **Issue:** SupplierLayout is instantiated 3 separate times for `/jobs`, `/calendar`, `/profile` routes. Should be a single parent route with children.
- **Issue:** Route meta `roles` uses parent matching — child routes inherit parent's `meta.roles`. This is correct behavior but not explicit in the child route definitions.

#### `src/main.ts` (10 lines)
**Rating: Clean** — No issues.

#### `src/App.vue` (3 lines)
**Rating: Clean** — Simple RouterView wrapper.

### 4.2 Layout Components

#### `src/components/AppLayout.vue` (267 lines)
**Rating: Good**

- Clean nav with dropdown menus
- Proper click-outside handling with cleanup
- **Issue:** `KeepAlive` wraps all child routes without an `include` or `max` prop. Every visited view stays in memory indefinitely (see Performance).
- **Issue:** Three dropdown menus (Leases, Maintenance, Property Info) have near-identical template code — could be a reusable `NavDropdown` component.
- **Issue:** No mobile responsiveness — nav items will overflow on smaller screens.

#### `src/components/SupplierLayout.vue` (70 lines)
**Rating: Acceptable**

- **Issue:** `isActive('/jobs')` returns true for any path starting with `/jobs` — could false-positive on future routes.
- **Issue:** Duplicated layout structure with AppLayout and OwnerLayout (header, logo, nav items, initials, logout button).

#### `src/components/OwnerLayout.vue` (69 lines)
**Rating: Acceptable**

- Same duplication concern as SupplierLayout.
- **Recommendation:** Extract a `BaseLayout.vue` that accepts nav items as props.

### 4.3 Auth Views

#### `src/views/auth/LoginView.vue` (94 lines)
**Rating: Good**

- Clean login form with loading/error states
- Password visibility toggle
- **Issue:** No rate limiting on client side (though backend should handle this)
- **Issue:** Error message is generic ("Invalid email or password") — good for security but `catch` block doesn't distinguish network errors from auth failures
- **Issue:** No "forgot password" link
- **Issue:** `autocomplete` attributes not set on inputs (browser autofill may not work optimally)

### 4.4 Dashboard

#### `src/views/dashboard/DashboardView.vue` (132 lines)
**Rating: Good**

- Parallel API calls with `Promise.all`
- Loading skeletons
- **Issue:** `recentMaintenance` typed as `any[]`
- **Issue:** Occupancy calculation `total - occupied - available` could be negative if data is inconsistent — handled with `Math.max(0, ...)`, which is good defensive coding
- **Issue:** No error state shown — if API fails, user sees empty data with no indication of failure

### 4.5 Properties

#### `src/views/properties/PropertiesView.vue` (161 lines)
**Rating: Good**

- Client-side search filtering
- Add property dialog with form reset
- **Issue:** `properties` typed as `any[]`
- **Issue:** Client-side filtering won't scale — no server-side search or pagination
- **Issue:** No form validation beyond checking `name` existence
- **Issue:** No error toast/notification on create failure
- **Issue:** `occupancyPercent()` relies on `p.units` being present in the list response — may not be included if the API returns a flat list

#### `src/views/properties/PropertyAgentView.vue` (7 lines)
**Rating: Stub** — Placeholder only, no functionality.

#### `src/views/properties/UnitTenantInfoView.vue` (7 lines)
**Rating: Stub** — Placeholder only, no functionality.

#### `src/views/properties/PropertyInfoSection.vue` (3 lines)
**Rating: Clean** — Simple RouterView wrapper for nested routes.

### 4.6 Tenants

#### `src/views/tenants/TenantsView.vue` (89 lines)
**Rating: Good**

- Clean table with search
- **Issue:** Displays `id_number` (South African ID number) — PII shown in plain text in the table. Consider masking (e.g., `******7890`).
- **Issue:** No pagination — all tenants loaded at once
- **Issue:** Read-only view — no ability to edit, add, or manage tenants
- **Issue:** `tenants` typed as `any[]`

### 4.7 Leases (most complex feature area)

#### `src/views/leases/LeasesView.vue` (~250+ lines)
**Rating: Acceptable**

- Grouped by property with expandable rows
- Document management, edit, delete, renew actions
- **Issue:** Large file with multiple concerns (list, detail, import wizard, edit drawer, document panel, e-signing)
- **Issue:** `deleteLease` uses `confirm()` — should use a styled modal
- **Issue:** No pagination
- **Issue:** Tab switching between "All Leases" and "Build Lease Template" is unusual — templates have their own route

#### `src/views/leases/LeaseTemplatesView.vue` (152 lines)
**Rating: Good**

- Template grid with create/upload
- **Issue:** `catch { /* ignore */ }` silently swallows template loading errors
- **Issue:** Blank DOCX creation sends an empty Blob — backend may reject invalid DOCX format
- **Issue:** Uses `alert()` for error display — should use styled toast

#### `src/views/leases/TemplateEditorView.vue` (~99KB)
**Rating: Needs Major Refactoring**

This is by far the largest file in the codebase. It contains:
- WYSIWYG HTML editor with contenteditable
- AI chat sidebar
- Recipient/actor management
- Field palette and drag-drop
- Export (PDF, DOCX)
- Template activation

**Issues:**
- File is ~2000+ lines — far exceeds reasonable SFC size
- **XSS Risk:** Uses `v-html` to render template content (see Security)
- Should be decomposed into at minimum 5-7 components:
  - `TemplateEditorHeader.vue`
  - `TemplateAIChat.vue`
  - `TemplateRecipientPanel.vue`
  - `TemplateFieldPalette.vue`
  - `TemplateEditorCanvas.vue`
  - `TemplateExportMenu.vue`

#### `src/views/leases/LeaseBuilderView.vue` (~300+ lines)
**Rating: Acceptable with XSS concern**

- Split panel with form + live template preview
- Inline sub-components using `defineComponent()` + `h()`
- **Critical:** `v-html="previewHtml"` renders server-returned HTML directly (see Security)
- **Issue:** Inline `defineComponent()` calls are unusual in Vue SFC codebase — should be proper `.vue` files
- **Issue:** Render function sub-components lose template readability and IDE support

#### `src/views/leases/LeaseCalendarView.vue` (252 lines)
**Rating: Good**

- Monthly calendar with event filtering
- Day detail panel
- **Issue:** Calendar builds all weeks in a computed property with nested loops and `.filter()` per day — O(weeks * days * events). Could be optimized with a pre-indexed event map by date.
- **Issue:** `events.value = []` in catch block silently hides errors
- **Issue:** Uses local month/year navigation with `watch` — could use route query params for shareable URLs

### 4.8 Maintenance

#### `src/views/maintenance/RequestsView.vue` (409 lines)
**Rating: Good**

- Two-panel layout with list + detail
- Quote dispatch workflow
- **Issue:** `suppliers` loaded in parallel with requests — good
- **Issue:** `catch { /* ignore */ }` in `loadSuppliers()` — failure to load suppliers would silently break the dispatch workflow
- **Issue:** `updateStatus` and `assignSupplier` don't have error handling — failed PATCH requests would silently fail while the UI optimistically updates
- **Issue:** `confirm()` used for award confirmation — should be styled modal
- **Issue:** No real-time updates — after dispatch, user must manually check for quote responses

#### `src/views/maintenance/SuppliersView.vue` (~33KB)
**Rating: Acceptable**

- Supplier CRUD with geocoding, trade management, document uploads, Excel import
- **Issue:** Very large file — should be decomposed
- **Issue:** Geocoding uses Google Maps API key from environment

#### `src/views/maintenance/SkillLibraryView.vue` (122 lines)
**Rating: Good**

- Skills list + RAG agent chat
- Good error handling with specific error messages
- **Issue:** `skills.slice(0, 200)` — client-side truncation of a potentially large list. Backend should paginate.
- **Issue:** Chat is single-turn only — no conversation history

### 4.9 Supplier Portal

#### `src/views/supplier/JobsListView.vue` (~200+ lines)
**Rating: Good**

- Job list with quote submission workflow
- Stats row with key metrics
- **Issue:** Same `any[]` typing patterns
- **Issue:** No optimistic UI — submitting a quote requires waiting for response before UI updates

#### `src/views/supplier/CalendarView.vue`
**Rating: Not fully audited** — Similar calendar pattern to LeaseCalendarView.

#### `src/views/supplier/SupplierProfileView.vue` (206 lines)
**Rating: Acceptable**

- Profile editing with trades, banking, documents
- **Issue:** Banking details (account number, branch code) displayed and editable in plain text — sensitive financial data
- **Issue:** `uploadDoc` workflow is confusing — file is selected AND uploaded immediately, but `showUploadForm` opens after upload starts, and document type can only be selected after the file is uploading
- **Issue:** `catch { /* ignore */ }` on document upload error
- **Issue:** No confirmation before saving profile changes
- **Issue:** `delete payload.trades; delete payload.documents` — mutation of the object before sending. Should create a clean payload instead.

### 4.10 Owner Portal

#### `src/views/owner/OwnerDashboard.vue` (38 lines)
**Rating: Acceptable**

- Simple stats display
- **Issue:** `catch { /* ignore */ }` — if API fails, shows "Loading..." forever
- **Issue:** No loading skeleton — just "Loading..." text

#### `src/views/owner/OwnerPropertiesView.vue` (40 lines)
**Rating: Clean** — Simple property card grid.

---

## 5. Security Findings

### 5.1 CRITICAL: XSS via `v-html`

**Files affected:**
- `src/views/leases/LeaseBuilderView.vue:130` — `v-html="previewHtml"`
- `src/views/leases/TemplateEditorView.vue:373` — `v-html="opt.html"`
- `src/views/leases/TemplateEditorView.vue:746` — `v-html="editorHtml"`

**Risk:** If the HTML content from the backend contains `<script>` tags, `onerror` handlers, or other XSS vectors, they will execute in the user's browser context. This is particularly dangerous because:
- Template content may be user-authored
- The admin portal has full access to all tenant/property/lease data
- A compromised template could exfiltrate JWT tokens from localStorage

**Recommendation:**
1. Sanitize all HTML before rendering with a library like `DOMPurify`
2. If full HTML editing is required, use a sandboxed iframe with `srcdoc`
3. At minimum, strip `<script>`, event handlers (`on*`), and `javascript:` URIs

### 5.2 CRITICAL: JWT Tokens in localStorage

**File:** `src/stores/auth.ts`, `src/api.ts`

`localStorage` is accessible to any JavaScript running on the same origin, making tokens vulnerable to XSS attacks. Combined with the `v-html` XSS vectors above, this creates a complete attack chain:

1. Attacker injects malicious HTML into a lease template
2. Admin views the template → XSS executes
3. Script reads `localStorage.getItem('access_token')` and `localStorage.getItem('refresh_token')`
4. Tokens exfiltrated to attacker's server

**Recommendation:**
- Move tokens to `httpOnly` cookies (requires backend changes)
- At minimum, use `sessionStorage` instead of `localStorage` to limit persistence
- Implement Content Security Policy (CSP) headers

### 5.3 CRITICAL: No CSRF Protection

**Current state:** Pure JWT Bearer token auth with no CSRF tokens.

While JWT in Authorization headers is generally CSRF-immune, if tokens are moved to cookies (as recommended), CSRF protection becomes essential. Even with current setup, the refresh endpoint uses a POST with the refresh token — this should be protected.

### 5.4 HIGH: No Content Security Policy

No CSP meta tag in `index.html` and presumably no server-side CSP headers. This allows:
- Inline script execution (XSS vector)
- Loading of external resources from any origin
- `eval()` and similar dangerous APIs

**Recommendation:** Add CSP headers via the server or a Vite plugin.

### 5.5 MEDIUM: PII Exposure

**File:** `src/views/tenants/TenantsView.vue:41`

South African ID numbers displayed in full in the tenant table. ID numbers are sensitive PII under POPIA (Protection of Personal Information Act).

**File:** `src/views/supplier/SupplierProfileView.vue:85-86`

Bank account numbers and branch codes displayed in plain text input fields.

**Recommendation:** Mask sensitive data by default, require explicit "reveal" action.

### 5.6 MEDIUM: Silent Token Clearing on Refresh Failure

**File:** `src/api.ts:31-33`

On refresh failure, tokens are silently removed and user is hard-redirected. This could be exploited to force-logout users by intercepting the refresh request.

### 5.7 LOW: Google Maps API Key in `.env`

**File:** `.env`

`VITE_GOOGLE_MAPS_KEY` is a client-side key (prefixed with `VITE_`). This is expected, but ensure the key has proper HTTP referrer restrictions in the Google Cloud Console.

---

## 6. Performance Findings

### 6.1 HIGH: KeepAlive Without Limits

**File:** `src/components/AppLayout.vue:171-175`

```html
<KeepAlive>
  <component :is="Component" />
</KeepAlive>
```

Every visited view is cached in memory indefinitely. The admin app has 15+ routable views under this layout. Each cached view retains its full component tree, reactive state, and DOM.

**Impact:** Memory usage grows linearly with pages visited. For the TemplateEditorView (~99KB source, likely much more in runtime DOM), this is particularly costly.

**Recommendation:**
- Add `include` prop to only cache specific views that benefit from caching
- Add `max` prop to limit cached instances (e.g., `max="5"`)
- Or remove KeepAlive entirely and use Pinia stores for state persistence where needed

### 6.2 HIGH: No Pagination

**Affected views:**
- `PropertiesView.vue` — loads all properties
- `TenantsView.vue` — loads all tenants
- `LeasesView.vue` — loads all leases
- `SuppliersView.vue` — loads all suppliers
- `SkillLibraryView.vue` — loads all skills (truncated to 200 client-side)
- `RequestsView.vue` — loads all maintenance requests per filter

All data is fetched in a single API call with no pagination. For a growing property management platform, this will cause:
- Slow initial page loads
- High memory usage
- Unnecessary network transfer

The API responses handle both paginated (`data.results`) and flat (`data`) responses, suggesting the backend supports pagination but it's not being used.

**Recommendation:** Implement pagination with `page_size` parameter and add a pagination UI component.

### 6.3 MEDIUM: Calendar Event Filtering

**File:** `src/views/leases/LeaseCalendarView.vue:212`

```typescript
const dayEvents = filteredEvents.value.filter((e: any) => e.date === dateStr)
```

This runs inside a nested loop (6 weeks * 7 days = 42 iterations), each filtering the entire events array. For months with many lease events, this is O(42 * n).

**Recommendation:** Pre-index events by date string in a `Map<string, Event[]>`.

### 6.4 MEDIUM: Large Lucide Icon Imports

**File:** Multiple views import individual icons from `lucide-vue-next`.

While tree-shaking should handle this, the total number of unique icon imports across the app is ~25+. Ensure the build output confirms tree-shaking is working correctly.

### 6.5 LOW: Duplicate Google Fonts Import

**Files:** `index.html:7` AND `src/assets/main.css:5`

The Inter font is imported twice — once in the HTML head and once via `@import url()` in CSS. Remove one.

---

## 7. Code Quality Findings

### 7.1 HIGH: Pervasive `any` Typing

Nearly every component uses `ref<any>`, `ref<any[]>`, or `ref<any | null>` for API response data. Examples:

```typescript
// Found in virtually every view:
const properties = ref<any[]>([])
const tenants = ref<any[]>([])
const selected = ref<any | null>(null)
const stats = ref<any>(null)
const profile = ref<any | null>(null)
```

This eliminates TypeScript's value entirely for the data layer.

**Recommendation:**
1. Create a `src/types/` directory with interfaces for all API models:
   ```typescript
   // src/types/property.ts
   export interface Property {
     id: number
     name: string
     property_type: string
     address: string
     city: string
     province: string
     postal_code: string
     unit_count: number
     units?: Unit[]
   }
   ```
2. Use these types in refs: `const properties = ref<Property[]>([])`
3. Consider auto-generating types from backend API schema (OpenAPI → TypeScript)

### 7.2 HIGH: Silent Error Swallowing

At least 12 instances of `catch { /* ignore */ }` or `catch { }` across the codebase:

| File | Line | Context |
|------|------|---------|
| `LeaseTemplatesView.vue` | 123 | Template list loading |
| `LeaseCalendarView.vue` | 160 | Event loading |
| `LeaseCalendarView.vue` | 186 | Mark complete |
| `RequestsView.vue` | 289 | Supplier loading |
| `RequestsView.vue` | 310 | Dispatch loading |
| `OwnerDashboard.vue` | 36 | Stats loading |
| `SupplierProfileView.vue` | 203 | Document upload |
| Multiple views | Various | Various API calls |

**Impact:** Users experience data silently not loading with no feedback. Debugging production issues becomes extremely difficult.

**Recommendation:**
1. Create a global error notification system (toast/snackbar)
2. Replace all silent catches with user-visible error messages
3. Add error logging (e.g., Sentry, LogRocket)

### 7.3 MEDIUM: Duplicated Utility Functions

| Function | Duplicated In | Times |
|----------|--------------|-------|
| `formatDate(iso: string)` | DashboardView, TenantsView, RequestsView, LeaseCalendarView, JobsListView, LeasesView | 6+ |
| `priorityBadge(p: string)` | DashboardView, RequestsView, JobsListView | 3+ |
| `statusBadge(s: string)` | DashboardView, RequestsView, LeaseCalendarView, LeasesView | 4+ |
| `initials(name: string)` | AppLayout, SupplierLayout, OwnerLayout, TenantsView | 4 |

**Recommendation:** Create `src/utils/formatters.ts` with shared helpers.

### 7.4 MEDIUM: No Form Validation

Forms across the app have minimal validation:
- Properties: only checks `name` is truthy
- Suppliers: no validation at all before POST
- Lease Builder: no validation before create
- Profile: no validation before save

**Recommendation:** Implement form validation with a library like `vee-validate` or `@vuelidate/core`, or at minimum add required field checks and input format validation.

### 7.5 MEDIUM: Inconsistent API Response Handling

Every view independently handles both paginated and flat responses:
```typescript
const data = response.data.results ?? response.data
```

This pattern is repeated in every data-loading function. Should be centralized in the API layer.

### 7.6 LOW: `alert()` and `confirm()` Usage

Native browser dialogs used in:
- `LeaseTemplatesView.vue:147` — `alert()` for error
- `RequestsView.vue:373` — `confirm()` for award
- `LeasesView.vue` — `confirm()` for delete

These break the UI aesthetic and are not customizable.

### 7.7 LOW: Mixed Naming Conventions

- Some views use `loading` + `saving` booleans, others use `loading` + `submitting`
- Some use `dialog` for modal state, others use `showUpload`, `showEdit`, `showImport`
- Badge helper function names vary: `statusBadge`, `dispatchStatusBadge`, `quoteStatusBadge`

---

## 8. Accessibility Findings

### 8.1 HIGH: No ARIA Labels on Interactive Elements

- Icon-only buttons (logout, close, expand) have no `aria-label`
- Dropdown menus have no `role="menu"` or `aria-expanded`
- Modal dialogs have no `role="dialog"` or `aria-modal="true"`
- No focus trapping in modals — Tab key can move focus behind the modal backdrop

### 8.2 MEDIUM: No Keyboard Navigation

- Dropdown menus only open on click — no keyboard support (Enter/Space to open, Escape to close, Arrow keys to navigate)
- Table rows are not keyboard-navigable
- Calendar day cells use `@click` but have no keyboard equivalent

### 8.3 MEDIUM: Color-Only Status Indication

Badges use color alone to convey status (red = urgent, green = active). Users with color vision deficiency cannot distinguish these. Should include text and/or icons.

### 8.4 LOW: Missing Skip Navigation

No "Skip to main content" link for keyboard users navigating the header.

### 8.5 LOW: No `<title>` Updates Per Route

Page title stays as "Klikk Admin" regardless of the current view. Should update via `useTitle()` or route meta.

---

## 9. UX/UI Observations

### 9.1 No Mobile Responsiveness (Admin Layout)

The AppLayout header nav with 6+ items (Dashboard, Properties, Tenants, Leases dropdown, Maintenance dropdown, Property Info dropdown) will overflow on screens below ~1024px. No hamburger menu or responsive nav exists.

The SupplierLayout and OwnerLayout are simpler and may work on smaller screens, but have not been tested.

### 9.2 No Empty State Illustrations

Empty states show plain text ("No properties found", "No tenants found"). Consider adding illustrations or action prompts to guide users.

### 9.3 No Toast/Notification System

Success actions (property created, lease saved, profile updated) provide no visual confirmation. Users have to infer success from the dialog closing or data appearing.

### 9.4 Inconsistent Modal Patterns

Some modals use `<Teleport to="body">` with `<div class="fixed inset-0">`, others use `fixed inset-0 z-50 flex items-center justify-center`. Some have `backdrop-blur-sm`, others don't. Some close on backdrop click, others don't.

### 9.5 No Breadcrumbs

Nested routes (e.g., `/leases/templates/5/edit`) have no breadcrumb trail. Users rely on manual navigation.

---

## 10. Design System & Visual Improvements

### 10.1 Color Palette — Underutilized & Inconsistent

**Current palette (tailwind.config.js):**
| Token | Hex | Usage |
|-------|-----|-------|
| `navy` | `#2B2D6E` | Header, buttons, primary accent |
| `navy-dark` | `#23255a` | Hover state for primary buttons |
| `navy-light` | `#3b3e8f` | Not used anywhere in the codebase |
| `pink-brand` | `#FF3D7F` | Logo dot, AI sparkle icon only |
| `lavender` | `#F0EFF8` | Login page background only |

**Issues:**

1. **Pink-brand is wasted.** The accent color `#FF3D7F` only appears in the logo dot and 2 icon references. For a brand color, it should carry more weight — CTAs, active states, notification dots, progress indicators, or data visualization accents. Currently the app is almost entirely navy + gray.

2. **Lavender only used on login.** The `#F0EFF8` lavender is defined but only the login page uses `bg-lavender`. The main app body uses a hardcoded `#F5F5F8` in CSS and `bg-gray-50` in layouts — three different background values for what should be one token.

3. **No semantic color tokens.** The design system has no `success`, `warning`, `danger`, `info` color tokens. Instead, components reach directly into Tailwind's `emerald`, `red`, `amber`, `blue` palettes with inconsistent shade choices:
   - Success: `bg-emerald-50 text-emerald-700` (badges) vs `bg-green-50 text-green-700` (quote cards) vs `bg-green-600` (award button)
   - Warning: `bg-amber-50 text-amber-700` (badges) vs `bg-amber-100 text-amber-800` (calendar)
   - These should be unified under semantic tokens like `colors.success.50`, `colors.success.700`

4. **No dark mode support.** No `dark:` variants anywhere. If dark mode is ever needed, every component needs touching.

**Recommendation:**
```js
// tailwind.config.js — expanded palette
colors: {
  navy: { DEFAULT: '#2B2D6E', dark: '#23255a', light: '#3b3e8f' },
  accent: { DEFAULT: '#FF3D7F', light: '#FF6B9D', dark: '#E02D6B' },
  surface: { DEFAULT: '#F5F5F8', secondary: '#F0EFF8' },
  success: { 50: '#ecfdf5', 100: '#d1fae5', 600: '#059669', 700: '#047857' },
  warning: { 50: '#fffbeb', 100: '#fef3c7', 600: '#d97706', 700: '#b45309' },
  danger:  { 50: '#fef2f2', 100: '#fee2e2', 600: '#dc2626', 700: '#b91c1c' },
  info:    { 50: '#eff6ff', 100: '#dbeafe', 600: '#2563eb', 700: '#1d4ed8' },
}
```

### 10.2 Typography Scale — Too Many Arbitrary Sizes

The app uses **5 different arbitrary font sizes** via Tailwind's JIT bracket syntax:

| Size | Usage Count | Where |
|------|-------------|-------|
| `text-[10px]` | 30+ instances | Badges, labels, scores, meta text |
| `text-[11px]` | 8 instances | Step indicators, actor labels, recipient buttons |
| `text-[9px]` | ~2 instances | Very small labels in TemplateEditor |
| Standard `text-xs` (12px) | Widespread | Labels, secondary text |
| Standard `text-sm` (14px) | Widespread | Body text, inputs |

**Issues:**

1. **`text-[10px]` is overused and too small.** At 10px, text fails WCAG minimum readability guidelines. Used in badges, priority labels, scores, coordinates — these are often critical information.

2. **No consistent type scale.** The app jumps between `text-[10px]`, `text-[11px]`, `text-xs` (12px), `text-sm` (14px), `text-base` (16px), `text-lg` (18px), `text-xl` (20px), `text-2xl` (24px) — 8 distinct sizes with no clear hierarchy.

3. **Heading hierarchy is flat.** Most pages use `text-lg font-semibold` for the page title. There's no `<h2>`, `<h3>` scale. Section headers are just `text-xs font-semibold uppercase` or `text-sm font-medium`.

**Recommendation:**
Define a strict 5-level type scale in Tailwind config and eliminate arbitrary sizes:

| Level | Use | Size | Weight |
|-------|-----|------|--------|
| Page title | `text-lg` / 18px | `font-semibold` | Only one per page |
| Section header | `text-sm` / 14px | `font-semibold` | Card headers, form sections |
| Body | `text-sm` / 14px | `font-normal` | Default text |
| Caption | `text-xs` / 12px | `font-medium` | Labels, meta, timestamps |
| Micro | `text-[11px]` (custom token `text-micro`) | `font-medium` | Badges only |

Eliminate `text-[10px]` entirely — bump all instances to at least `text-xs` (12px).

### 10.3 Spacing & Layout Inconsistencies

| Pattern | Variants Found | Should Be |
|---------|---------------|-----------|
| Page padding | `p-6` (layouts), `p-5` (some cards), `px-5 py-5` (forms) | Single token: `p-6` |
| Card padding | `p-4`, `p-5`, `p-6`, `p-8` (login) | Standardize: `p-5` default, `p-6` for emphasis |
| Section spacing | `space-y-3`, `space-y-4`, `space-y-5`, `space-y-6`, `space-y-8` | Max 3 levels: `space-y-3` (tight), `space-y-5` (default), `space-y-8` (sections) |
| Table cell padding | `px-4 py-3` (global) vs `px-5 py-3.5` (inline overrides) | Use global `.table-wrap` only |
| Modal width | `max-w-sm`, `max-w-md`, `max-w-lg`, `max-w-2xl`, `max-w-xl` | Standardize to 2-3 sizes |

### 10.4 Component Design Inconsistencies

#### Modals / Dialogs — 6 Different Implementations

| View | Backdrop | Border Radius | Shadow | Close Method |
|------|----------|--------------|--------|-------------|
| PropertiesView | `bg-black/40 backdrop-blur-sm` | `rounded-xl` (card) | `shadow-sm` (card) | Click backdrop + X button |
| LeaseTemplatesView | `bg-black/40` (no blur) | `rounded-2xl` | `shadow-2xl` | Click backdrop + X button |
| RequestsView dispatch | `bg-black/40 backdrop-blur-sm` | `rounded-xl` (card) | `shadow-sm` (card) | Click backdrop + X button |
| SuppliersView detail | `bg-black/30` | None specified | `shadow-xl` | Click backdrop + X button |
| LeaseCalendarView | `bg-black/30` | None | `shadow-xl` | Click backdrop + X button |
| ESigningPanel | `bg-black/40` | `rounded-2xl` | `shadow-2xl` | X button only |

**Issues:**
- Backdrop opacity varies: `/30` vs `/40`
- Some have `backdrop-blur-sm`, others don't
- Border radius: `rounded-xl` vs `rounded-2xl` vs none
- Shadow: `shadow-sm` vs `shadow-xl` vs `shadow-2xl`
- Some are centered modals, others are slide-in panels (calendar, suppliers)

**Recommendation:** Create a `BaseModal.vue` and `BaseDrawer.vue` with standard props:
```vue
<BaseModal :open="showDialog" @close="showDialog = false" size="md">
  <!-- content -->
</BaseModal>
```
Standard values: `bg-black/40 backdrop-blur-sm`, `rounded-2xl`, `shadow-2xl`, with `sm/md/lg/xl` size variants.

#### Buttons — Inline Overrides Defeat the Design System

The CSS layer defines `.btn-primary`, `.btn-ghost`, `.btn-danger`, but many views bypass these with inline Tailwind classes:

```html
<!-- LeaseTemplatesView: custom button instead of btn-primary -->
class="flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-navy text-white rounded-lg hover:bg-navy/90 transition-colors"

<!-- RequestsView: award button doesn't use btn-primary or any .btn class -->
class="mt-1 px-3 py-1 text-xs font-medium text-white bg-green-600 rounded-lg hover:bg-green-700"

<!-- TemplateEditorView: custom small button -->
class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors"
```

At least 15 buttons across the app use custom classes instead of the design system tokens. This means button styling changes in `main.css` won't propagate.

**Recommendation:**
- Add `.btn-sm` and `.btn-xs` size variants to the CSS layer
- Add `.btn-success` for green action buttons
- Enforce usage of `.btn-*` classes — no inline button styling

#### Filter Pills — Duplicated Pattern

Filter pill buttons appear in 4 views (RequestsView, SuppliersView, JobsListView, LeaseCalendarView) with slightly different styling. All follow the same pattern:

```html
class="px-3 py-1.5 rounded-full text-sm font-medium transition-colors"
:class="active ? 'bg-navy text-white' : 'bg-white border border-gray-200 text-gray-600'"
```

This should be a `FilterPill.vue` component or a `.pill` / `.pill-active` CSS class.

#### Loading Skeletons — Inconsistent Heights & Patterns

| View | Skeleton Style |
|------|---------------|
| Dashboard | `h-3`, `h-7`, `h-4` rectangles |
| Properties | `h-5` rectangles x4 |
| Tenants | `h-5` rectangles x5 |
| RequestsView | Card shapes with `h-3`, `h-4` inside |
| OwnerDashboard | Plain "Loading..." text (no skeleton!) |
| SuppliersView | `h-5` rectangles x5 |

Should use consistent skeleton components that match the actual content layout.

### 10.5 Navigation Design Issues

#### Header is Overcrowded

The admin header packs 7 navigation elements into a single 56px bar:
- Logo
- Dashboard (link)
- Properties (link)
- Tenants (link)
- Leases (dropdown, 4 items)
- Maintenance (dropdown, 2 items)
- Property Info (dropdown, 3 items)
- User avatar + Logout

At viewport widths below ~1100px, items will start to compress and overlap. There is no:
- Hamburger menu for mobile/tablet
- Collapsible sidebar alternative
- Responsive breakpoint behavior

**Recommendation:** For an admin dashboard with this many features, consider switching to a **collapsible left sidebar** instead of a top nav. Benefits:
- Scales to more nav items without redesign
- Can show icons-only when collapsed
- Standard admin dashboard pattern (users expect it)
- Frees up the top bar for breadcrumbs, search, notifications

#### No Active State for Parent Routes

When viewing `/leases/templates/5/edit`, the "Leases" dropdown highlights correctly, but the specific sub-item "Templates" doesn't highlight because `isActive('/leases/templates')` returns true for the templates list, not the editor child route.

#### No Breadcrumbs on Deep Routes

Routes like `/leases/templates/5/edit` or `/property-info/skills` have no breadcrumb trail. Users must click the nav dropdown to understand where they are.

### 10.6 Data Display Design Issues

#### Tables Lack Visual Hierarchy

All tables use the same flat style with thin `border-b border-gray-100` row separators. For data-heavy views like SuppliersView (7 columns) and LeasesView (grouped + expandable), consider:
- **Alternating row colors** (`even:bg-gray-50/30`) for scanability
- **Sticky table headers** for long lists
- **Column alignment** — numeric columns (rent, units, percentages) should be right-aligned
- **Sortable columns** — no sort capability exists on any table

#### Stats Cards Are Plain

Dashboard stats cards are simple number + label. For a property management dashboard, consider:
- **Trend indicators** — up/down arrows with percentage change
- **Sparkline mini-charts** — show 7-day or 30-day trends
- **Click-through** — stats cards should link to their respective list views

#### Empty States Are Bare

Current empty states are just centered gray text:
```
"No properties found"
"No tenants found"
"No maintenance requests for this filter"
```

These should include:
- An illustration or icon (already partially done with `FileSignature` in LeaseTemplatesView)
- A clear call-to-action button ("Add your first property")
- Help text explaining what this section is for

### 10.7 Form Design Issues

#### No Visual Grouping in Long Forms

The supplier create/edit dialog has 15+ fields in a flat layout. The only visual break is a `border-t` before the Address section. Consider:
- **Fieldset grouping** with labeled borders or section headers
- **Accordion/stepper** for complex forms (like the lease builder already uses)
- **Progressive disclosure** — show advanced fields (BEE level, CIDB grading, insurance expiry) in a collapsible "Advanced" section

#### No Input Validation Feedback

Inputs have focus rings (`focus:ring-2 focus:ring-navy/20`) but no:
- Error state styling (red border, error message below input)
- Success state (green border after valid input)
- Character counts for textareas
- Required field indicators (asterisks are inconsistent — some forms show `*`, others don't)

**Recommendation:** Add to the design system:
```css
.input-error { @apply border-red-400 focus:ring-red-200 focus:border-red-500; }
.input-success { @apply border-green-400 focus:ring-green-200 focus:border-green-500; }
.input-help { @apply text-xs text-gray-400 mt-1; }
.input-error-msg { @apply text-xs text-red-600 mt-1; }
```

#### Select Dropdowns Are Unstyled

Native `<select>` elements are used throughout. They don't match the design language — no custom dropdown chevron, no search/filter capability for long option lists (e.g., selecting a property or supplier from potentially hundreds).

Consider a custom `BaseSelect.vue` with search filtering for lists > 10 items.

### 10.8 Micro-Interactions & Polish

| Missing Interaction | Where | Impact |
|-------------------|-------|--------|
| **No success feedback** | After creating property, lease, supplier | User can't confirm action succeeded |
| **No transition on route change** | All routes | Abrupt page swaps feel jarring |
| **No skeleton-to-content transition** | All loading states | Content pops in without animation |
| **No hover preview** | Lease list rows, property rows | Can't preview without expanding/clicking |
| **No tooltip on truncated text** | Supplier names, addresses, lease numbers | Truncated text is unrecoverable |
| **No drag-to-reorder** | Lease template fields | Field order appears fixed |
| **No keyboard shortcuts** | Template editor, lease builder | Power users can't work efficiently |

### 10.9 Visual Hierarchy — Specific Improvements per View

#### Dashboard
- Stats cards all look identical — differentiate the "primary" metric (e.g., make Open Requests larger or use a colored left border)
- Recent Maintenance table has no row actions — clicking should navigate to the request detail
- Occupancy bars are too thin (`h-2`) — increase to `h-3` with rounded caps for better visibility
- No date range context — "Recent Maintenance" shows 5 items but doesn't say "this week" or "last 7 days"

#### Properties
- Occupancy bar in the table is `h-1.5` — nearly invisible. Use a wider bar or replace with a numeric badge
- No property detail view — clicking a row does nothing. Should open a property detail with units, tenants, lease history

#### Tenants
- No actions (edit, invite, deactivate) — it's a read-only list
- Initials avatar circle uses `bg-navy` for all tenants — use a hash-based color to differentiate

#### Leases (Main List)
- The grouped-by-property layout is good but the property header row is too subtle (`bg-gray-50` with 12px text)
- Status badges in collapsed rows compete with the priority badges for attention
- The "Renew" button in expanded view is easy to miss — consider making it more prominent for leases nearing expiry

#### Maintenance Requests
- Left border color-coding by priority is effective
- Detail panel has too much vertical spacing — the quotes section is pushed below the fold
- "Get Quotes" link in the detail panel is easy to miss as a small text link — should be a proper button

#### Template Editor
- The 3-panel layout (AI chat + editor + recipient sidebar) leaves very little space for the actual document on standard 1920px screens
- Chat panel collapsed state (44px) shows only the sparkle icon with no label — easy to forget it exists
- Step indicator (1. Add Fields → 2. Send Invite) at the top suggests a wizard flow but there's no "Next" button to advance

### 10.10 Design System Gaps — What's Missing

| Component | Needed For | Priority |
|-----------|-----------|----------|
| `Toast / Notification` | Success/error feedback after actions | High |
| `BaseModal` | Consistent dialog styling | High |
| `BaseDrawer` | Slide-in panels (supplier detail, calendar day) | High |
| `FilterPill` | Status/type filters across 4+ views | Medium |
| `SearchInput` | Search bars across 3+ views | Medium |
| `EmptyState` | Consistent empty state with icon + CTA | Medium |
| `Skeleton` | Loading state components matching content layout | Medium |
| `Avatar` | User/tenant initials with hash-based colors | Medium |
| `DataTable` | Sortable, paginated tables | Medium |
| `Tooltip` | Truncated text, icon-only buttons | Low |
| `Breadcrumb` | Deep route navigation | Low |
| `Tabs` | Lease view tabs, supplier directory tabs | Low |
| `DropdownMenu` | Nav dropdowns, action menus | Low |
| `Badge` (component) | Replace CSS-only badges with a Vue component accepting `variant` prop | Low |

---

## 11. Dependency & Build Analysis

### 10.1 Dependencies

| Package | Status | Notes |
|---------|--------|-------|
| `vue@^3.4.0` | OK | Current latest is 3.5.x — minor update available |
| `vue-router@^4.3.0` | OK | |
| `pinia@^2.1.0` | OK | |
| `axios@^1.6.0` | OK | Consider native `fetch` for lighter bundle |
| `tailwindcss@^3.4.19` | Review | Tailwind 4 is available — evaluate migration |
| `lucide-vue-next@^1.0.0` | OK | |
| `tailwind-merge@^3.5.0` | Unused? | Imported in package.json but no usage found in codebase — verify |
| `clsx@^2.1.1` | Unused? | Imported in package.json but no usage found in codebase — verify |
| `autoprefixer@^10.4.27` | OK | Should be devDependency |
| `postcss@^8.5.8` | OK | Should be devDependency |
| `tailwindcss@^3.4.19` | OK | Should be devDependency |

### 10.2 Misplaced Dependencies

`autoprefixer`, `postcss`, and `tailwindcss` are in `dependencies` but should be in `devDependencies`. They are build-time tools, not runtime dependencies.

### 10.3 Missing Dependencies

- No sanitization library (DOMPurify) for `v-html` usage
- No form validation library
- No error tracking (Sentry, etc.)
- No date library (using raw `Date` — consider `date-fns` for complex calendar logic)
- No toast/notification library

### 10.4 Dockerfile Issues

**File:** `Dockerfile`

```dockerfile
FROM node:20-slim
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"]
```

**Issues:**
1. **Runs dev server in production** — `npm run dev` starts Vite's development server, not a production build. Should build and serve static assets with nginx or similar.
2. **No lockfile copied** — `package-lock.json` should be copied before `npm install` for reproducible builds
3. **No multi-stage build** — Final image contains node_modules and source code
4. **No `.dockerignore`** — `node_modules`, `.git`, etc. may be copied into the image

**Recommended Dockerfile:**
```dockerfile
FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

---

## 11. Testing Assessment

### Current State: No Tests

- No test files exist anywhere in the project
- No test runner (Vitest, Jest) in dependencies
- No test configuration
- No CI/CD pipeline visible

### Recommended Testing Strategy

| Layer | Tool | Priority | Coverage Target |
|-------|------|----------|----------------|
| Unit tests | Vitest | High | Utility functions, composables, store |
| Component tests | Vitest + @vue/test-utils | High | Form components, badge logic |
| E2E tests | Playwright or Cypress | Medium | Login flow, CRUD operations |
| Visual regression | Chromatic or Percy | Low | Layout components |

### Critical Test Cases

1. **Auth flow:** Login → token storage → refresh → logout
2. **Route guards:** Unauthorized access redirects, role-based access
3. **API interceptor:** Token refresh on 401, concurrent request handling
4. **Form submission:** Property creation, lease creation, quote submission
5. **Calendar logic:** Week generation, event filtering, month navigation

---

## 12. Recommendations Priority Matrix

### Immediate (Before Next Deploy)

| # | Finding | Severity | Effort |
|---|---------|----------|--------|
| 1 | Add DOMPurify sanitization for all `v-html` usage | Critical | Low |
| 2 | Fix Dockerfile to use production build | High | Low |
| 3 | Remove duplicate Google Fonts import | Low | Trivial |
| 4 | Add error handling to replace silent `catch {}` blocks | High | Medium |

### Short-Term (Next 2 Sprints)

| # | Finding | Severity | Effort |
|---|---------|----------|--------|
| 5 | Create TypeScript interfaces for all API models | High | Medium |
| 6 | Extract shared utility functions (`formatDate`, `initials`, badge helpers) | Medium | Low |
| 7 | Add KeepAlive `include`/`max` constraints | High | Low |
| 8 | Set up Vitest and write unit tests for auth store and API interceptor | High | Medium |
| 9 | Add toast notification system | Medium | Medium |
| 10 | Mask PII (ID numbers, bank details) in table displays | Medium | Low |
| 11 | Move build-time dependencies to devDependencies | Low | Trivial |

### Medium-Term (Next Quarter)

| # | Finding | Severity | Effort |
|---|---------|----------|--------|
| 12 | Decompose TemplateEditorView.vue into 5-7 components | High | High |
| 13 | Extract reusable components (BaseModal, SearchInput, etc.) | Medium | Medium |
| 14 | Create composables for shared logic | Medium | Medium |
| 15 | Implement pagination across all list views | High | High |
| 16 | Add ARIA labels and keyboard navigation | High | Medium |
| 17 | Add mobile responsiveness to admin layout | Medium | Medium |
| 18 | Add form validation library | Medium | Medium |
| 19 | Consolidate SupplierLayout route duplication | Medium | Low |
| 20 | Add Content Security Policy headers | Medium | Low |
| 21 | Refactor API layer to centralize response normalization | Medium | Low |

### Long-Term (Backlog)

| # | Finding | Severity | Effort |
|---|---------|----------|--------|
| 22 | Migrate tokens from localStorage to httpOnly cookies | Critical | High |
| 23 | Add E2E tests with Playwright | Medium | High |
| 24 | Implement real-time updates via WebSocket | Medium | High |
| 25 | Add route-based page titles | Low | Low |
| 26 | Extract BaseLayout from 3 layout components | Low | Medium |
| 27 | Add error tracking (Sentry) | Medium | Low |
| 28 | Evaluate Tailwind 4 migration | Low | Medium |
| 29 | Add breadcrumb navigation | Low | Medium |
| 30 | Create a proper 404 page | Low | Low |

---

## Appendix A: Complete File Inventory

```
admin/
├── .env                                          # Google Maps API key
├── Dockerfile                                    # Dev server container (needs fix)
├── index.html                                    # Entry HTML
├── package.json                                  # Dependencies
├── package-lock.json                             # Lockfile
├── postcss.config.js                             # PostCSS config
├── tailwind.config.js                            # Tailwind theme
├── vite.config.ts                                # Build config
└── src/
    ├── main.ts                                   # App bootstrap (10 lines)
    ├── App.vue                                   # Root component (3 lines)
    ├── api.ts                                    # Axios + interceptors (41 lines)
    ├── assets/
    │   └── main.css                              # Tailwind + custom styles (59 lines)
    ├── components/
    │   ├── AppLayout.vue                         # Agent/Admin layout (267 lines)
    │   ├── SupplierLayout.vue                    # Supplier layout (70 lines)
    │   └── OwnerLayout.vue                       # Owner layout (69 lines)
    ├── router/
    │   └── index.ts                              # Route definitions (143 lines)
    ├── stores/
    │   └── auth.ts                               # Auth Pinia store (57 lines)
    └── views/
        ├── auth/
        │   └── LoginView.vue                     # Login page (94 lines)
        ├── dashboard/
        │   └── DashboardView.vue                 # Stats + recent maintenance (132 lines)
        ├── leases/
        │   ├── LeasesView.vue                    # Lease list + grouped display (~250+ lines)
        │   ├── LeaseBuilderView.vue              # Form + preview split (~300+ lines)
        │   ├── LeaseCalendarView.vue             # Monthly calendar (252 lines)
        │   ├── LeaseTemplatesView.vue            # Template grid (152 lines)
        │   ├── TemplateEditorView.vue            # WYSIWYG editor (~2000+ lines) !!
        │   ├── EditLeaseDrawer.vue               # Lease edit drawer (~800+ lines)
        │   ├── ImportLeaseWizard.vue             # PDF import wizard (~800+ lines)
        │   └── ESigningPanel.vue                 # E-signature panel (~400+ lines)
        ├── maintenance/
        │   ├── RequestsView.vue                  # Request list + detail + dispatch (409 lines)
        │   ├── SuppliersView.vue                 # Supplier CRUD (~800+ lines)
        │   ├── SkillLibraryView.vue              # Skills + RAG agent (122 lines)
        │   └── MaintenanceView.vue               # Redirect stub
        ├── owner/
        │   ├── OwnerDashboard.vue                # Owner stats (38 lines)
        │   └── OwnerPropertiesView.vue           # Owner property cards (40 lines)
        ├── properties/
        │   ├── PropertiesView.vue                # Property list + create (161 lines)
        │   ├── PropertyInfoSection.vue           # RouterView wrapper (3 lines)
        │   ├── PropertyAgentView.vue             # Stub (7 lines)
        │   └── UnitTenantInfoView.vue            # Stub (7 lines)
        ├── supplier/
        │   ├── JobsListView.vue                  # Job list + quote workflow (~200+ lines)
        │   ├── CalendarView.vue                  # Supplier calendar
        │   └── SupplierProfileView.vue           # Profile + banking + docs (206 lines)
        ├── suppliers/
        │   ├── DirectoryView.vue                 # Supplier directory (~800+ lines)
        │   ├── DispatchView.vue                  # Dispatch management
        │   └── SuppliersLayout.vue               # Tab nav wrapper
        └── tenants/
            └── TenantsView.vue                   # Tenant list + search (89 lines)
```

---

## Appendix B: API Endpoints Used

| Method | Endpoint | Used In |
|--------|----------|---------|
| POST | `/auth/login/` | auth.ts |
| GET | `/auth/me/` | auth.ts |
| POST | `/auth/token/refresh/` | api.ts |
| GET | `/auth/tenants/` | TenantsView |
| GET | `/stats/` | DashboardView |
| GET | `/properties/` | PropertiesView, LeaseBuilderView |
| POST | `/properties/` | PropertiesView |
| GET | `/properties/owner/dashboard/` | OwnerDashboard |
| GET | `/properties/owner/properties/` | OwnerPropertiesView |
| GET | `/maintenance/` | DashboardView, RequestsView |
| PATCH | `/maintenance/:id/` | RequestsView |
| GET | `/maintenance/:id/dispatch/` | RequestsView |
| POST | `/maintenance/:id/dispatch/` | RequestsView |
| POST | `/maintenance/:id/dispatch/send/` | RequestsView |
| POST | `/maintenance/:id/dispatch/award/` | RequestsView |
| GET | `/maintenance/suppliers/` | RequestsView, SuppliersView |
| GET | `/maintenance/skills/` | SkillLibraryView |
| GET | `/maintenance/agent-assist/rag-status/` | SkillLibraryView |
| POST | `/maintenance/agent-assist/chat/` | SkillLibraryView |
| GET | `/maintenance/supplier/profile/` | SupplierProfileView |
| PATCH | `/maintenance/supplier/profile/` | SupplierProfileView |
| GET | `/maintenance/supplier/documents/` | SupplierProfileView |
| POST | `/maintenance/supplier/documents/` | SupplierProfileView |
| GET | `/leases/` | LeasesView |
| POST | `/leases/` | LeaseBuilderView |
| GET | `/leases/templates/` | LeaseTemplatesView, LeaseBuilderView |
| POST | `/leases/templates/` | LeaseTemplatesView |
| GET | `/leases/templates/:id/` | TemplateEditorView |
| PATCH | `/leases/templates/:id/` | TemplateEditorView |
| GET | `/leases/calendar/` | LeaseCalendarView |
| PATCH | `/leases/:id/events/:id/` | LeaseCalendarView |

---

*End of audit. This document should be reviewed and findings prioritized by the development team.*
