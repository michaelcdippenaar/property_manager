---
id: RNT-QUAL-044
stream: rentals
title: "Fix test-hub integration suite failures: Property schema drift, audit FK, and 422 serializer drift"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: in-progress
assigned_to: implementer
depends_on: []
asana_gid: "1214237326400634"
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Restore the esigning integration test suite to a green baseline by fixing the Property migration schema drift, `django_content_type` seeding failure, and 422/201 serializer drift that cause 31 failures and 8 errors when running `pytest apps/esigning/ apps/test_hub/esigning/`.

## Acceptance criteria
- [ ] Generate and apply a Property migration for `house_rules` and `information_items` columns (or remove the fields if rolled back incorrectly)
- [ ] Fix `django_content_type` seeding for the audit FK — likely a `post_migrate` signal or a test fixture flushing the contenttypes table
- [ ] Triage the 422 vs 201 drift in `ESigningListCreateTests` / `SequentialSigningTests` — align serializer validation or update test expectations
- [ ] `pytest apps/esigning/ apps/test_hub/esigning/ -v` runs green (0 failures, 0 errors)
- [ ] `database "test_klikk_db" does not exist` error during mid-run resolved (fixture dropping test DB investigated)

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
