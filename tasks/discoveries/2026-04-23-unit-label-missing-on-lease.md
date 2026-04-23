---
discovered_by: rentals-tester
discovered_during: RNT-SEC-024
discovered_at: 2026-04-23
priority_hint: P1
suggested_prefix: RNT-QUAL
---

## What I found
The push notifications signal in `backend/apps/notifications/push_signals.py:89` references `instance.unit_label`, but the Lease model has no such attribute. This causes an `AttributeError` that crashes any test creating a Lease with status change (e.g., when saving a new Lease). Introduced in commit 188e628d (RNT-QUAL-007).

## Why it matters
All Lease creation tests fail with `AttributeError: 'Lease' object has no attribute 'unit_label'`. Blocks RNT-SEC-024 test run (test_rha_gate.py cannot create test leases) and any other tests that create Leases. High priority regression.

## Where I saw it
- `backend/apps/notifications/push_signals.py:89` — `body=f"Your lease for {instance.unit_label}..."`
- Error occurs in `on_lease_status_change` signal handler
- Triggered by `pytest apps/leases/tests/test_rha_gate.py -v` (line 560, `_make_db_lease` calls `tc.create_lease()`)

## Suggested acceptance criteria
- [ ] Replace `instance.unit_label` with `str(instance.unit)` or equivalent (Unit.__str__ returns "Property Name — Unit 123")
- [ ] Verify all Lease creation tests pass
- [ ] Check for other references to non-existent `unit_label` attribute in the codebase

## Why I didn't fix it in the current task
Out of scope — I'm a test runner, not a developer. The bug is in RNT-QUAL-007 code, not in RNT-SEC-024. Blocks the test, so I'm filing it as a blocker discovery.
