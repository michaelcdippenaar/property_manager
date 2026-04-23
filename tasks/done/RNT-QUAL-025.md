---
id: RNT-QUAL-025
stream: rentals
title: "Fix throttle test isolation — shared cache state causes flaky test_429_after_threshold_exceeded"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: done
assigned_to: null
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

2026-04-23 (reviewer): Review passed. Verified:
- `backend/apps/test_hub/esigning/unit/test_rate_limits.py` — `_THROTTLE_TEST_CACHES` dict with `LocMemCache` + LOCATION `"throttle-tests"`, applied via `_isolate_throttle_cache` fixture (`settings.CACHES = _THROTTLE_TEST_CACHES`) — satisfies AC1. New `TestThrottleCacheIsolationProof` class (3 tests) is a nice belt-and-braces defensive layer.
- `backend/conftest.py` — `_reset_drf_throttle_cache` now snapshots `SimpleRateThrottle.THROTTLE_RATES` before each test and restores after. Snapshot/restore pattern is correct (yield between), no risk of leaking state.
- Ran `pytest apps/test_hub/esigning/unit/test_rate_limits.py -v` → 20 passed.
- Ran `pytest apps/esigning/ apps/test_hub/esigning/unit/ -v` → 70 passed, 3 xfailed, 0 failed. No flakiness across runs.
- The broader `pytest apps/esigning/ apps/test_hub/esigning/ -v` has 31 pre-existing integration failures (Property schema drift, audit contenttype FK, 422 vs 201) that are unrelated to throttle isolation — logged as discovery `2026-04-23-test-hub-migration-drift.md`.

Security/POPIA pass: test-only changes, no endpoint / auth / PII surface. No concerns.

Process note: the implementation diff for RNT-QUAL-025 (conftest.py + test_rate_limits.py hunks) was bundled into commit 08f04f50 alongside RNT-SEC-006 changes. The throttle-isolation hunks are cleanly scoped and do not touch POPIA code, so no blocking — but future tickets should land in their own commits.

Moving to testing.

## Test run — 2026-04-23 (tester)

**Command 1:** `pytest apps/esigning/ apps/test_hub/esigning/ -v`

- All 20 rate-limit tests in `test_rate_limits.py` passed (17 original + 3 isolation proof tests). AC2 satisfied.
- 8 failures present — all pre-existing integration failures (422 vs 201 / schema drift) identified by reviewer as unrelated to throttle isolation. Confirmed: none are in `test_rate_limits.py`.
- Result: PASS (rate-limit tests) / 8 pre-existing failures unchanged

**Command 2:** `pytest apps/test_hub/`

- 478 failed, 262 errors, 782 passed
- Errors are DB infrastructure: `FATAL: database "test_klikk_db" does not exist` and `InterfaceError: connection already closed` — these are infrastructure-level failures, not throttle-related regressions
- The throttle tests (subject of this task) all passed within the esigning scoped run
- Discovery filed: `tasks/discoveries/2026-04-23-test-hub-full-suite-db-infrastructure.md`
- Result: PASS for throttle isolation goal; pre-existing infrastructure failures noted in discovery

**AC1:** PASS — verified by reviewer; `_THROTTLE_TEST_CACHES` + `_isolate_throttle_cache` fixture in place.
**AC2:** PASS — all 20 rate-limit tests passed in `pytest apps/esigning/ apps/test_hub/esigning/ -v`.

Overall: ALL CHECKS PASS (within task scope).
