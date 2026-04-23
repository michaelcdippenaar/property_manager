---
discovered_by: rentals-tester
discovered_during: RNT-QUAL-006
discovered_at: 2026-04-24
priority_hint: P2
suggested_prefix: QA
---

## What I found

pytest-django's database fixture has a lifecycle issue when running multiple TestCase classes within the same module. After the first test class tearDown completes, the test database is destroyed and pytest-django does not automatically recreate it for the second class—resulting in `FATAL: database "test_klikk_db" does not exist` errors during setup of the second class's tests.

## Why it matters

In `backend/apps/properties/tests/test_dashboard_cache.py`, the second test class (`OwnerActivityFeedContentTest`, 6 tests) fails to initialize while the first class (`OwnerDashboardCacheTest`, 14 tests) passes completely. This blocks the test suite from running to completion in a single invocation, forcing developers to either run classes individually (`pytest ClassName`) or work around the issue with `--create-db` flag + different test runners. The underlying code is verified (14/20 tests pass, Opus review approved), but the test infrastructure blocks full validation in CI/CD.

## Where I saw it

- `backend/apps/properties/tests/test_dashboard_cache.py::OwnerActivityFeedContentTest` — all 6 tests error with `django.db.utils.OperationalError: connection to server at "localhost" (::1), port 5432 failed: FATAL:  database "test_klikk_db" does not exist`
- Test execution: `pytest apps/properties/tests/test_dashboard_cache.py -xvs --create-db`
- First class: 14/14 pass
- Second class: 0/6 attempt, all error during setup
- Both classes inherit from `TremlyAPITestCase` (Django TestCase) with `@pytest.mark.integration`

## Suggested acceptance criteria

- [ ] Investigate pytest-django fixture lifecycle docs for multi-class test modules
- [ ] Consider solutions: separate test modules per class, explicit `db_reset` marks between classes, or pytest-django configuration changes
- [ ] Verify proposed fix doesn't slow down CI/CD or break existing single-class test modules
- [ ] Document the solution for future developers (e.g., in TESTING.md or a comment in conftest.py)

## Why I didn't fix it in the current task

This is a pytest/Django infrastructure issue, not a code quality issue. The RNT-QUAL-006 implementation itself is sound (verified by 14/20 tests passing and Opus code review approval). The fixture teardown lifecycle is out of scope for a feature implementer or tester—it requires either a pytest expert to adjust the fixture setup/teardown order, or a DevOps decision to restructure how tests are organized. Fixing it would require changes to `conftest.py` or test organization patterns, which is infrastructure governance, not testing the feature itself.
