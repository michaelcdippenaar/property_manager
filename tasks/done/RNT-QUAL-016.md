---
id: RNT-QUAL-016
stream: rentals
title: "Fix 15 pre-existing test failures across auth, esigning, municipal-bill, and access tests"
feature: ""
lifecycle_stage: null
priority: P2
effort: M
v1_phase: "1.0"
status: done
assigned_to: null
depends_on: []
asana_gid: "1214229862791924"
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Restore the full test suite to a clean baseline by fixing the 15 pre-existing failures across four failure groups, eliminating CI noise that masks real regressions.

## Acceptance criteria
- [x] `test_register_default_role_is_admin` and `test_first_registered_user_is_admin` updated to reflect current role names (`owner`/`agency_admin`)
- [x] Rate-limit tests in `test_rate_limits.py::TestPublicSignMinuteThrottle` passing — URL routing fixed or tests updated to current URL pattern
- [x] All 7 `test_municipal_bill_view.py` failures fixed — mock/tool_use block and error string mismatches resolved
- [x] 2 tenant portal conversation test failures fixed — stale mock setups corrected
- [x] 2 `TestGetAccessiblePropertyIds` failures fixed — `Mock not iterable` setup corrected
- [x] `pytest` run exits with zero failures (or any intentionally skipped tests marked `xfail` with a comment)
- [x] No new failures introduced

## Files likely touched
- `backend/apps/test_hub/accounts/integration/test_auth.py`
- `backend/apps/test_hub/accounts/integration/test_registration_account_type.py`
- `backend/apps/test_hub/esigning/unit/test_rate_limits.py`
- `backend/apps/test_hub/properties/integration/test_municipal_bill_view.py`
- `backend/apps/test_hub/tenant_portal/integration/test_conversations.py`
- `backend/apps/test_hub/properties/unit/test_access.py`

## Test plan
**Automated:**
- `cd backend && pytest --tb=short -q` — zero failures
- Rate-limit tests: `pytest apps/test_hub/esigning/unit/test_rate_limits.py -v` — 17/17 pass

## Handoff notes
Promoted from discovery: `2026-04-22-pre-existing-test-failures.md` (RNT-QUAL-011). 15 pre-existing failures mask real regressions; two groups are security-adjacent (rate limits, access control).

(2026-04-23 rentals-pm) Dedup sweep: all 5 target files pass cleanly — 75 passed, 0 failures. All 15 originally-reported failures are resolved. Moved to done.
