---
id: RNT-QUAL-025
stream: rentals
title: "Fix throttle test isolation — shared cache state causes flaky test_429_after_threshold_exceeded"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214195383099701"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Isolate the throttle test class cache backend so `test_429_after_threshold_exceeded` passes when run as part of the full esigning suite, not just in isolation.

## Acceptance criteria
- [ ] `TestPublicSignMinuteThrottle` uses `@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "throttle-tests"}})` (or equivalent) to prevent cache contamination from prior test classes
- [ ] All 17 rate-limit tests pass when run as part of the full esigning suite: `pytest apps/esigning/ apps/test_hub/esigning/ -v`

## Files likely touched
- `backend/apps/test_hub/esigning/unit/test_rate_limits.py`

## Test plan
**Automated:**
- `cd backend && pytest apps/esigning/ apps/test_hub/esigning/ -v` — confirm all 17 rate-limit tests pass
- Run the full suite `pytest apps/test_hub/` — confirm no flaky failures

## Handoff notes
2026-04-22: Promoted from discovery `2026-04-22-throttle-test-isolation.md` (found during RNT-003). Rate-limit test is a security control verification — flakiness masks real throttle regressions.
