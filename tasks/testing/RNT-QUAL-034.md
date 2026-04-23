---
id: RNT-QUAL-034
stream: rentals
title: "Mandate renew: inherit notes when caller omits field"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: testing
assigned_to: tester
depends_on: []
asana_gid: "1214218109691410"
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Fix `mandate_views.py` renew action so `notes` defaults to the source mandate's notes rather than an empty string, matching the behaviour of all other cloned fields.

## Acceptance criteria
- [x] `overrides.get("notes", "")` changed to `overrides.get("notes", mandate.notes)` in the renew action
- [x] Test added to `test_mandate_lifecycle.py` asserting notes are preserved when `notes` is omitted from the renew POST body
- [x] Existing tests remain green

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

2026-04-23 — One-line fix in `mandate_views.py` line 265: changed default from `""` to `mandate.notes`. Added two tests to `MandateRenewalTest`: `test_renewal_inherits_notes_when_omitted` (confirms notes propagate when POST body omits the field) and `test_renewal_notes_can_be_overridden` (confirms explicit override wins). All 26 tests pass.

2026-04-23 — Review passed. Checked: (1) mandate_views.py line 265 default changed from "" to mandate.notes — correct and consistent with all other cloned fields on lines 259-264; (2) notes field is TextField(blank=True) so empty-string source inherits cleanly; (3) two new tests cover omit-inherits and explicit-override branches; (4) no auth, POPIA, or raw-SQL issues — fix is inside an already-guarded action.
