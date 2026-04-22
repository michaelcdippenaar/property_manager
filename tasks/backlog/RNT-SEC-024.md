---
id: RNT-SEC-024
stream: security
title: "Formally review and pipeline the RHA compliance gate shipped in commit eed71cb"
feature: "lease_management"
lifecycle_stage: 8
priority: P1
effort: M
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: [RNT-015]
asana_gid: "1214197140899873"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Put the RHA compliance gate code (`rha_check.py`, migration `0018`, `ESigningPanel.vue` changes) that shipped in commit `eed71cb` through the standard implement → review → testing pipeline, confirm the migration is safe, and verify the `rhaOverride` bypass path has correct role checks.

## Acceptance criteria
- [ ] `rha_check.py` (253 lines) reviewed for correctness, error handling, and edge cases
- [ ] Migration `0018_add_rha_flags_to_lease.py` reviewed: no destructive changes to existing lease records, indexes appropriate, reversible
- [ ] `ESigningPanel.vue` `rhaOverride` path confirmed to require `staff` or `agency_admin` role (backend + frontend check)
- [ ] `test_rha_gate.py` (315 lines) reviewed — coverage adequate, no false-negatives in the test suite
- [ ] Any issues found during review are fixed and re-reviewed before this task moves to testing
- [ ] After testing sign-off, a note is added to the git history tying `eed71cb` to this task ID as the formal review record

## Files likely touched
- `backend/apps/leases/rha_check.py`
- `backend/apps/leases/migrations/0018_add_rha_flags_to_lease.py`
- `backend/apps/leases/tests/test_rha_gate.py`
- `admin/src/views/leases/ESigningPanel.vue`

## Test plan
**Manual:**
- Attempt `rhaOverride` as a tenant-role user — must be rejected (403 or UI option hidden)
- Attempt `rhaOverride` as `agency_admin` — must succeed
- Run migration on a copy of production schema — verify zero data loss on existing lease rows

**Automated:**
- `cd backend && pytest apps/leases/tests/test_rha_gate.py -v`
- `cd backend && python manage.py migrate --run-syncdb` on a clean DB

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-22 — Promoted from discovery `2026-04-22-rha-gate-unreviewed-code-in-sec-commit.md` filed by the reviewer during RNT-SEC-013. The RHA gate (rha_check.py, migration 0018, ESigningPanel changes) was bundled into the RNT-SEC-013 commit without a task or review trail. This task is the formal remediation: a full review pass of everything in eed71cb that was not part of RNT-SEC-013's scope.
