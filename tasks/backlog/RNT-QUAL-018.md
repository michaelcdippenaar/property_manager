---
id: RNT-QUAL-018
stream: rentals
title: "Fix throttle test isolation so TestPublicSignMinuteThrottle is not flaky in full suite"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214237287752937"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Isolate `TestPublicSignMinuteThrottle` from shared throttle cache state so the test passes reliably when run as part of the full esigning suite.

## Acceptance criteria
- [ ] `TestPublicSignMinuteThrottle` class uses `@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "throttle-tests"}})` (or equivalent per-class isolation) so it is not contaminated by prior test classes
- [ ] All 17 rate-limit tests pass when run as part of the full esigning suite: `pytest apps/esigning/ apps/test_hub/esigning/ -v`
- [ ] No regressions in other throttle tests

## Files likely touched
- `backend/apps/test_hub/esigning/unit/test_rate_limits.py`

## Test plan
**Automated:**
- `cd backend && pytest apps/esigning/ apps/test_hub/esigning/ -v` — all 17 rate-limit tests pass, no flaky failure
- Run 5× to confirm no flakiness

## Handoff notes
Promoted from discovery: `2026-04-22-throttle-test-isolation.md` (RNT-003). Rate limiting on public signing endpoints is a security control; flaky test masks real regressions.
