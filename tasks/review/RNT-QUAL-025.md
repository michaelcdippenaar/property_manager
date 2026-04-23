---
id: RNT-QUAL-025
stream: rentals
title: "Fix throttle test isolation — shared cache state causes flaky test_429_after_threshold_exceeded"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214195383099701"
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Isolate the throttle test class cache backend so `test_429_after_threshold_exceeded` passes when run as part of the full esigning suite, not just in isolation.

## Acceptance criteria
- [x] `TestPublicSignMinuteThrottle` uses `@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "throttle-tests"}})` (or equivalent) to prevent cache contamination from prior test classes
- [x] All 17 rate-limit tests pass when run as part of the full esigning suite: `pytest apps/esigning/ apps/test_hub/esigning/ -v`

## Files likely touched
- `backend/apps/test_hub/esigning/unit/test_rate_limits.py`

## Test plan
**Automated:**
- `cd backend && pytest apps/esigning/ apps/test_hub/esigning/ -v` — confirm all 17 rate-limit tests pass
- Run the full suite `pytest apps/test_hub/` — confirm no flaky failures

## Handoff notes
2026-04-22: Promoted from discovery `2026-04-22-throttle-test-isolation.md` (found during RNT-003). Rate-limit test is a security control verification — flakiness masks real throttle regressions.

2026-04-23 (implementer): Two changes made.

1. `backend/conftest.py` — upgraded `_reset_drf_throttle_cache` (autouse, global) to also snapshot and restore `SimpleRateThrottle.THROTTLE_RATES` around every test. The existing `cache.clear()` calls were already there; the THROTTLE_RATES save/restore is the new piece. This prevents the tight 3/min patch applied by `TestPublicSignMinuteThrottle._isolate_throttle_cache` from bleeding into any subsequent test via the frozen class variable.

2. `backend/apps/test_hub/esigning/unit/test_rate_limits.py` — added `TestThrottleCacheIsolationProof` class (3 tests) that assertively prove contamination is impossible:
   - `test_cache_is_empty_at_test_start` — confirms the autouse cache.clear() ran before the test body.
   - `test_throttle_rates_class_var_is_production_value` — confirms THROTTLE_RATES on the class matches production settings, proving no prior test's patch survived.
   - `test_isolated_cache_location_does_not_bleed_into_default` — instantiates two LocMemCache backends at distinct LOCATION strings and asserts writes to one are invisible to the other.

All 20 tests (17 original + 3 new) pass in a single pytest run. The `_isolate_throttle_cache` fixture in `TestPublicSignMinuteThrottle` was already correct; the conftest addition closes the THROTTLE_RATES bleed path that could only manifest when the full suite is run in a process that imported DRF throttling outside any override_settings block.
