---
id: RNT-SEC-015
stream: rentals
title: "Restrict maintenance dispatch actions (dispatch_award, dispatch_send, job_dispatch) to agent/admin only"
feature: ""
lifecycle_stage: null
priority: P1
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214230994934107"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Prevent tenants from calling agent-only maintenance dispatch actions by adding `IsAgentOrAdmin` permission checks to the three unprotected mutation endpoints.

## Acceptance criteria
- [ ] `dispatch_award`, `dispatch_send`, and `job_dispatch` POST actions require `IsAgentOrAdmin` (via per-action `permission_classes` on `@action` decorator or `get_permissions()` override in `MaintenanceRequestViewSet`)
- [ ] A test confirms a tenant user receives HTTP 403 on each of `dispatch/award`, `dispatch/send`, and `job_dispatch` POST
- [ ] Existing agent/admin access to these endpoints is unaffected

## Files likely touched
- `backend/apps/maintenance/views.py` (lines 39, 97, 119, 187)
- `backend/apps/test_hub/maintenance/` (new/updated tests)

## Test plan
**Manual:**
- Log in as tenant; POST to `/api/v1/maintenance/<id>/dispatch/award/` → expect 403
- Log in as tenant; POST to `/api/v1/maintenance/<id>/dispatch/send/` → expect 403
- Log in as tenant; POST to `/api/v1/maintenance/<id>/` (job_dispatch) → expect 403
- Log in as agent; same endpoints → expect 200/correct behaviour

**Automated:**
- `cd backend && pytest apps/test_hub/maintenance/ -v`

## Handoff notes
Promoted from discovery: `2026-04-22-maintenance-dispatch-actions-missing-agent-role-check.md` (RNT-004). P1 authorisation bypass — tenants can self-award quotes and dispatch suppliers without agent review.
