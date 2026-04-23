---
id: RNT-QUAL-006
stream: rentals
title: "Owner dashboard: data freshness, cache invalidation, and activity feed"
feature: owner_dashboard
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
asana_gid: "1214177462887240"
assigned_to: null
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Owner dashboard data is stale by minutes-to-hours in places (cached aggregates not invalidated on write). Owners need near-real-time visibility to trust the platform.

## Acceptance criteria
- [ ] Invalidate owner dashboard cache on: rent payment received, lease signed, maintenance created/closed, mandate signed
- [ ] "Last updated" timestamp visible on each widget
- [ ] Recent activity feed: last 20 events across their portfolio (rent received, maintenance opened, lease signed, etc.)
- [ ] Payment performance widget reflects this month in real time
- [ ] Works across owner web + owner mobile surface (if present)

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
