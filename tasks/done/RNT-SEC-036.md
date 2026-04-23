---
id: RNT-SEC-036
stream: rentals
title: "Supplier role can POST maintenance requests (missing create guard)"
feature: ""
lifecycle_stage: null
priority: P1
effort: S
v1_phase: "1.0"
status: done
assigned_to: null
depends_on: []
asana_gid: "1214235717077123"
created: 2026-04-23
updated: 2026-04-23
---

## Goal

Block supplier users from creating maintenance requests via the API so that only tenants and agents can POST to `MaintenanceRequestViewSet`.

## Acceptance criteria
- [x] `MaintenanceRequestViewSet.get_permissions()` adds `create` to the agent-only guard, OR adds a separate `IsTenantOrAgent` permission class that returns 403 for suppliers
- [x] `POST /api/v1/maintenance/` by a supplier user returns 403
- [x] `TestMaintenanceRBAC::test_supplier_create_maintenance_is_documented` updated to assert strict `== 403` (not lenient `in (201, 400, 403)`)
- [x] Tenant `create` flow still returns 201; agent `create` flow still returns 201
- [x] POPIA note in view docstring: suppliers may only interact with jobs dispatched to them

## Files likely touched
- `backend/apps/maintenance/views.py` — `MaintenanceRequestViewSet.get_permissions()`, `_AGENT_ONLY_ACTIONS`
- `backend/apps/maintenance/permissions.py` (or shared `backend/apps/core/permissions.py`) — possibly add `IsTenantOrAgent`
- `backend/tests/integration/test_rbac_matrix.py` — `TestMaintenanceRBAC` assertions

## Test plan
**Manual:**
- Authenticate as a supplier; attempt `POST /api/v1/maintenance/` with a valid payload — expect 403
- Authenticate as a tenant; `POST /api/v1/maintenance/` — expect 201

**Automated:**
- `cd backend && pytest tests/integration/test_rbac_matrix.py -k "supplier" -v`

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-23 rentals-pm: Promoted from discovery `2026-04-23-supplier-can-create-maintenance-request.md`. Discovered by rentals-implementer during QA-009. Product decision baked into AC: both tenants and agents may create; suppliers may not.

2026-04-23 rentals-implementer: Added `IsTenantOrAgent` permission class to `backend/apps/accounts/permissions.py` (allows tenant + all agent-variant roles including admin; denies supplier, owner, viewer). Wired it into `MaintenanceRequestViewSet.get_permissions()` as the guard for `create`, layered cleanly before the existing `_AGENT_ONLY_ACTIONS` and `destroy` branches from RNT-SEC-035. Added POPIA docstring to the viewset. Renamed `test_supplier_create_maintenance_is_documented` to `test_supplier_cannot_create_maintenance_request` with strict `== 403` assertion. Added two new passing tests: `test_tenant_can_create_maintenance_request` (201) and `test_agent_can_create_maintenance_request` (201). All 13 `TestMaintenanceRBAC` tests pass.

2026-04-23 rentals-reviewer: Review passed. Checked: (1) `IsTenantOrAgent.ALLOWED_ROLES` correctly includes tenant + all 5 agent-variant roles, excludes supplier/owner/accountant/viewer; (2) `get_permissions()` create branch returns `[IsTenantOrAgent()]` before the existing `_AGENT_ONLY_ACTIONS` and `destroy` guards — order is correct; (3) POPIA docstring present in both the permission class and the viewset; (4) test renamed from lenient `in (201,400,403)` to strict `== 403`; (5) two new 201 tests for tenant and agent create present and well-formed; (6) no raw SQL, no PII logged, no secrets, no f-string queries. Minor gap noted: no `test_owner_cannot_create_maintenance_request` — dropped discovery `tasks/discoveries/2026-04-23-owner-cannot-create-maintenance-request-not-tested.md` for PM triage (not blocking).

2026-04-23 rentals-tester: Test run — all checks pass.
- `pytest tests/integration/test_rbac_matrix.py -k "supplier" -v`: 27 selected, 27 passed (includes `test_supplier_cannot_create_maintenance_request` PASSED with strict == 403).
- `pytest tests/integration/test_rbac_matrix.py::TestMaintenanceRBAC -v`: 13/13 passed — covers supplier 403, tenant 201, agent 201, owner read-only, cross-agency/cross-tenant isolation.
- Broader maintenance regression (`pytest tests/ -k "maintenance" --no-cov`): 29 passed, 0 failed.
