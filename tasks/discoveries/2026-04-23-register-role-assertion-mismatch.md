---
discovered_by: rentals-tester
discovered_during: RNT-SEC-033
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found
Two integration tests in `apps/test_hub/accounts/` fail with a role mismatch: `test_register_default_role_is_admin` expects `"admin"` but gets `"owner"`, and `test_first_registered_user_is_admin` expects `User.Role.ADMIN` but gets `"agency_admin"`. Confirmed pre-existing — failures reproduce on the commit before RNT-SEC-033.

## Why it matters
The registration role-assignment logic or the test expectations are out of sync; either the production code assigns the wrong default role on first registration, or the tests no longer reflect the intended behaviour after a role model change.

## Where I saw it
- `backend/apps/test_hub/accounts/integration/test_auth.py::RegisterViewTests::test_register_default_role_is_admin`
- `backend/apps/test_hub/accounts/integration/test_registration_account_type.py::RegisterAsAgencyTests::test_first_registered_user_is_admin`

## Suggested acceptance criteria (rough)
- [ ] Determine correct intended role for first-registered user and align code or test assertions.
- [ ] Both tests pass in CI.

## Why I didn't fix it in the current task
Out of scope — RNT-SEC-033 only touches XFF IP extraction; these failures predate it and concern role assignment logic.
