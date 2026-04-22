---
discovered_by: rentals-implementer
discovered_during: RNT-SEC-002
discovered_at: 2026-04-22
priority_hint: P1
suggested_prefix: RNT-QUAL
---

## What I found

The `properties` app has two conflicting leaf-node migrations: `0024_unit_features` and
`0025_room_unit_amenities`. Running `pytest` on any DB-dependent test fails with
"Conflicting migrations detected; multiple leaf nodes in the migration graph".

## Why it matters

Any test that uses `db` or `django_db` fixtures cannot run until the conflict is resolved.
This blocks the full integration test suite from executing and will break CI when enabled.
The rate-limit integration tests added in RNT-SEC-002 (`test_429_after_threshold_exceeded`)
are currently erroring for this reason.

## Where I saw it

- `backend/apps/properties/migrations/0024_unit_features.py`
- `backend/apps/properties/migrations/0025_room_unit_amenities.py`
- Error message: `Conflicting migrations detected; multiple leaf nodes in the migration
  graph: (0024_unit_features, 0025_room_unit_amenities in properties).`

## Suggested acceptance criteria (rough)

- [ ] Run `python manage.py makemigrations --merge properties` to produce a merge migration
- [ ] Verify `pytest` can create the test database without errors
- [ ] Confirm all existing passing tests still pass after merge

## Why I didn't fix it in the current task

Out of scope for the rate-limit task. Modifying migration history carries schema-change
risk that deserves its own review and test pass.
