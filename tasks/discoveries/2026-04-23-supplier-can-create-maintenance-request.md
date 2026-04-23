---
discovered_by: rentals-implementer
discovered_during: QA-009
discovered_at: 2026-04-23
priority_hint: P1
suggested_prefix: RNT-SEC
---

## What I found

`MaintenanceRequestViewSet` uses `permission_classes = [IsAuthenticated]` for all CRUD actions. Only the `dispatch_award`, `dispatch_send`, and `job_dispatch` mutate actions are gated to `IsAgentOrAdmin`. A supplier user (who is authenticated) can therefore POST a new `MaintenanceRequest` directly via the API, bypassing the intent that maintenance requests are created by tenants (via the tenant portal) or agents.

## Why it matters

Suppliers can inject arbitrary maintenance requests and associate them with any unit — including units outside their assigned jobs. This is both a data-integrity risk and a potential spam vector. Under POPIA, suppliers should only see and interact with jobs dispatched to them.

## Where I saw it

- `backend/apps/maintenance/views.py:MaintenanceRequestViewSet.get_permissions` — `create` action is not in `_AGENT_ONLY_ACTIONS`
- Confirmed by `TestMaintenanceRBAC::test_supplier_create_maintenance_is_documented` in `tests/integration/test_rbac_matrix.py`

## Suggested acceptance criteria (rough)

- [ ] `MaintenanceRequestViewSet.get_permissions()` adds `create` to the agent-only guard OR adds a separate `IsTenantOrAgent` permission
- [ ] Supplier POST to `/api/v1/maintenance/` returns 403
- [ ] Test updated from lenient `in (201, 400, 403)` to strict `== 403`

## Why I didn't fix it in the current task

Out of scope for QA-009 (test-matrix task). The fix requires deciding whether tenants or agents should be the only allowed creators — a product decision.
