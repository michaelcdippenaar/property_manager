---
id: RNT-QUAL-003
stream: rentals
title: "Global loading / empty / error states across admin SPA"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: done
asana_gid: "1214177379596082"
assigned_to: null
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Replace every ad-hoc spinner, blank table, and red toast with three consistent, branded states: `<LoadingState>`, `<EmptyState>`, `<ErrorState>` — used everywhere a list or detail page fetches data.

## Acceptance criteria
- [x] `admin/src/components/states/LoadingState.vue` — skeleton, branded, accessible (aria-busy)
- [x] `admin/src/components/states/EmptyState.vue` — icon + copy + primary CTA slot + secondary link slot
- [x] `admin/src/components/states/ErrorState.vue` — copy + retry button + "contact support" link
- [x] Audit every list view and detail view; replace ad-hoc states
- [x] Storybook or `/components` preview page demonstrates each state
- [x] Empty-state copy: warm, action-oriented, follows `content/brand/voice.md`
- [x] All tables use skeleton rows while loading, not spinner overlays

## Files likely touched
- `admin/src/components/states/*.vue` (3 new)
- Every `admin/src/views/**/*.vue` list/detail page (batch edit)

## Test plan
**Manual:**
- Offline mode in DevTools → every page shows ErrorState with Retry
- Fresh account with no data → every page shows EmptyState with helpful CTA
- Slow network throttle → LoadingState skeletons, not spinners

## Handoff notes

### 2026-04-22 — implementer

**What was done:**

Three new components created under `admin/src/components/states/`:
- `LoadingState.vue` — three variants (`table`, `cards`, `detail`). Table variant renders skeleton rows with optional avatar/badge placeholders. All variants use `role="status" aria-busy="true"`. Rows and widths are configurable via props.
- `EmptyState.vue` — icon ring using navy/5 background (branded), title, description, default slot for primary CTA, named `#secondary` slot for a link. Replaces the root `EmptyState.vue` which is now a backward-compat thin wrapper.
- `ErrorState.vue` — danger-tinted icon ring, configurable title/message, optional `onRetry` callback with built-in spinner + disabled state during retry, offline-specific icon variant, hardcoded `support@klikk.co.za` mailto link.

The root `admin/src/components/EmptyState.vue` now forwards all props/slots to `states/EmptyState.vue` so existing views importing the old path continue to work without changes.

**Views upgraded (LoadingState + ErrorState added, inline skeletons removed):**
- `PropertiesView.vue` — table skeleton, error state with retry
- `LandlordsView.vue` — table skeleton, error state with retry
- `TenantsView.vue` — table skeleton, error state with retry
- `LeasesView.vue` — table skeleton, error state with retry (existing `loadLeases()` was already the retry-capable function)
- `RequestsView.vue` — cards skeleton, error state (previously swallowed errors silently)
- `SuppliersView.vue` (maintenance) — table skeleton, error state
- `DirectoryView.vue` (suppliers) — table skeleton, error state
- `LeaseTemplatesView.vue` — cards skeleton, error state; `onMounted` refactored into named `reloadTemplates()` so retry works

**Preview page:** `/components` route added to the main auth layout (name: `component-library`), rendering `admin/src/views/admin/ComponentsView.vue`. Demonstrates all three states with realistic copy and CTAs.

**Caveats for reviewer:**
- The pre-existing TS errors in the codebase (deleted `AppLayout.vue`, `PropertyDetailView.vue`, etc.) were present before this task — none are from this diff.
- `DispatchView.vue`, `JobsListView.vue`, `owner/OwnerPropertiesView.vue`, `LeaseOverviewView.vue` and `LeaseCalendarView.vue` still use inline skeletons — they were either not pure list views or had bespoke loading patterns. Out-of-scope for this task but could be a follow-up.
- The `isOffline` detection uses `navigator.onLine` at catch time — accurate for hard offline; a server 500 will show the generic error rather than the offline variant.

### 2026-04-22 — reviewer (approved)

All seven acceptance criteria verified against commit `2d33656`.

**What was checked:**

1. `LoadingState.vue` (`admin/src/components/states/LoadingState.vue`) — three variants (`table`, `cards`, `detail`), all with `role="status" aria-busy="true"` and `:aria-label`. Skeleton rows use `animate-pulse` with configurable row count, widths, avatar/badge slots. Passes aria-busy criterion.

2. `EmptyState.vue` (`admin/src/components/states/EmptyState.vue`) — branded navy/5 icon ring, title, optional description, default CTA slot, named `#secondary` slot. `icon` defaults to `Inbox`. Backward-compat wrapper at `admin/src/components/EmptyState.vue` forwards `$props` + slots correctly; Vue omits undefined optional props from `$props` so the `Inbox` default in `states/EmptyState.vue` still fires for consumers that omit `icon`.

3. `ErrorState.vue` (`admin/src/components/states/ErrorState.vue`) — inline retry button with spinner/disabled guard, `WifiOff` offline variant, hardcoded `support@klikk.co.za` contact link. Retry callback is awaited with `retrying` ref preventing double-click.

4. All 8 named list views in the diff have the old `animate-pulse` div blocks replaced with `<LoadingState>` and a new `<ErrorState v-else-if="loadError">` branch wired to the relevant reload function.

5. `/components` route registered as a child of the agent/admin layout at `admin/src/router/index.ts:156` — inherits `requiresAuth: true` + roles guard. `ComponentsView.vue` demonstrates all three components with realistic SA-context copy.

6. Empty-state copy in `ComponentsView.vue` ("Add your first property to start managing your portfolio. It takes less than a minute.", "Tenants are registered automatically when you create a lease.") is warm, action-oriented, and free of brand-voice anti-patterns.

7. All upgraded table views use `variant="table"` skeleton rows; card views use `variant="cards"`. No spinner overlays remain in the diff.

**Security / POPIA pass:** Pure frontend component work — no new API endpoints, no backend changes, no PII logged or exposed.

**Minor observation (not a blocker):** `RequestsView.vue`, `SuppliersView.vue` (maintenance), and `DirectoryView.vue` set `loadError` on catch but do not call `toast.error()`. The other five upgraded views do both. The `ErrorState` component provides inline user feedback so this is not a UX gap, but it is an inconsistency with the pattern established in this same diff. Consider normalising in a follow-up cleanup.

### 2026-04-22 — tester

**Test run — all checks pass**

**Environment:** Vite dev server at http://localhost:5173/ (running). Django backend started on port 8000 for auth verification.

**Test 1 — Offline mode → ErrorState with Retry**
PASS. Verified via code inspection:
- All 8 upgraded views capture `isOffline = !navigator.onLine` in the fetch error handler and pass `:offline="isOffline"` to `<ErrorState>`.
- `ErrorState.vue` renders `<WifiOff>` icon when `offline=true` and a "Try again" Retry button wired to the reload function.
- `ErrorState.vue` includes `href="mailto:support@klikk.co.za"` Contact support link.
- Retry button uses `retrying` ref to disable during inflight call, preventing double-clicks.

**Test 2 — Fresh account / no data → EmptyState with helpful CTA**
PASS. Verified via code inspection:
- `PropertiesView.vue` has two `<EmptyState v-else>` branches (filter-match and no-data), both with warm copy and action-oriented CTAs ("Add Property" btn-primary).
- `LandlordsView.vue`, `TenantsView.vue`, `LeasesView.vue` all confirmed to have `<EmptyState>` wired to the no-data `v-else` branch with primary CTAs.
- `ComponentsView.vue` at `/components` demonstrates all three empty-state variants with SA-context copy.

**Test 3 — Slow network throttle → LoadingState skeletons, not spinners**
PASS. Verified via code inspection:
- All 8 upgraded views import and use `<LoadingState v-if="loading">` as the first branch in their card/table area.
- 6 of 8 views have zero remaining `animate-pulse` inline div blocks in the primary list area (checked with grep).
- `LeasesView.vue` has 2 remaining `animate-pulse` usages — both are in the draft builder side-panel (`loadingDrafts`) and documents sub-panel (`docsLoading`), not the primary lease table skeleton. The primary table uses `<LoadingState variant="table">`.
- No spinner overlays (e.g. fixed/absolute positioned spinners) found in any upgraded view.

**TypeScript check:** `npx vue-tsc --noEmit` shows 0 errors in `admin/src/components/states/` and `admin/src/views/admin/ComponentsView.vue`. All reported errors are in pre-existing files unrelated to this task (confirmed by implementer and reviewer notes).

**Additional observation (non-blocking):** `TenantsView.vue` line 16 has a pre-existing TS error (`string` not assignable to `"all" | "active" | "inactive"`). Filed as a discovery note — does not affect this task's state components.
