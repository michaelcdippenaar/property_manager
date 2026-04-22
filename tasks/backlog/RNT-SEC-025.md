---
id: RNT-SEC-025
stream: rentals
title: "Fix auth bypass on MaintenanceRequestViewSet agent-only actions"
feature: ""
lifecycle_stage: null
priority: P1
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214218083783108"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Prevent tenants from calling agent-only dispatch actions (`dispatch_award`, `dispatch_send`, `job_dispatch` POST) on their own maintenance requests, closing an authorisation bypass that allows a tenant to award quotes and dispatch suppliers without agent review.

## Acceptance criteria
- [ ] `dispatch_award`, `dispatch_send`, and `job_dispatch` POST all require `IsAgentOrAdmin` (via per-action `permission_classes` or `get_permissions()` override)
- [ ] A test confirms a tenant user receives HTTP 403 on each of these three endpoints
- [ ] Existing agent and admin tests continue to pass
- [ ] Class-level `permission_classes = [IsAuthenticated]` is retained for tenant read actions (GET)

## Files likely touched
- `backend/apps/maintenance/views.py`
- `backend/apps/test_hub/maintenance/` (new or updated tests)

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/maintenance/ -v`

## Handoff notes
Promoted from discovery `2026-04-22-maintenance-dispatch-actions-missing-agent-role-check.md` (found during RNT-004). P1 security: tenant can bypass agent review to award quotes and dispatch suppliers.
