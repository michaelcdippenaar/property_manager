---
discovered_by: rentals-reviewer
discovered_during: RNT-004
discovered_at: 2026-04-22
priority_hint: P1
suggested_prefix: RNT-SEC
---

## What I found
`MaintenanceRequestViewSet` in `backend/apps/maintenance/views.py` has `permission_classes = [IsAuthenticated]` at the class level. The `dispatch_award`, `dispatch_send`, and `job_dispatch` (POST) actions have no per-action `permission_classes` override restricting them to agents/admins. A tenant who can access their own `MaintenanceRequest` (via `get_queryset`) can call these agent-only mutation actions.

## Why it matters
A tenant could POST to `dispatch/award` to award a quote on their own job, bypassing agent review — changing job status to IN_PROGRESS and creating a `SupplierJobAssignment` with themselves as `assigned_by`. They could also POST to `dispatch/send` to dispatch suppliers directly. This is an authorisation bypass on a core workflow action.

## Where I saw it
- `backend/apps/maintenance/views.py:39` — class-level `permission_classes = [IsAuthenticated]`
- `backend/apps/maintenance/views.py:187` — `dispatch_award` no role check
- `backend/apps/maintenance/views.py:119` — `dispatch_send` no role check
- `backend/apps/maintenance/views.py:97` — `job_dispatch` POST no role check

## Suggested acceptance criteria (rough)
- [ ] `dispatch_award`, `dispatch_send`, and `job_dispatch` POST require `IsAgentOrAdmin` (via per-action `permission_classes` on the `@action` decorator or via `get_permissions()` override)
- [ ] A test confirms a tenant user receives 403 on each of these endpoints

## Why I didn't fix it in the current task
Pre-existing before RNT-004 diff. RNT-004 only added the `SupplierJobAssignment` creation block inside `dispatch_award` — fixing the auth gap would be out of scope and doubles the diff.
