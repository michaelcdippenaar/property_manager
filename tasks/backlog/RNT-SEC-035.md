---
id: RNT-SEC-035
stream: rentals
title: "Owner role can PATCH leases and DELETE maintenance requests (missing write guard)"
feature: ""
lifecycle_stage: null
priority: P1
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214221203782966"
created: 2026-04-23
updated: 2026-04-23
---

## Goal

Restrict the `owner` role to read-only access on `LeaseViewSet` and `MaintenanceRequestViewSet` so that PATCH/DELETE calls from an owner return 403.

## Acceptance criteria
- [ ] `LeaseViewSet.get_permissions()` returns `[IsAgentOrAdmin]` for `create`, `update`, `partial_update`, and `destroy` actions; `owner` and `tenant` roles remain permitted for `list`/`retrieve`
- [ ] `MaintenanceRequestViewSet.get_permissions()` blocks `destroy` for the `owner` role (returns 403)
- [ ] `TestOwnerReadOnly.test_owner_cannot_patch_lease` in `tests/integration/test_rbac_matrix.py` updated to assert strict 403 (not flexible 200-or-403)
- [ ] `TestOwnerReadOnly.test_owner_cannot_delete_maintenance_request` updated to assert 403/405
- [ ] No regression: existing agent `update`/`destroy` flows still pass

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
