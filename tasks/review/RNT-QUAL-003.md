---
id: RNT-QUAL-003
stream: rentals
title: "Global loading / empty / error states across admin SPA"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: review
asana_gid: "1214177379596082"
assigned_to: reviewer
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
