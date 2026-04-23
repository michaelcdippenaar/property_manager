---
discovered_by: rentals-tester
discovered_during: RNT-QUAL-025
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found
Running `pytest apps/test_hub/` (full suite) results in 478 failures and 262 errors due to database connection failures — `FATAL: database "test_klikk_db" does not exist` and `InterfaceError: connection already closed`. The esigning-scoped run (`pytest apps/esigning/ apps/test_hub/esigning/ -v`) also has 8 pre-existing integration failures (422 vs 201, Property schema drift) that were referenced in the RNT-QUAL-025 reviewer notes as discovery `2026-04-23-test-hub-migration-drift.md` — but that file was never written.

## Why it matters
The full `apps/test_hub/` test suite cannot run to completion; DB infrastructure failures mask any real regressions and make "no flaky failures" assertions impossible. The missing `2026-04-23-test-hub-migration-drift.md` discovery means the 8 esigning integration failures have no formal tracking.

## Where I saw it
- `pytest apps/test_hub/` → 478 failed, 262 errors, 782 passed
- Errors: `django.db.utils.OperationalError: connection to server at "localhost" (::1), port 5432 failed: FATAL:  database "test_klikk_db" does not exist`
- `apps/test_hub/esigning/integration/test_esigning.py` — 8 tests returning 422 instead of 201/502

## Suggested acceptance criteria (rough)
- [ ] `pytest apps/test_hub/` completes with 0 errors (DB infrastructure stable for full suite)
- [ ] Discovery `2026-04-23-test-hub-migration-drift.md` is formally filed covering the 8 esigning integration 422-vs-201 failures

## Why I didn't fix it in the current task
Out of scope — RNT-QUAL-025 only covers throttle test isolation. DB infrastructure and migration drift are separate concerns.
