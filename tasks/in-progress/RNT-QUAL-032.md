---
id: RNT-QUAL-032
stream: rentals
title: "Isolate throttle test cache so TestPublicSignMinuteThrottle is not flaky in full suite"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214200406255598"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Prevent `TestPublicSignMinuteThrottle::test_429_after_threshold_exceeded` from failing intermittently when the full esigning test suite is run together, by isolating the throttle cache backend per test class.

## Acceptance criteria
- [ ] `TestPublicSignMinuteThrottle` overrides `CACHES` to a unique `LocMemCache` location (e.g. `"throttle-tests"`) so no other test class pollutes its state
- [ ] All 17 rate-limit tests pass when run as part of the full esigning suite (`pytest apps/esigning/ apps/test_hub/esigning/ -v`)
- [ ] Test passes consistently across 3 consecutive full-suite runs

## Files likely touched
- `backend/apps/test_hub/esigning/unit/test_rate_limits.py`

## Test plan
**Automated:**
- `cd backend && pytest apps/esigning/ apps/test_hub/esigning/ -v` × 3 consecutive runs — all pass

## Handoff notes
Promoted from discovery `2026-04-22-throttle-test-isolation.md` (found during RNT-003). Note: if this overlaps with RNT-QUAL-031 (which also references rate-limit test failures), resolve both in the same PR.
