---
discovered_by: rentals-implementer
discovered_during: RNT-003
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found
`test_rate_limits.py::TestPublicSignMinuteThrottle::test_429_after_threshold_exceeded` fails when the full esigning test suite runs together due to shared throttle cache state bleeding in from other test classes. The test passes cleanly in isolation (17/17 in `test_rate_limits.py`).

## Why it matters
The flaky failure masks real throttle regressions — future changes to rate-limiting logic may break the throttle silently because CI noise causes reviewers to ignore the failure. Rate limiting on public signing endpoints is a security control (POPIA audit trail + brute-force protection).

## Where I saw it
- `backend/apps/test_hub/esigning/unit/test_rate_limits.py::TestPublicSignMinuteThrottle::test_429_after_threshold_exceeded`

## Suggested acceptance criteria (rough)
- [ ] Throttle test class isolates its cache backend using `@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "throttle-tests"}})` or equivalent per-class override so it is not contaminated by prior test classes
- [ ] All 17 rate-limit tests pass when run as part of the full esigning suite (`pytest apps/esigning/ apps/test_hub/esigning/ -v`)

## Why I didn't fix it in the current task
Out of scope for RNT-003 (resend link invalidation). The failure is pre-existing and caused by test infrastructure, not application logic.
