---
id: RNT-QUAL-029
stream: rentals
title: "Add select_related to esigning webhook handle_signing_complete queryset"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214200629245826"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Eliminate N+1 DB queries in `handle_signing_complete` by adding `select_related("lease__unit__property", "mandate__property")` before dispatching to `_notify_staff` and `_email_signed_copy_to_signers`.

## Acceptance criteria
- [ ] `handle_signing_complete` (or its submission queryset fetch) adds `select_related("lease__unit__property", "mandate__property")`
- [ ] Unit test asserts no extra queries are fired when processing a mandate completion event (`assertNumQueries`)
- [ ] Existing webhook tests continue to pass

## Files likely touched
- `backend/apps/esigning/webhooks.py`
- `backend/apps/test_hub/esigning/` (new or updated test)

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/esigning/ -v`

## Handoff notes
Promoted from discovery `2026-04-22-esigning-webhook-helpers-missing-select-related.md` (found during RNT-001).
