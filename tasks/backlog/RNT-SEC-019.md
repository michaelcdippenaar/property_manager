---
id: RNT-SEC-019
stream: rentals
title: "Restrict GotenbergHealthView to admin-only to prevent infrastructure disclosure"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214195240490293"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Restrict `GotenbergHealthView` to admin users only (or strip version/engine fields) so authenticated agents cannot enumerate internal infrastructure details via the health endpoint.

## Acceptance criteria
- [ ] `GotenbergHealthView` restricted to `IsAdminUser` only (not all agents), OR response strips engine name, version strings, and internal service structure before returning to client
- [ ] Test asserting that an agent (non-admin) user receives 403 on `GET /api/v1/esigning/gotenberg/health/`

## Files likely touched
- `backend/apps/esigning/views.py` (`GotenbergHealthView`, ~line 387)
- `backend/apps/esigning/urls.py` (~line 45)
- Relevant test file in `backend/apps/test_hub/esigning/`

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/esigning/ -k "gotenberg_health" -v`
- Agent role user: assert 403
- Admin user: assert 200

## Handoff notes
2026-04-22: Promoted from discovery `2026-04-22-gotenberg-health-endpoint-recon.md` (found during RNT-SEC-004 review). Not a direct exploit but useful for targeted attack reconnaissance.
