---
id: RNT-QUAL-023
stream: rentals
title: "Fix 15 pre-existing test failures across auth, rate-limit, municipal-bill, and access tests"
feature: ""
lifecycle_stage: null
priority: P2
effort: M
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214195382933912"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Resolve all 15 pre-existing test failures so the suite is green and future regressions are detectable without noise.

## Acceptance criteria
- [ ] `test_register_default_role_is_admin` and `test_first_registered_user_is_admin` pass (role assertion updated)
- [ ] `TestPublicSignMinuteThrottle` (2 tests) pass — URL routing fixed so endpoint returns 200/429 not 404
- [ ] 7 `test_municipal_bill_view.py` tests pass — mock/implementation aligned to current tool_use block format and error strings
- [ ] 2 `test_conversations.py` maintenance interaction tests pass
- [ ] 2 `TestGetAccessiblePropertyIds` tests pass — Mock is iterable
- [ ] No new failures introduced

## Files likely touched
- `backend/apps/test_hub/accounts/integration/test_auth.py`
- `backend/apps/test_hub/accounts/integration/test_registration_account_type.py`
- `backend/apps/test_hub/esigning/unit/test_rate_limits.py`
- `backend/apps/test_hub/properties/integration/test_municipal_bill_view.py`
- `backend/apps/test_hub/tenant_portal/integration/test_conversations.py`
- `backend/apps/test_hub/properties/unit/test_access.py`

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/ --tb=short -q` — confirm 0 failures

## Handoff notes
2026-04-22: Promoted from discovery `2026-04-22-pre-existing-test-failures.md` (found during RNT-QUAL-011 testing). All 15 failures predate QUAL-011; caused by application logic, URL routing, and mock drift.
