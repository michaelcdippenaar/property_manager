---
discovered_by: rentals-reviewer
discovered_during: RNT-SEC-013
discovered_at: 2026-04-22
priority_hint: P1
suggested_prefix: RNT
---

## What I found

Commit `eed71cb` (filed as the RNT-SEC-013 implementation) contains a large block of unrelated, unreviewed code that was never assigned a task and never went through the review pipeline: `backend/apps/leases/rha_check.py` (253 lines of RHA compliance logic), `backend/apps/leases/migrations/0018_add_rha_flags_to_lease.py` (a schema migration), `backend/apps/leases/tests/test_rha_gate.py` (315 lines of tests), `admin/src/views/leases/ESigningPanel.vue` (159 lines of UI changes), `content/product/rha-compliance.md`, and 20+ new backlog task files.

## Why it matters

A Django schema migration and new business-logic module shipped directly to main under a security-verification ticket, bypassing the normal implement → review → testing pipeline. The migration alters the lease model schema without any reviewer having checked it. If the RHA gate logic or migration has bugs, they are now live with no review trail.

## Where I saw it

- `backend/apps/leases/rha_check.py` (253 lines, new file)
- `backend/apps/leases/migrations/0018_add_rha_flags_to_lease.py` (new migration)
- `backend/apps/leases/tests/test_rha_gate.py` (315 lines, new file)
- `admin/src/views/leases/ESigningPanel.vue` (159-line addition)
- All in commit `eed71cb`

## Suggested acceptance criteria (rough)
- [ ] Assign a proper RNT task ID to the RHA compliance gate feature
- [ ] The RHA gate code (`rha_check.py`, migration, ESigningPanel changes) goes through the standard implement → review → testing pipeline
- [ ] Confirm migration `0018` does not break existing lease records or the occupancy signal
- [ ] Confirm the `rhaOverride` path in ESigningPanel.vue has appropriate role checks (staff/agency_admin only)

## Why I didn't fix it in the current task

Out of scope. RNT-SEC-013 is a gitleaks verification task. The RHA gate is a separate feature that should have its own task.
