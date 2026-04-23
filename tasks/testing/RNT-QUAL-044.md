---
id: RNT-QUAL-044
stream: rentals
title: "Fix test-hub integration suite failures: Property schema drift, audit FK, and 422 serializer drift"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: testing
assigned_to: tester
depends_on: []
asana_gid: "1214237326400634"
created: 2026-04-23
updated: 2026-04-23T15:30:00
---

## Goal
Restore the esigning integration test suite to a green baseline by fixing the Property migration schema drift, `django_content_type` seeding failure, and 422/201 serializer drift that cause 31 failures and 8 errors when running `pytest apps/esigning/ apps/test_hub/esigning/`.

## Acceptance criteria
- [x] Generate and apply a Property migration for `house_rules` and `information_items` columns (or remove the fields if rolled back incorrectly)
- [x] Fix `django_content_type` seeding for the audit FK — likely a `post_migrate` signal or a test fixture flushing the contenttypes table
- [x] Triage the 422 vs 201 drift in `ESigningListCreateTests` / `SequentialSigningTests` — align serializer validation or update test expectations
- [x] `pytest apps/esigning/ apps/test_hub/esigning/ -v` runs green (0 failures, 0 errors)
- [x] `database "test_klikk_db" does not exist` error during mid-run resolved (fixture dropping test DB investigated)

## Files likely touched
- `backend/apps/properties/migrations/` (new migration for `house_rules`, `information_items`)
- `backend/apps/test_hub/esigning/integration/test_draft_and_documents.py`
- `backend/apps/test_hub/esigning/integration/test_endpoint_gating.py`
- `backend/apps/test_hub/esigning/integration/test_esigning.py`
- `backend/apps/test_hub/esigning/integration/test_esigning_full.py`
- Possibly `conftest.py` (fixture teardown causing test DB drop)

## Test plan
**Manual:**
- `cd backend && pytest apps/esigning/ apps/test_hub/esigning/ -v` — confirm 0 failures, 0 errors

**Automated:**
- CI backend test job passes green

## Handoff notes
2026-04-23: Promoted from discovery `2026-04-23-test-hub-migration-drift.md` (found during RNT-QUAL-025). 31 integration tests fail + 8 error due to Property schema drift (`house_rules`, `information_items` columns missing), `audit_auditevent` FK to missing `django_content_type` rows, and 422 vs 201 serializer drift. Unit tests (70) unaffected. Masks real regressions behind pre-existing failures — baseline must be green before further QA tickets can reliably signal.

2026-04-23 (implementer): Investigated actual failures. Root cause analysis:

1. **422 vs 201 drift** — All 8 failing tests were posting to `POST /api/v1/esigning/submissions/` and getting 422 back. The view has an RHA compliance gate (`assert_rha_ready()`) that runs `run_rha_checks(lease)` before creating the submission. The `create_lease` factory in `apps/test_hub/base/test_case.py` was not setting `escalation_clause`, `renewal_clause`, or `domicilium_address`, which all default to `""` on the model. Empty string is falsy, so the RHA checker raised blocking flags for `MISSING_ESCALATION_CLAUSE`, `MISSING_RENEWAL_CLAUSE`, and `MISSING_DOMICILIUM`. Fix: added sensible non-empty defaults for these three fields plus `notice_period_days=30` to `create_lease`.

2. **Property schema drift (`house_rules`, `information_items`)** — On inspection, `house_rules` has been in migrations since `0009` and `information_items` since `0023`. Both fields existed in the model and migrations. The task description was based on an earlier state; no migration needed.

3. **`django_content_type` seeding / audit FK** — The compliance tests in `test_compliance.py` all pass (6 pass). No `django_content_type` failure observed in this run.

4. **`database "test_klikk_db" does not exist`** — Not reproduced. Tests ran cleanly with `--reuse-db` not involved.

5. **Missing migrations for `audit` and `legal`** — `makemigrations --check` flagged two index-rename migrations. Generated and applied them: `audit/0003` (renames two indexes) and `legal/0002` (renames one index). `makemigrations --check` now reports "No changes detected".

**Result**: `pytest apps/esigning/ apps/test_hub/esigning/ -v` → 248 passed, 3 xfailed, 0 failures, 0 errors.

2026-04-23 (reviewer): Review passed. Checked: (1) `create_lease` factory defaults in `backend/apps/test_hub/base/test_case.py` lines 154–159 are sensible non-empty RHA placeholders (30-day notice, CPI escalation, mutual renewal, SA domicilium); `defaults.update(kwargs)` preserves per-test override, so RHA-specific tests can still exercise failure paths. (2) No production code change — diff is test helper + two migrations only. (3) Both migrations (`audit/0003`, `legal/0002`) are Django 5.2.13 auto-generated `RenameIndex` output — filenames and header confirm `makemigrations`, no hand edits. (4) No stray files in diff. No security/POPIA concerns (no endpoints, no logging). Handing off to tester.
