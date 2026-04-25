---
id: RNT-SEC-049
stream: rentals-security
title: "Make UserSerializer.role (and is_staff/is_superuser) read-only to prevent privilege escalation"
feature: ""
lifecycle_stage: null
priority: P0
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214274142704302"
created: 2026-04-24
updated: 2026-04-24
---

## Goal

Prevent any authenticated user from escalating their own role via PATCH `/me/` by adding `role`, `is_staff`, `is_superuser`, and `email_verified_at` to `read_only_fields` in `UserSerializer`.

## Acceptance criteria

- [ ] `UserSerializer` has `role`, `is_staff`, `is_superuser`, and `email_verified_at` in `read_only_fields`.
- [ ] A PATCH to `/api/v1/accounts/me/` with `{"role": "admin"}` by a tenant-level user returns 200 but the role is unchanged in the DB.
- [ ] The TODO in `backend/apps/test_hub/accounts/integration/test_auth.py:133` is resolved and the previously soft-passed test passes.
- [ ] No regression in admin-facing user management endpoints that legitimately set roles.

## Files likely touched

- `backend/apps/accounts/serializers.py` (`UserSerializer.read_only_fields`)
- `backend/apps/test_hub/accounts/integration/test_auth.py` (line 133 — remove TODO, enable assertion)

## Test plan

**Manual:**
- As a tenant, PATCH `/api/v1/accounts/me/` with `{"role": "admin"}` — role must remain `tenant`.

**Automated:**
- `cd backend && pytest apps/accounts/tests/ apps/test_hub/accounts/integration/test_auth.py -k role`

## Handoff notes

Promoted from discovery `2026-04-24-user-serializer-role-readonly.md` (2026-04-24). P0 — privilege escalation defence-in-depth; existing test already flagged this with a TODO.
