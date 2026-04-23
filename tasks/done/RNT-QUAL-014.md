---
id: RNT-QUAL-014
stream: rentals
title: "Add select_related to esigning webhook handle_signing_complete to avoid N+1 queries"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: done
assigned_to: null
depends_on: []
asana_gid: "1214227879702322"
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Prefetch related objects when fetching `ESigningSubmission` in `handle_signing_complete` so `_notify_staff` and `_email_signed_copy_to_signers` do not trigger additional per-call DB queries.

## Acceptance criteria
- [x] `handle_signing_complete` (or its queryset fetch) adds `.select_related("lease__unit__property", "mandate__property")` before dispatching to helper functions
- [x] Unit test confirms no extra queries are fired when processing a mandate completion event (use `assertNumQueries` or `django.test.utils.CaptureQueriesContext`)
- [x] No functional regressions in esigning webhook flow

## Files likely touched
- `backend/apps/esigning/webhooks.py`
- `backend/apps/test_hub/esigning/unit/test_webhooks.py` (or create new test file)

## Test plan
**Manual:**
- Trigger a mandate signing completion via test webhook; confirm no additional DB queries in Django debug toolbar / SQL log

**Automated:**
- `cd backend && pytest apps/esigning/ apps/test_hub/esigning/ -v` — all pass
- `assertNumQueries` test for mandate completion path

## Handoff notes
Promoted from discovery: `2026-04-22-esigning-webhook-helpers-missing-select-related.md` (RNT-001). Performance concern, no functional breakage today but will cause N+1 churn at scale.

**2026-04-23 — implementer**

The signing completion logic lives in `complete_native_signer()` in `backend/apps/esigning/services.py` (not in a `handle_signing_complete` function or `webhooks.py`). That function re-fetches the submission with `select_for_update().get(pk=...)` for concurrency safety, stripping any pre-loaded relations from `_resolve_link`. This is where the N+1 was occurring.

Fix applied: added `.select_related("lease__unit__property", "mandate__property", "created_by")` to the re-fetch. Had to use `select_for_update(of=("self",))` instead of plain `select_for_update()` — PostgreSQL rejects `FOR UPDATE` on the nullable side of outer joins that `select_related` emits for nullable FK paths (`lease` and `mandate` are both nullable on `ESigningSubmission`).

Two new `assertNumQueries(0)` tests added to `backend/apps/test_hub/esigning/integration/test_select_related_queries.py` in class `TestCompleteNativeSignerSelectRelated`, covering both the mandate path and the lease path. Full esigning suite: 245 passed, 3 xfailed, 0 failures.

**2026-04-23 — reviewer**

Review passed. Checked: AC1 — `.select_related("lease__unit__property", "mandate__property", "created_by")` is present at `services.py:736`; AC2 — two `assertNumQueries(0)` tests in `TestCompleteNativeSignerSelectRelated` cover mandate and lease paths, and the returned `submission` object is the re-fetched, lock-held instance so the 0-query assertions are valid; AC3 — no logic changes outside the queryset construction, no regression risk. `select_for_update(of=("self",))` usage is correct for nullable outer-join paths on PostgreSQL. Security pass: no new endpoints, no raw SQL, no PII logged, no auth surface changed.

**2026-04-23 — tester**

Test run: `cd backend && pytest apps/test_hub/esigning/ -v`
- Result: 245 passed, 3 xfailed, 0 failures (65.49s)
- All AC checks confirmed by test suite pass
- PASS
