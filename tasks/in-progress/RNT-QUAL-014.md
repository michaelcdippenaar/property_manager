---
id: RNT-QUAL-014
stream: rentals
title: "Add select_related to esigning webhook handle_signing_complete to avoid N+1 queries"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214227879702322"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Prefetch related objects when fetching `ESigningSubmission` in `handle_signing_complete` so `_notify_staff` and `_email_signed_copy_to_signers` do not trigger additional per-call DB queries.

## Acceptance criteria
- [ ] `handle_signing_complete` (or its queryset fetch) adds `.select_related("lease__unit__property", "mandate__property")` before dispatching to helper functions
- [ ] Unit test confirms no extra queries are fired when processing a mandate completion event (use `assertNumQueries` or `django.test.utils.CaptureQueriesContext`)
- [ ] No functional regressions in esigning webhook flow

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
