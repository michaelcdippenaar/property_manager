---
discovered_by: rentals-reviewer
discovered_during: RNT-SEC-036
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found
`IsTenantOrAgent` correctly excludes the owner role from creating maintenance requests, but there is no integration test asserting `test_owner_cannot_create_maintenance_request` (i.e., owner POST returns 403). The supplier, tenant, and agent cases are all covered by the new tests in RNT-SEC-036, but owner is silently absent.

## Why it matters
The RBAC matrix should be exhaustive for every blocked role on every guarded action. An owner regression (e.g., someone adding owner to `IsTenantOrAgent.ALLOWED_ROLES` for a different feature) would not be caught by the test suite.

## Where I saw it
- `backend/tests/integration/test_rbac_matrix.py` — `TestMaintenanceRBAC` class has no `test_owner_cannot_create_maintenance_request`
- `backend/apps/accounts/permissions.py:242-246` — `IsTenantOrAgent.ALLOWED_ROLES` does not include `User.Role.OWNER`

## Suggested acceptance criteria (rough)
- [ ] Add `test_owner_cannot_create_maintenance_request` to `TestMaintenanceRBAC` asserting strict `== 403`
- [ ] Optionally add ACCOUNTANT and VIEWER coverage too (both excluded from ALLOWED_ROLES)

## Why I didn't fix it in the current task
Out of scope — RNT-SEC-036 AC covered supplier, tenant, and agent only. Adding owner is a separate test-coverage task.
