---
discovered_by: rentals-implementer
discovered_during: RNT-SEC-007
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT
---

## What I found

`Lease` has no dedicated model fields for escalation clause text, renewal clause text, or domicilium address. RHA s5(3) requires a lease to specify all three, but the compliance checker (`rha_check.py`) cannot enforce them because there is nothing to check against on the model.

## Why it matters

The AC for RNT-SEC-007 lists escalation, renewal, and domicilium as mandatory terms that must be flagged. The checker silently skips them. A lease can be sent for signing without any escalation or domicilium clause and no flag will fire.

## Where I saw it

- `backend/apps/leases/models.py` — `Lease` class has no `escalation_clause`, `renewal_clause`, or `domicilium_address` field
- `backend/apps/leases/rha_check.py:_check_mandatory_terms` — comment added explaining the intentional skip

## Suggested acceptance criteria (rough)

- [ ] Add `escalation_clause` (TextField, blank=True) to `Lease`
- [ ] Add `renewal_clause` (TextField, blank=True) to `Lease`
- [ ] Add `domicilium_address` (TextField, blank=True) to `Lease`
- [ ] Migration for all three fields
- [ ] `_check_mandatory_terms` flags each as blocking when empty
- [ ] Tests cover all three new blocking codes

## Why I didn't fix it in the current task

Adding three new model fields + migration + checker logic + tests is well beyond the scope of the S-effort RNT-SEC-007 task. Requires a PM decision on field granularity (free-text vs structured) and whether the lease builder AI should populate them.
