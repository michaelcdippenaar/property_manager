---
id: RNT-QUAL-048
stream: rentals
title: "RHA compliance gate: implement hard-block on missing deposit/inspection fields (v1.1)"
feature: ""
lifecycle_stage: null
priority: P2
effort: M
v1_phase: "1.1"
status: backlog
assigned_to: null
depends_on: [DEC-024]
asana_gid: "1214246263090626"
created: 2026-04-24
updated: 2026-04-24
---

## Goal
Implement a hard-block on lease activation when mandatory RHA fields (deposit amount, inspection-in date, inspection signed-off) are absent — preventing non-compliant lease activation without agent acknowledgement bypass.

## Context
DEC-024 (answered 2026-04-24) chose soft-warn for v1.0 launch. The soft-warn banner + "acknowledged" tick is the v1.0 behaviour. This task implements the stricter v1.1 hard-block once the first-client dry-run has informed edge-case handling.

## Acceptance criteria
- [ ] Lease activation API endpoint returns 400 (not 200) when any of the following are absent: deposit amount, inspection-in date, inspection signed-off field
- [ ] Soft-warn banner from v1.0 is replaced (or upgraded) to a hard-error that cannot be dismissed without correcting the data
- [ ] Agent UI clearly states which specific fields are missing and how to fill them
- [ ] Existing test suite for lease activation updated — tests for missing-field activation must now expect 400
- [ ] Migration (if RHA fields are new DB columns) included
- [ ] POPIA pass: no new PII exposure

## Files likely touched
- `backend/apps/leases/views.py` (activation endpoint)
- `backend/apps/leases/serializers.py` (validation)
- `backend/apps/leases/models.py` (if new fields required)
- `admin/src/views/leases/LeaseActivationFlow.vue` (UI)
- `backend/apps/leases/tests/test_activation.py`

## Test plan
**Automated:**
- `cd backend && pytest apps/leases/tests/test_activation.py -v`

**Manual:**
- Attempt to activate lease with missing deposit → 400 returned, clear error message shown
- Fill all required fields → activation succeeds

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-24 — rentals-pm: Created as v1.1 follow-up to DEC-024. Do not implement in v1.0. Soft-warn with "acknowledged" tick is the v1.0 behaviour.
