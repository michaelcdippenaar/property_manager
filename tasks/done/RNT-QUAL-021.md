---
id: RNT-QUAL-021
stream: rentals
title: "Add select_related to esigning webhook handle_signing_complete to prevent N+1"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: done
assigned_to: null
depends_on: []
asana_gid: "1214194921052921"
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Add `select_related("lease__unit__property", "mandate__property")` to the queryset fetch inside `handle_signing_complete` so `_notify_staff` and `_email_signed_copy_to_signers` do not trigger N+1 DB queries on mandate completions.

## Acceptance criteria
- [x] `handle_signing_complete` (or its submission queryset fetch) adds `select_related("lease__unit__property", "mandate__property")`
- [x] Unit test confirms no extra queries fired when processing a mandate completion event (use `assertNumQueries`)

## Files likely touched
- `backend/apps/esigning/webhooks.py` (`handle_signing_complete`, ~line where submission is fetched)

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/esigning/ -k "signing_complete" -v`
- Add `assertNumQueries` test for mandate completion path

## Handoff notes
2026-04-22: Promoted from discovery `2026-04-22-esigning-webhook-helpers-missing-select-related.md` (found during RNT-001 review). No functional breakage — performance/query efficiency concern.

2026-04-23: Implementation verified complete. The task referenced a non-existent `handle_signing_complete` function; the actual signing completion handler is `services.complete_native_signer()` which is called by `ESigningPublicSubmitSignatureView` in `views.py`. The `select_related("lease__unit__property", "mandate__property", "created_by")` with `select_for_update(of=("self",))` was already present in `backend/apps/esigning/services.py` at line 734–738, preventing N+1 queries for both `_notify_staff` and `_email_signed_copy_to_signers`. The `assertNumQueries(0)` tests were already written in `backend/apps/test_hub/esigning/integration/test_select_related_queries.py` covering mandate path (`TestCompleteNativeSignerSelectRelated`), lease path, and `_resolve_link` paths. Test run showed env-level DB issues (test DB dropped mid-run) for the `TestCompleteNativeSignerSelectRelated` class but the `TestResolveLinkselectRelatedLease` test passed cleanly; the failures were infrastructure-only (`relation "accounts_user" does not exist` / DB dropped), not code failures. No code changes were needed — this task was already implemented as part of adjacent work.

2026-04-23 Review passed: Verified (1) select_related chain `lease__unit__property, mandate__property, created_by` in services.py:736 covers every field touched by `_notify_staff` (webhooks.py:292 — reads `submission.created_by.email`, `submission.lease.unit.property.name`, `submission.lease.unit.unit_number`, `submission.mandate.property.name`) and `_email_signed_copy_to_signers` (webhooks.py:349 — reads `submission.lease.unit.property.name`, `submission.lease.unit.unit_number`, `submission.mandate.property.name`). (2) Grep confirms no `handle_signing_complete` exists anywhere in backend — the real completion path is `complete_native_signer` called from `views.py:678` (both `_notify_staff` branches and `_email_signed_copy_to_signers` fire off the same pre-joined submission returned by that function). (3) Ran `pytest apps/test_hub/esigning/integration/test_select_related_queries.py -v` → **5 passed** in 20.56s, including `TestCompleteNativeSignerSelectRelated` mandate + lease `assertNumQueries(0)` assertions. No regressions, no POPIA concerns (no new endpoints, no new logging of PII).

### Test run 2026-04-23 (rentals-tester)
- `pytest apps/test_hub/esigning/integration/test_select_related_queries.py -v` → **5/5 PASSED**
  - TestResolveLinkselectRelatedMandate::test_resolve_link_mandate_no_extra_query_for_property PASSED
  - TestResolveLinkselectRelatedMandate::test_resolve_link_mandate_property_name_correct PASSED
  - TestResolveLinkselectRelatedLease::test_resolve_link_lease_no_extra_query_for_unit_property PASSED
  - TestCompleteNativeSignerSelectRelated::test_complete_native_signer_lease_no_extra_query_for_property PASSED
  - TestCompleteNativeSignerSelectRelated::test_complete_native_signer_mandate_no_extra_query_for_property PASSED
- `python3 manage.py check` → **System check identified no issues (0 silenced)**
- Decision: all checks pass → done
