---
discovered_by: rentals-reviewer
discovered_during: RNT-QUAL-005
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found
In `mandate_views.py` the `renew` action defaults `notes` to `""` when the caller omits the field, instead of inheriting `mandate.notes` like every other cloned field does.

## Why it matters
Agents who renew a mandate without explicitly re-supplying notes will silently lose the original mandate's notes (e.g. special conditions, internal comments). Inconsistent with all other override fields which fall back to the source mandate's value.

## Where I saw it
- `backend/apps/properties/mandate_views.py:265`
  `notes = overrides.get("notes", ""),`

## Suggested acceptance criteria (rough)
- [ ] Change the fallback to `overrides.get("notes", mandate.notes)` so notes are inherited on renewal unless explicitly overridden.
- [ ] Add a test case in `test_mandate_lifecycle.py` asserting notes are preserved when `notes` is omitted from the renew POST body.

## Why I didn't fix it in the current task
Pre-existing behaviour from the original implementation commit; the re-work diff only addressed serializer validation. Fixing it here would expand scope beyond the requested change.
