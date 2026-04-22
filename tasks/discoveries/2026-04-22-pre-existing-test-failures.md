---
discovered_by: rentals-tester
discovered_during: RNT-QUAL-011
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found
15 tests are failing in the suite that are unrelated to the QUAL-011 migration fix. They fall into 4 groups: (1) user registration role assertions expect `admin` but get `owner`/`agency_admin`; (2) rate-limit tests get 404 on `/api/v1/esigning/public-sign/.../sign/`; (3) municipal bill view tests fail due to mock/implementation mismatches (tool_use block expected, error message strings changed); (4) two tenant portal conversation tests and two property access unit tests fail due to stale mock setups.

## Why it matters
These failures mask real regressions — every future test run will have noise in the summary, making it harder to detect new breakages. The rate-limit tests (from RNT-SEC-002) and access tests are security-adjacent.

## Where I saw it
- `backend/apps/test_hub/accounts/integration/test_auth.py::RegisterViewTests::test_register_default_role_is_admin`
- `backend/apps/test_hub/accounts/integration/test_registration_account_type.py::RegisterAsAgencyTests::test_first_registered_user_is_admin`
- `backend/apps/test_hub/esigning/unit/test_rate_limits.py::TestPublicSignMinuteThrottle` (2 tests — URL 404)
- `backend/apps/test_hub/properties/integration/test_municipal_bill_view.py` (7 tests — tool_use block + error string mismatches)
- `backend/apps/test_hub/tenant_portal/integration/test_conversations.py` (2 tests — maintenance interaction)
- `backend/apps/test_hub/properties/unit/test_access.py::TestGetAccessiblePropertyIds` (2 tests — Mock not iterable)

## Suggested acceptance criteria (rough)
- [ ] All 15 tests pass or are intentionally skipped/xfailed with a comment
- [ ] No new failures introduced

## Why I didn't fix it in the current task
Out of scope — QUAL-011 is a migration-only fix. These failures predate QUAL-011 and are caused by application logic, URL routing, and test mock drift.
