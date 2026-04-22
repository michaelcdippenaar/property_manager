---
id: RNT-SEC-020
stream: rentals
title: "Restrict maintenance dispatch actions to agent/admin role (auth bypass fix)"
feature: ""
lifecycle_stage: null
priority: P1
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214195381558558"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Add `IsAgentOrAdmin` permission checks to `dispatch_award`, `dispatch_send`, and `job_dispatch` POST in `MaintenanceRequestViewSet` so tenants cannot call agent-only mutation actions on their own requests.

## Acceptance criteria
- [ ] `dispatch_award`, `dispatch_send`, and `job_dispatch` POST all require `IsAgentOrAdmin` (via per-action `permission_classes` or `get_permissions()` override)
- [ ] Test confirms a tenant user receives 403 on each of these three endpoints
- [ ] Existing agent/admin happy-path tests still pass

## Files likely touched
- `backend/apps/maintenance/views.py` (lines 39, 97, 119, 187)
- `backend/apps/test_hub/maintenance/` (new or updated tests)

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/maintenance/ -v`
- Tenant user: 403 on `dispatch/award`, `dispatch/send`, `dispatch/` POST
- Agent user: 200/correct response on same endpoints

## Handoff notes
2026-04-22: Promoted from discovery `2026-04-22-maintenance-dispatch-actions-missing-agent-role-check.md` (found during RNT-004 review). Tenants can currently award quotes and dispatch suppliers on their own jobs — authorisation bypass on core workflow.
