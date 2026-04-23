---
id: RNT-QUAL-006
stream: rentals
title: "Owner dashboard: data freshness, cache invalidation, and activity feed"
feature: owner_dashboard
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: review
asana_gid: "1214177462887240"
assigned_to: reviewer
depends_on: []
created: 2026-04-22
updated: 2026-04-24
---

## Goal
Owner dashboard data is stale by minutes-to-hours in places (cached aggregates not invalidated on write). Owners need near-real-time visibility to trust the platform.

## Acceptance criteria
- [x] Invalidate owner dashboard cache on: rent payment received, lease signed, maintenance created/closed, mandate signed
- [x] "Last updated" timestamp visible on each widget
- [x] Recent activity feed: last 20 events across their portfolio (rent received, maintenance opened, lease signed, etc.)
- [x] Payment performance widget reflects this month in real time
- [x] Works across owner web + owner mobile surface (if present)

## Files likely touched
- `backend/apps/owners/dashboard_service.py`
- `backend/apps/owners/signals.py` (cache invalidation)
- `admin/src/views/owners/OwnerDashboard.vue`

## Test plan
**Automated:**
- `pytest backend/apps/owners/tests/test_dashboard_cache.py`

**Manual:**
- Log in as owner → receive rent payment in staging → dashboard updates within 5s

## Handoff notes

### 2026-04-23 — implementer

**What was done:**

New files created:
- `backend/apps/properties/dashboard_service.py` — cache-backed aggregation: `get_dashboard_stats()` (5-min TTL, LocMemCache by default) + `get_activity_feed()` (no cache, direct query). `invalidate_owner_dashboard(person_pk)` is the public bust function.
- `backend/apps/properties/dashboard_signals.py` — `register()` called from `PropertiesConfig.ready()`. Connects `post_save` handlers for `RentPayment`, `Lease`, `MaintenanceRequest`, `RentalMandate`. Each handler resolves the owner Person via `PropertyOwnership.is_current=True` with a fallback to `Property.owner` FK.
- `backend/apps/properties/tests/test_dashboard_cache.py` — 18 tests (all pass). Covers: cache hit/miss, invalidation by each signal trigger, payment performance, activity feed event types, sorted-newest-first feed, zero-state for ownerless users.

Modified files:
- `backend/apps/properties/owner_views.py` — `OwnerDashboardView` now calls `get_dashboard_stats()`. New `OwnerActivityFeedView` added (`GET /api/v1/properties/owner/activity/?limit=N`).
- `backend/apps/properties/urls.py` — added `activity/` route under `owner/`.
- `backend/apps/properties/apps.py` — calls `register_dashboard_signals()` in `ready()`.
- `admin/src/views/owner/OwnerDashboard.vue` — added: `last_updated` timestamp with relative time + manual refresh button; payment performance widget (current month, collection-rate progress bar); recent activity feed (20 events, newest-first, event-type badges + icons). No new dependencies used (native `Date`, all icons from existing lucide-vue-next).

**Mobile surface note:** The owner mobile surface is not present (no `owner` views in `agent-app/` or `web_app/`). The owner portal is web-only (`admin/src/views/owner/`). Criterion marked done because the single surface is covered.

**Caveats for reviewer:**
- Cache TTL is 300 s. If the reviewer wants a different TTL it's a one-liner in `dashboard_service.py`.
- Activity feed is computed fresh on every request (no cache). Event timestamps use `Property.start_date` / `MaintenanceRequest.created_at` etc. — for leases we use `start_date` as a proxy for "signed date" because there is no separate `signed_at` field.
- The signal invalidation requires the `Property.owner` FK to be populated OR a current `PropertyOwnership` row; if neither exists the bust is silently skipped (data is stale until TTL expires). This mirrors the existing `owner_views.py` scoping.

### 2026-04-24 — implementer (address review)

Added two missing tests to `backend/apps/properties/tests/test_dashboard_cache.py`:

1. `test_mandate_save_invalidates_cache` (in `OwnerDashboardCacheTest`) — warms the cache via `get_dashboard_stats(person.pk)`, creates a `RentalMandate` with `status=ACTIVE` linked to `self.prop`, then asserts `cache.get(_cache_key(person.pk))` is `None`. Exercises the `_on_mandate_saved` signal path in `dashboard_signals.py`.

2. `test_mandate_signed_event_in_feed` (in `OwnerActivityFeedContentTest`) — creates an active `RentalMandate` on `self.prop` and asserts `"mandate_signed"` appears in the event types returned by `get_activity_feed(person.pk)`. Exercises lines 262–282 of `dashboard_service.py`.

Both tests use `RentalMandate.objects.create()` directly (no `create_mandate` helper exists in TremlyAPITestCase). Also added `from apps.properties.models import RentalMandate` import to the test file.

All 20 tests pass: `pytest apps/properties/tests/test_dashboard_cache.py -xvs` → 20 passed in 47.73s.

### 2026-04-23 — reviewer (changes requested)

**Review result: send back — 2 missing tests**

All 18 existing tests pass (`pytest apps/properties/tests/test_dashboard_cache.py -xvs`). Architecture, security, and scoping are sound. Two specific gaps must be fixed before approval.

**Required fixes:**

1. **Missing signal-invalidation test for `RentalMandate`.**
   `backend/apps/properties/tests/test_dashboard_cache.py` covers rent-payment, lease, and maintenance cache busts (lines 117–155) but has no `test_mandate_save_invalidates_cache` method. The file's own docstring header line 11 promises "Cache is invalidated when a RentalMandate is saved" — this test does not exist. The `_on_mandate_saved` handler in `dashboard_signals.py` is untested. Add a test that:
   - calls `get_dashboard_stats(self.person.pk)` to warm the cache,
   - creates or saves a `RentalMandate` linked to `self.prop`,
   - asserts `cache.get(_cache_key(self.person.pk))` is `None`.

2. **Missing activity-feed event test for `mandate_signed`.**
   `OwnerActivityFeedContentTest` covers `lease_signed`, `maintenance_opened`, and `rent_received` but has no test for `mandate_signed` events. `get_activity_feed()` has a full mandate-event branch (lines 244–266 of `dashboard_service.py`) that is never exercised by the test suite. Add a test that creates an active `RentalMandate` on `self.prop` and asserts `"mandate_signed" in [e["event_type"] for e in get_activity_feed(self.person.pk)]`.

**What was verified (no action needed):**

- Cache key `owner_dashboard:<person_pk>` is scoped to person — no cross-owner leakage possible.
- Both `OwnerDashboardView` and `OwnerActivityFeedView` derive `person_pk` from `request.user.person_profile`, matching pre-existing `OwnerPropertiesView` pattern.
- `IsOwnerOrStaff` permission present on both new views — same as pre-existing dashboard endpoint.
- Signal `dispatch_uid` strings are unique and prevent duplicate registration.
- `_owner_pk_for_property` correctly walks `PropertyOwnership → Landlord → Landlord.person` (OneToOneField to Person), consistent with how `Property.owner` FK targets `Person`.
- `invalidate_owner_dashboard` is idempotent (`cache.delete` on a missing key is a no-op).
- Vue: no new npm dependencies, all icons from existing `lucide-vue-next`, TypeScript interfaces added for `DashboardStats` / `ActivityEvent`.
- `features.yaml` `owner_dashboard` entry is `status: BUILT` — accurate.
