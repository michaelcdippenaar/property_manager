---
id: RNT-QUAL-005
stream: rentals
title: "Mandate edge cases across all 4 mandate types"
feature: rental_mandate_esigning
lifecycle_stage: 1
priority: P1
effort: M
v1_phase: "1.0"
status: backlog
asana_gid: "1214177379658607"
assigned_to: null
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Sweep through all four mandate types — sole, shared, multiple, limited — and confirm every state transition, signature combo, and expiry path works correctly, not just the default.

## Acceptance criteria
- [ ] Cover: sole mandate (1 owner, 1 agent), shared mandate (>1 agent), multiple-agent (non-exclusive), limited-duration (start + end enforced)
- [ ] Multi-owner signatures: all owners must sign before active; if one rejects → mandate `rejected`, agent notified
- [ ] Mandate expiry: cron / beat task transitions expired mandates to `expired` and notifies agent 30, 14, 7 days before
- [ ] Mandate termination: written notice period respected; active-lease check (cannot terminate while lease is active on that property without override)
- [ ] Renewal flow: clone mandate, link to previous, retain audit chain
- [ ] All 4 types render correctly in both admin SPA and Quasar mobile

## Files likely touched
- `backend/apps/properties/mandate_models.py`
- `backend/apps/properties/mandate_views.py`
- `backend/apps/properties/tasks.py` (expiry beat)
- `admin/src/views/properties/MandateTab.vue`

## Test plan
**Automated:**
- `pytest backend/apps/properties/tests/test_mandate_lifecycle.py` — one test case per type × state

**Manual:**
- Create each of 4 types end-to-end in staging; confirm signatures, expiry reminders, and termination paths

## Handoff notes
