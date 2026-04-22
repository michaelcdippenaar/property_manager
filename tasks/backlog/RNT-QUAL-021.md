---
id: RNT-QUAL-021
stream: rentals
title: "Add select_related to esigning webhook handle_signing_complete to prevent N+1"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214194921052921"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Add `select_related("lease__unit__property", "mandate__property")` to the queryset fetch inside `handle_signing_complete` so `_notify_staff` and `_email_signed_copy_to_signers` do not trigger N+1 DB queries on mandate completions.

## Acceptance criteria
- [ ] `handle_signing_complete` (or its submission queryset fetch) adds `select_related("lease__unit__property", "mandate__property")`
- [ ] Unit test confirms no extra queries fired when processing a mandate completion event (use `assertNumQueries`)

## Files likely touched
- `backend/apps/esigning/webhooks.py` (`handle_signing_complete`, ~line where submission is fetched)

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/esigning/ -k "signing_complete" -v`
- Add `assertNumQueries` test for mandate completion path

## Handoff notes
2026-04-22: Promoted from discovery `2026-04-22-esigning-webhook-helpers-missing-select-related.md` (found during RNT-001 review). No functional breakage — performance/query efficiency concern.
