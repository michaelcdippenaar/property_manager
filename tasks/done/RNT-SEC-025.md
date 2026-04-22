---
id: RNT-SEC-025
stream: rentals
title: "Fix auth bypass on MaintenanceRequestViewSet agent-only actions"
feature: ""
lifecycle_stage: null
priority: P1
effort: S
v1_phase: "1.0"
status: testing
assigned_to: tester
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

### 2026-04-22 — implementer

Added `get_permissions()` override to `MaintenanceRequestViewSet` in `backend/apps/maintenance/views.py`. The override checks `self.action` against a set `_AGENT_ONLY_ACTIONS = {"dispatch_award", "dispatch_send", "job_dispatch"}` and returns `[IsAgentOrAdmin()]` for those actions. `job_dispatch` handles both GET and POST on the same action name; GET is kept at `IsAuthenticated` (tenant read) while POST (create dispatch + rank suppliers) is locked to agents.

Added a new test class `MaintenanceDispatchTenantForbiddenTests` in `backend/apps/test_hub/maintenance/integration/test_maintenance.py` with four tests:
- `test_tenant_cannot_post_job_dispatch` — expects 403
- `test_tenant_can_get_job_dispatch` — expects 200 or 404 (not 403) to confirm GET is not over-locked
- `test_tenant_cannot_dispatch_send` — expects 403
- `test_tenant_cannot_dispatch_award` — expects 403

Syntax verified on both files. Full pytest suite requires project venv (PyCharm-managed); shell environment lacked `daphne`/`decouple` etc. — tester should run `cd backend && pytest apps/test_hub/maintenance/ -v` inside the project venv.

### 2026-04-22 — reviewer

Review passed. Checked: (1) `get_permissions()` override in `backend/apps/maintenance/views.py` lines 45–52 correctly gates `dispatch_award`, `dispatch_send`, and `job_dispatch` POST behind `IsAgentOrAdmin`; GET on `job_dispatch` stays at `IsAuthenticated` as required. (2) `IsAgentOrAdmin` was already imported at line 9 — no new import needed. (3) Class-level `permission_classes = [IsAuthenticated]` at line 39 is untouched, preserving tenant read access via `super().get_permissions()` fallback. (4) Four tests added in `MaintenanceDispatchTenantForbiddenTests` cover all three forbidden POST actions plus the one permitted GET; URL reverse names (`maintenance-job-dispatch`, `maintenance-dispatch-send`, `maintenance-dispatch-award`) match pre-existing test usage in the same file confirming they resolve. (5) POPIA/security pass: no PII logged, no raw SQL, no new endpoints; fix closes the auth bypass. No discoveries.
