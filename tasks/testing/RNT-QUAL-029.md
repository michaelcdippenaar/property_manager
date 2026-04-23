---
id: RNT-QUAL-029
stream: rentals
title: "Add select_related to esigning webhook handle_signing_complete queryset"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: testing
assigned_to: tester
depends_on: []
asana_gid: "1214200629245826"
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Eliminate N+1 DB queries in `handle_signing_complete` by adding `select_related("lease__unit__property", "mandate__property")` before dispatching to `_notify_staff` and `_email_signed_copy_to_signers`.

## Acceptance criteria
- [x] `handle_signing_complete` (or its submission queryset fetch) adds `select_related("lease__unit__property", "mandate__property")`
- [x] Unit test asserts no extra queries are fired when processing a mandate completion event (`assertNumQueries`)
- [x] Existing webhook tests continue to pass

## Files likely touched
- `backend/apps/esigning/webhooks.py`
- `backend/apps/test_hub/esigning/` (new or updated test)

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/esigning/ -v`

## Handoff notes
Promoted from discovery `2026-04-22-esigning-webhook-helpers-missing-select-related.md` (found during RNT-001).

2026-04-23 — implementer:
`handle_signing_complete` as a named function does not exist; the signing completion logic lives in `ESigningPublicSubmitSignatureView.post` in `apps/esigning/views.py`. The submission is loaded via `_resolve_link` in `ESigningPublicSignDetailView`.

The fix was applied to `_resolve_link`: the `ESigningPublicLink` queryset already had `select_related("submission__lease__unit__property")` but was missing `"submission__mandate__property"`. Added the missing path so both lease and mandate routes are covered in a single join.

New integration test file: `apps/test_hub/esigning/integration/test_select_related_queries.py` — three tests:
- `TestResolveLinkselectRelatedMandate::test_resolve_link_mandate_no_extra_query_for_property` — uses `assertNumQueries(0)` to confirm mandate.property access fires no extra SQL after `_resolve_link`.
- `TestResolveLinkselectRelatedMandate::test_resolve_link_mandate_property_name_correct` — smoke-check correct property name returned.
- `TestResolveLinkselectRelatedLease::test_resolve_link_lease_no_extra_query_for_unit_property` — regression guard that the existing lease path still fires zero extra queries.

Full esigning suite result: 243 passed, 3 xfailed.

2026-04-23 — reviewer:
Review passed. Checked: `select_related` in `_resolve_link` (`views.py` lines 490-494) now covers both `submission__lease__unit__property` and `submission__mandate__property`. Verified both paths are exercised by `_notify_staff` and `_email_signed_copy_to_signers` in `webhooks.py` (lines 187/190, 301/304, 377/380). Three `assertNumQueries(0)` integration tests added covering mandate and lease paths. Fix is at the correct location — `_resolve_link` is the single fetch point for the public signing flow; both webhook helpers receive the already-resolved submission object. No auth, POPIA, or security concerns.
