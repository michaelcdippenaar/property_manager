---
id: RNT-SEC-035
stream: rentals
title: "Owner role can PATCH leases and DELETE maintenance requests (missing write guard)"
feature: ""
lifecycle_stage: null
priority: P1
effort: S
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214221203782966"
created: 2026-04-23
updated: 2026-04-23T12:00:00
---

## Goal

Restrict the `owner` role to read-only access on `LeaseViewSet` and `MaintenanceRequestViewSet` so that PATCH/DELETE calls from an owner return 403.

## Acceptance criteria
- [x] `LeaseViewSet.get_permissions()` returns `[IsAgentOrAdmin]` for `create`, `update`, `partial_update`, and `destroy` actions; `owner` and `tenant` roles remain permitted for `list`/`retrieve`
- [x] `MaintenanceRequestViewSet.get_permissions()` blocks `destroy` for the `owner` role (returns 403)
- [x] `TestOwnerReadOnly.test_owner_cannot_patch_lease` in `tests/integration/test_rbac_matrix.py` updated to assert strict 403 (not flexible 200-or-403)
- [x] `TestOwnerReadOnly.test_owner_cannot_delete_maintenance_request` updated to assert 403/405
- [x] No regression: existing agent `update`/`destroy` flows still pass

## Files likely touched
- `backend/apps/leases/views.py` — `LeaseViewSet.get_permissions()`
- `backend/apps/maintenance/views.py` — `MaintenanceRequestViewSet.get_permissions()`
- `backend/tests/integration/test_rbac_matrix.py` — `TestOwnerReadOnly` assertions

## Test plan
**Manual:**
- Log in as an owner user; attempt `PATCH /api/v1/leases/<pk>/` — expect 403
- Attempt `DELETE /api/v1/maintenance/<pk>/` as owner — expect 403

**Automated:**
- `cd backend && pytest tests/integration/test_rbac_matrix.py -k "owner" -v`

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-23 rentals-pm: Promoted from discovery `2026-04-23-owner-write-access-on-leases.md`. Discovered by rentals-implementer during QA-009. Lenient test assertions already exist in the RBAC matrix — tighten them as part of this fix.

2026-04-23 rentals-implementer: Implemented and verified.

Changes:
- `backend/apps/leases/views.py`: Added `IsAgentOrAdmin` import and `get_permissions()` on `LeaseViewSet` that routes `create/update/partial_update/destroy` through `[IsAgentOrAdmin()]`; all other actions fall through to `super()` (IsAuthenticated). Owners and tenants retain `list`/`retrieve` access.
- `backend/apps/maintenance/views.py`: Extended the existing `get_permissions()` on `MaintenanceRequestViewSet` with an explicit branch for `destroy` returning `[IsAgentOrAdmin()]`. The existing `_AGENT_ONLY_ACTIONS` set is unchanged so RNT-SEC-036 can layer on top without conflict.
- `backend/tests/integration/test_rbac_matrix.py`: Tightened `TestOwnerReadOnly.test_owner_cannot_patch_lease` to assert strict 403 (removed `in (200, 403)` leniency). Tightened `test_owner_cannot_delete_maintenance_request` to assert strict 403 (removed `204/403/405` leniency).

Test results: `TestOwnerReadOnly` 4/4 passed; `TestLeasesRBAC` + `TestMaintenanceRBAC` 24/24 passed — no regressions.
