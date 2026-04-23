---
id: RNT-QUAL-041
stream: rentals
title: "Fix register role assertion mismatch — align default role assignment with test expectations"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: done
assigned_to: done
depends_on: []
asana_gid: "1214229833102884"
created: 2026-04-23
updated: 2026-04-23
---

## Goal

Resolve the two failing registration role tests by aligning the production role-assignment logic with the intended behaviour (or updating stale test assertions), so that the default role on first registration is unambiguous and both tests pass.

## Acceptance criteria
- [x] Determine the intended default role for a first-registered user (decision: `admin`, `owner`, or `agency_admin`)
- [x] Either update `RegisterView` / role-assignment signal to assign the correct role, or update the test assertions to reflect the current intentional behaviour — with a comment explaining the choice
- [x] `RegisterViewTests::test_register_default_role_is_admin` passes (currently gets `"owner"`, expects `"admin"`)
- [x] `RegisterAsAgencyTests::test_first_registered_user_is_admin` passes (currently gets `"agency_admin"`, expects `User.Role.ADMIN`)
- [x] No regressions in remaining accounts/auth test suite

## Files likely touched
- `backend/apps/accounts/views.py` (RegisterView or equivalent)
- `backend/apps/accounts/signals.py` (if role assignment is signal-driven)
- `backend/apps/test_hub/accounts/integration/test_auth.py`
- `backend/apps/test_hub/accounts/integration/test_registration_account_type.py`

## Test plan
**Manual:**
- Register a new user via `POST /api/v1/auth/register/` — inspect the returned or DB role value

**Automated:**
- `cd backend && pytest apps/test_hub/accounts/integration/ -v` — both failing tests must be green with no new failures

## Handoff notes
(2026-04-23 rentals-pm) Promoted from discovery `2026-04-23-register-role-assertion-mismatch.md`. Failures confirmed pre-existing before RNT-SEC-033. Implementer must decide whether the code or the tests are wrong — this may warrant a DEC-NNN if the intended role is unclear.

(2026-04-23 implementer) No code changes required. Investigation showed both tests are already passing. The failures described in the task description were stale at the time of implementation.

Decision established: the role-assignment logic in `backend/apps/accounts/serializers.py` line 71 already implements the intended behaviour: `account_type=agency` → `agency_admin`, `account_type=individual` (default) → `owner`. Both named tests confirm this:
- `RegisterViewTests::test_register_default_role_is_admin` posts `account_type=agency` and asserts `role == "agency_admin"` — PASSES.
- `RegisterAsAgencyTests::test_first_registered_user_is_admin` posts `account_type=agency` and asserts `role == User.Role.AGENCY_ADMIN` — PASSES.

Note: the task description said `test_register_default_role_is_admin` "expects admin" — but the test body actually asserts `agency_admin`. The task description was itself stale/incorrect; the tests were already correct and aligned with the code.

Full run: `pytest apps/test_hub/accounts/integration/ -v` → 203 passed, 0 failed. No regressions.

(2026-04-23 reviewer) Review passed — closed as obsolete. Reviewer independently ran both named tests: 2 passed, 0 failed (pytest -k "test_register_default_role_is_admin or test_first_registered_user_is_admin"). No production code was changed; task description contained stale failure info. All ACs satisfied by pre-existing code. Moving directly to done — no tester action required.
