---
id: RNT-QUAL-034
stream: rentals
title: "Mandate renew: inherit notes when caller omits field"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214218109691410"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Fix `mandate_views.py` renew action so `notes` defaults to the source mandate's notes rather than an empty string, matching the behaviour of all other cloned fields.

## Acceptance criteria
- [ ] `overrides.get("notes", "")` changed to `overrides.get("notes", mandate.notes)` in the renew action
- [ ] Test added to `test_mandate_lifecycle.py` asserting notes are preserved when `notes` is omitted from the renew POST body
- [ ] Existing tests remain green

## Files likely touched
- `backend/apps/properties/mandate_views.py` (line ~265)
- `backend/apps/properties/tests/test_mandate_lifecycle.py`

## Test plan
**Automated:**
- `cd backend && pytest apps/properties/tests/test_mandate_lifecycle.py`

**Manual:**
- POST renew to an existing mandate without supplying `notes` → confirm renewed mandate retains original notes

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-22 — Promoted from discovery `2026-04-22-mandate-renew-notes-not-inherited.md` found during RNT-QUAL-005 review.
