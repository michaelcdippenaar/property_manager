---
id: RNT-SEC-007
stream: rentals
title: "RHA compliance gate: block lease finalize when rha_flags non-empty"
feature: ai_lease_generation
lifecycle_stage: 6
priority: P1
effort: S
v1_phase: "1.0"
status: backlog
asana_gid: "1214177462435910"
assigned_to: null
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Today `rha_flags` on a lease is advisory — the operator can finalise a lease with outstanding Rental Housing Act gaps. Make them blocking for v1 so every lease that leaves Klikk is RHA s5 compliant.

## Acceptance criteria
- [ ] `Lease.finalize()` / `send_for_signing` raises if `rha_flags.blocking.length > 0`
- [ ] Flags cover s5(3): deposit amount + interest-bearing account + pro-rata; s5(4)+(5) joint inspection in + out; mandatory terms (parties, premises, rent, escalation, duration, renewal, domicilium)
- [ ] Admin SPA: blocking flags shown as red banner on lease detail with "Resolve" CTA to exact field
- [ ] Non-blocking advisory flags stay as yellow warnings
- [ ] Operator override with reason (logged, requires `staff` or `agency_admin`) — never silently bypassed
- [ ] Documentation in `content/product/rha-compliance.md`

## Files likely touched
- `backend/apps/leases/models.py` (finalize method)
- `backend/apps/leases/rha_check.py` (new or existing)
- `backend/apps/leases/views.py`
- `admin/src/views/leases/LeaseDetail.vue` (flag banner + resolve flow)
- `content/product/rha-compliance.md` (new)

## Test plan
**Automated:**
- `pytest backend/apps/leases/tests/test_rha_gate.py` — cannot finalise with blocking flag; can finalise when cleared; override is audited

**Manual:**
- Draft a lease missing interest-bearing deposit → try send-for-signing → blocked with fix CTA
- Override with reason → audit log shows staff user + reason

## Handoff notes
