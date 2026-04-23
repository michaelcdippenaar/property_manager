---
id: RNT-QUAL-031
stream: rentals
title: "Fix 15 pre-existing test failures across accounts, esigning, municipal-bill, and access tests"
feature: ""
lifecycle_stage: null
priority: P2
effort: M
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214200629287352"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Restore all 15 pre-existing failing tests to green so the suite has no baseline noise and future regressions are clearly visible.

## Acceptance criteria
- [ ] `test_register_default_role_is_admin` and `test_first_registered_user_is_admin` pass (role assertion updated to match current model: `owner`/`agency_admin`)
- [ ] `TestPublicSignMinuteThrottle` (2 tests) pass — URL route corrected or test updated to current endpoint
- [ ] 7 `test_municipal_bill_view.py` tests pass (tool_use block format + error message strings aligned with current implementation)
- [ ] 2 `test_conversations.py` maintenance-interaction tests pass (mock setup updated)
- [ ] 2 `TestGetAccessiblePropertyIds` tests pass (`Mock not iterable` resolved)
- [ ] No new failures introduced
- [ ] `cd backend && pytest --tb=short -q` shows 0 failures in the affected test files

## Files likely touched
- `backend/apps/test_hub/accounts/integration/test_auth.py`
- `backend/apps/test_hub/accounts/integration/test_registration_account_type.py`
- `backend/apps/test_hub/esigning/unit/test_rate_limits.py`
- `backend/apps/test_hub/properties/integration/test_municipal_bill_view.py`
- `backend/apps/test_hub/tenant_portal/integration/test_conversations.py`
- `backend/apps/test_hub/properties/unit/test_access.py`

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/accounts/ apps/test_hub/esigning/unit/test_rate_limits.py apps/test_hub/properties/ apps/test_hub/tenant_portal/ -v`

## Handoff notes
Promoted from discovery `2026-04-22-pre-existing-test-failures.md` (found during RNT-QUAL-011). 15 failures across 4 groups: role assertions, rate-limit URL 404, municipal-bill mock drift, access mock not iterable.
