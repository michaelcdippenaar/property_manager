---
discovered_by: rentals-reviewer
discovered_during: RNT-QUAL-025
discovered_at: 2026-04-23
priority_hint: P1
suggested_prefix: RNT-QUAL
---

## What I found
When running `pytest apps/esigning/ apps/test_hub/esigning/ -v` per the RNT-QUAL-025 test plan, 31 integration tests fail and 8 error with migration/schema drift: `column "house_rules" of relation "properties_property" does not exist`, `column "information_items" …`, and `audit_auditevent` FK violations pointing at missing `django_content_type` rows. One test also shows `database "test_klikk_db" does not exist` mid-run, which suggests a fixture is dropping the test DB. Unit tests (70 passing) are unaffected; only integration tests touching Property / AuditEvent break.

## Why it matters
- Masks real regressions behind a wall of pre-existing failures. A reviewer/tester cannot tell whether a new change broke something because the baseline is already red.
- The "run the full esigning suite" acceptance criterion in RNT-QUAL-025 could not be cleanly satisfied — I had to verify the 20 rate-limit tests pass on their own. Future tickets that claim "full suite green" will hit the same wall.
- `house_rules` / `information_items` are recent fields on `properties.Property` — a migration either hasn't been generated or isn't being applied to the test DB.

## Where I saw it
- `backend/apps/test_hub/esigning/integration/test_draft_and_documents.py` — all SupportingDocumentUpload tests failing on Property schema
- `backend/apps/test_hub/esigning/integration/test_endpoint_gating.py` — `audit_auditevent` FK to `django_content_type`
- `backend/apps/test_hub/esigning/integration/test_esigning.py` — mix of schema + 422 vs 201 (contract drift?)
- `backend/apps/test_hub/esigning/integration/test_esigning_full.py` — 422 vs 201

## Suggested acceptance criteria (rough)
- [ ] Generate + apply Property migration for `house_rules` and `information_items` columns (or remove the fields if they were rolled back incorrectly)
- [ ] Fix the `django_content_type` seeding for the audit FK — likely a `post_migrate` signal or a test fixture that's flushing the contenttypes table
- [ ] Triage the 422 vs 201 drift in ESigningListCreateTests / SequentialSigningTests (may be serializer validation change)
- [ ] `pytest apps/esigning/ apps/test_hub/esigning/` runs green

## Why I didn't fix it in the current task
RNT-QUAL-025 is specifically about throttle-test cache isolation. The 20 rate-limit tests pass clean. Fixing Property schema drift + audit FK + serializer 422s is a separate P1 sweep that needs a QA owner.
