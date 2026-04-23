---
discovered_by: rentals-implementer
discovered_during: QA-009
discovered_at: 2026-04-23
priority_hint: P1
suggested_prefix: RNT-SEC
---

## What I found

The `LeaseViewSet` uses `permission_classes = [IsAuthenticated]` with no write-action guard for the `owner` role. Owners are scoped to their own leases via `get_queryset` but can currently PATCH or DELETE a lease that belongs to their property using the agent-facing API (`/api/v1/leases/<pk>/`). The `MaintenanceRequestViewSet` has the same gap — owners see requests for their property and can DELETE them (204 returned in tests).

## Why it matters

Owners should be read-only consumers of lease and maintenance data. Allowing mutation lets an owner accidentally (or deliberately) alter lease terms, delete maintenance records, or corrupt financial state. This is also a data-integrity risk under RHA.

## Where I saw it

- `backend/apps/leases/views.py:LeaseViewSet` — `permission_classes = [IsAuthenticated]`, no `perform_update`/`perform_destroy` role check
- `backend/apps/maintenance/views.py:MaintenanceRequestViewSet` — `permission_classes = [IsAuthenticated]`, no write guard for `owner` role
- Confirmed by `TestOwnerReadOnly.test_owner_cannot_patch_lease` in `tests/integration/test_rbac_matrix.py` — assertion is flexible (200 or 403) noting this as a known gap

## Suggested acceptance criteria (rough)

- [ ] `LeaseViewSet.get_permissions()` returns `[IsAgentOrAdmin]` for `create`/`update`/`partial_update`/`destroy` actions; owner and tenant remain `IsAuthenticated` for `list`/`retrieve`
- [ ] `MaintenanceRequestViewSet.get_permissions()` blocks DELETE for `owner` role (403)
- [ ] `TestOwnerReadOnly.test_owner_cannot_patch_lease` updated to assert 403 (not 200)
- [ ] `TestOwnerReadOnly.test_owner_cannot_delete_maintenance_request` updated to assert 403/405

## Why I didn't fix it in the current task

Out of scope for QA-009 (which is a test-matrix task, not a fixes task). The fix requires careful scoping to avoid breaking existing agent mutation flows, and the behaviour is now documented with a passing (lenient) assertion in the test matrix.
