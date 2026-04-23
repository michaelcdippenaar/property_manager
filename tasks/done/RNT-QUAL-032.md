---
id: RNT-QUAL-032
stream: rentals
title: "Isolate throttle test cache so TestPublicSignMinuteThrottle is not flaky in full suite"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: done
assigned_to: null
depends_on: []
asana_gid: "1214200406255598"
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Prevent `TestPublicSignMinuteThrottle::test_429_after_threshold_exceeded` from failing intermittently when the full esigning test suite is run together, by isolating the throttle cache backend per test class.

## Acceptance criteria
- [x] `TestPublicSignMinuteThrottle` overrides `CACHES` to a unique `LocMemCache` location (e.g. `"throttle-tests"`) so no other test class pollutes its state
- [x] All 17 rate-limit tests pass when run as part of the full esigning suite (`pytest apps/esigning/ apps/test_hub/esigning/ -v`)
- [x] Test passes consistently across 3 consecutive full-suite runs

## Files likely touched
- `backend/apps/test_hub/esigning/unit/test_rate_limits.py`

## Test plan
**Automated:**
- `cd backend && pytest apps/esigning/ apps/test_hub/esigning/ -v` × 3 consecutive runs — all pass

## Handoff notes
Promoted from discovery `2026-04-22-throttle-test-isolation.md` (found during RNT-003). Note: if this overlaps with RNT-QUAL-031 (which also references rate-limit test failures), resolve both in the same PR.

### 2026-04-23 — implementer

**Root cause (deeper than "cache pollution"):**

Two separate issues were found and fixed:

1. **Cache isolation** (as described): Added `_isolate_throttle_cache(self, settings)` autouse fixture inside `TestPublicSignMinuteThrottle` that sets `settings.CACHES` to a uniquely-named `LocMemCache("throttle-tests")` via pytest-django's `settings` fixture. Django's `setting_changed` signal automatically calls `close_caches()` and resets the cache handler thread-local, so `django.core.cache.cache` points to the isolated backend for the duration of each test. Note: `@override_settings` as a CLASS decorator is not supported for non-`SimpleTestCase` pytest classes (Django raises `ValueError`) — the autouse fixture pattern was used instead.

2. **`SimpleRateThrottle.THROTTLE_RATES` class variable frozen at import time**: DRF sets `THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES` at module import time. Django's `setting_changed` signal only calls `api_settings.reload()` — it does NOT update the class variable. When `rest_framework.throttling` is first imported by an earlier test (outside any `@override_settings` context), `THROTTLE_RATES` gets the production base dict (`10/min`). The `@override_settings(REST_FRAMEWORK=...)` on individual methods updates `api_settings.DEFAULT_THROTTLE_RATES` but leaves `THROTTLE_RATES` frozen. With `10/min`, 4 requests don't trigger a 429. The fixture patches `SimpleRateThrottle.THROTTLE_RATES` directly with the tight test rates and restores it on teardown.

**Results:** All 17 rate-limit tests pass in 3 consecutive full-suite runs (`apps/esigning/ apps/test_hub/esigning/`).

**Discovery logged:** Found 8 pre-existing failures in `test_esigning.py`/`test_esigning_full.py` (422 instead of 201 on submission create). Filed as `tasks/discoveries/2026-04-23-esigning-integration-test-422.md`.

### 2026-04-23 — reviewer

**Review passed.**

Checked:
1. AC1 — `_THROTTLE_TEST_CACHES` with `LOCATION: "throttle-tests"` is defined at module level and applied via `settings.CACHES = _THROTTLE_TEST_CACHES` inside the autouse fixture. Satisfied.
2. AC2/AC3 — Implementer reports 17/17 pass across 3 consecutive runs. Tester to verify independently.
3. Fixture correctness — `_isolate_throttle_cache` is `autouse=True` inside `TestPublicSignMinuteThrottle` only, so no blast radius on other classes. Teardown correctly restores `SimpleRateThrottle.THROTTLE_RATES` via explicit `yield` + reassignment. pytest-django `settings` fixture handles `CACHES` restore automatically via `setting_changed`.
4. Root conftest interaction — `_reset_drf_throttle_cache` (root conftest, function scope) runs before the class fixture sets `CACHES`, so it clears the old default cache harmlessly; post-yield it clears the isolated cache and then `CACHES` is restored. Order is safe.
5. No conflicts with `backend/apps/test_hub/esigning/conftest.py` — that file has no cache or throttle fixtures.
6. Discovery `tasks/discoveries/2026-04-23-esigning-integration-test-422.md` is correctly filed and out of scope for this task.
7. Security/POPIA — test-only change, no production code touched, no auth/PII concerns.

### Test run 2026-04-23 — tester

**Automated:** `pytest apps/esigning/ apps/test_hub/esigning/ -v` × 3 consecutive runs

- Run 1: 17/17 rate-limit tests PASS (229 passed total, 8 pre-existing 422 failures in test_esigning.py/test_esigning_full.py — already filed as discovery `tasks/discoveries/2026-04-23-esigning-integration-test-422.md`, out of scope)
- Run 2: 17/17 rate-limit tests PASS (same 8 pre-existing failures)
- Run 3: 17/17 rate-limit tests PASS (same 8 pre-existing failures)

AC1 — `_THROTTLE_TEST_CACHES` with `LOCATION: "throttle-tests"` confirmed in test file. PASS
AC2 — All 17 rate-limit tests pass across full suite. PASS
AC3 — Consistent across 3 consecutive runs. PASS

**All checks pass.**
