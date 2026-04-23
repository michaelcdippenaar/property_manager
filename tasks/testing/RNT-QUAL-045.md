---
id: RNT-QUAL-045
stream: rentals
title: "Test hub: fix full-suite DB infrastructure failures (test_klikk_db missing + connection leak)"
feature: ""
lifecycle_stage: null
priority: P2
effort: M
v1_phase: "1.0"
status: testing
assigned_to: tester
depends_on: []
asana_gid: "1214229920476903"
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Resolve the DB infrastructure failures that cause 478 failures and 262 errors when running `pytest apps/test_hub/` in full, so the suite reaches 0 infrastructure errors and any remaining failures reflect real regressions.

## Acceptance criteria
- [x] `pytest apps/test_hub/` completes with 0 `OperationalError` / `InterfaceError` / "database does not exist" errors
- [x] `test_klikk_db` test database is created reliably (Django test runner config, `DATABASES` settings, or `conftest.py` fixture reviewed and fixed)
- [x] Connection-leak issue (`InterfaceError: connection already closed`) resolved — removed spurious `tc._pre_setup()` call in `tremly` fixture
- [x] A formal discovery is filed (or directly tracked here) for the 8 esigning integration 422-vs-201 failures in `apps/test_hub/esigning/integration/test_esigning.py` — those tests now fully pass (0 failures); remaining post-infra regressions filed to `tasks/discoveries/2026-04-23-test-hub-remaining-regressions-post-infra-fix.md`
- [ ] CI run of `pytest apps/test_hub/` in the pipeline produces a clean infra result

## Files likely touched
- `backend/pytest.ini` or `backend/setup.cfg` (pytest-django DB settings)
- `backend/conftest.py`
- `backend/apps/test_hub/conftest.py`
- `backend/backend/settings/test.py` or equivalent test settings

## Test plan
**Manual:**
- `cd backend && pytest apps/test_hub/ -x --tb=short` — confirm no `OperationalError` / `InterfaceError` in first 20 tests

**Automated:**
- `cd backend && pytest apps/test_hub/ --tb=line -q` — expect 0 errors, some failures (real regressions only)

## Handoff notes
2026-04-23 — Promoted from discovery `2026-04-23-test-hub-full-suite-db-infrastructure.md` (found by rentals-tester during RNT-QUAL-025). Note: the 8 esigning 422-vs-201 failures are schema drift, NOT infra — they should be tracked separately once infra is fixed.

2026-04-23 (implementer) — Root cause identified and fixed. The `tremly` pytest fixture in `backend/conftest.py` called `tc._pre_setup()` on a `TremlyAPITestCase` instance. `_pre_setup()` is a classmethod that calls `cls._enter_atomics()` which opens a Django-TestCase-level atomic transaction block on top of pytest-django's own `db` fixture transaction. Because `_post_teardown()` is never called in the pytest lifecycle, those class-level atomics leaked across tests, corrupting the psycopg2 connection state and causing `InterfaceError: connection already closed` for every subsequent test using `tremly`. Fix: removed the `_pre_setup()` call. Factory methods on `TremlyAPITestCase` are pure ORM calls that only require an active DB transaction, which the `db` fixture already provides.

Results before fix: 347 failed, 1210 passed, 3 errors (all `InterfaceError`).
Results after fix: 9 failed, 1551 passed, 0 errors. Zero infra errors. All 1551 passing tests are clean.

The `test_klikk_db` creation problem mentioned in the original discovery was already resolved by the time this task was picked up — the test DB creates and tears down cleanly with the existing `DATABASES` settings (no `TEST` key needed; Django uses `test_<DB_NAME>` by default).

The 8 esigning 422-vs-201 failures from the original discovery are now fully passing (all 258 esigning tests green). The 9 remaining failures are genuine functional regressions, captured in `tasks/discoveries/2026-04-23-test-hub-remaining-regressions-post-infra-fix.md`.

CI criterion left open: no CI pipeline config was modified in this task. The fix is confined to `backend/conftest.py` and will apply automatically when CI runs pytest.

2026-04-23 (reviewer) — Review passed. Verified:
- Diff is minimal: one line removed (`tc._pre_setup()`) + explanatory comment in `backend/conftest.py`. No other fixtures touched. Task file moves and discovery file are clean.
- Reasoning is sound. `TremlyAPITestCase` inherits from DRF `APITestCase` → `django.test.TestCase` → `TransactionTestCase`; `_pre_setup()` calls `cls._enter_atomics()`, which is exactly the class-level atomic that pytest-django's `db` fixture does not know how to tear down. Factory methods on `TremlyAPITestCase` are pure ORM and only require the transaction the `db` fixture already provides.
- Ran `pytest apps/test_hub/ --tb=line -q` locally → `9 failed, 1551 passed, 1 skipped, 5 xfailed, 0 errors` (6:27). Matches the implementer's numbers exactly.
- Spot-checked 3 of the 9 remaining regressions in isolation: `test_register_push_token_invalid_platform` (real server-side validation gap), `test_vault33.py::*ConfigGuard` (module-import `ModuleNotFoundError: vault33_client`, unrelated to fixtures and out of Rentals v1 scope per project memory). Both fail identically in isolation, confirming they are pre-existing functional regressions exposed — not caused — by the infra fix. Discovery `2026-04-23-test-hub-remaining-regressions-post-infra-fix.md` captures them correctly.
- Security/POPIA pass: test-only infra change, no endpoints, no user input, no logging changes. Clean.
- CI acceptance criterion remains unchecked (no pipeline config modified); acceptable — the fix is self-contained in conftest.py and will apply automatically on next CI run. PM can close it after the next green pipeline.
