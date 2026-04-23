---
id: RNT-QUAL-045
stream: rentals
title: "Test hub: fix full-suite DB infrastructure failures (test_klikk_db missing + connection leak)"
feature: ""
lifecycle_stage: null
priority: P2
effort: M
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214229920476903"
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Resolve the DB infrastructure failures that cause 478 failures and 262 errors when running `pytest apps/test_hub/` in full, so the suite reaches 0 infrastructure errors and any remaining failures reflect real regressions.

## Acceptance criteria
- [ ] `pytest apps/test_hub/` completes with 0 `OperationalError` / `InterfaceError` / "database does not exist" errors
- [ ] `test_klikk_db` test database is created reliably (Django test runner config, `DATABASES` settings, or `conftest.py` fixture reviewed and fixed)
- [ ] Connection-leak issue (`InterfaceError: connection already closed`) resolved — likely via `django.test.utils.setup_databases` ordering or `pytest-django` `@pytest.mark.django_db` scope misuse
- [ ] A formal discovery is filed (or directly tracked here) for the 8 esigning integration 422-vs-201 failures in `apps/test_hub/esigning/integration/test_esigning.py` — these are separately tracked as schema-drift failures and must not be conflated with infra errors
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
