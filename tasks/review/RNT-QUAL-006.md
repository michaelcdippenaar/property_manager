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
updated: 2026-04-23
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
