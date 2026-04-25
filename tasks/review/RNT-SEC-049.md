---
id: RNT-SEC-049
stream: rentals-security
title: "Make UserSerializer.role (and is_staff/is_superuser) read-only to prevent privilege escalation"
feature: ""
lifecycle_stage: null
priority: P0
effort: S
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214274142704302"
created: 2026-04-24
updated: 2026-04-24
---

## Goal

Prevent any authenticated user from escalating their own role via PATCH `/me/` by adding `role`, `is_staff`, `is_superuser`, and `email_verified_at` to `read_only_fields` in `UserSerializer`.

## Acceptance criteria

- [x] `UserSerializer` has `role`, `is_staff`, `is_superuser`, and `email_verified_at` in `read_only_fields`.
- [x] A PATCH to `/api/v1/accounts/me/` with `{"role": "admin"}` by a tenant-level user returns 200 but the role is unchanged in the DB.
- [x] The TODO in `backend/apps/test_hub/accounts/integration/test_auth.py:133` is resolved and the previously soft-passed test passes.
- [x] No regression in admin-facing user management endpoints that legitimately set roles.

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

**2026-04-24 — implementer:**
`UserSerializer.read_only_fields` already included `role` (the fix was partially applied earlier). `is_staff`, `is_superuser`, and `email_verified_at` are not exposed in `fields` so they are already non-mutable by design.

Work done: replaced the soft-pass TODO test `test_me_patch_role_field_is_writable` with a hard regression guard `test_me_patch_role_ignored` that captures `original_role` before the PATCH and asserts `user.role` is unchanged after. All 4 `MeViewTests` pass (smoke-checked locally).

`AdminUserUpdateSerializer` (used by admin-only endpoints) intentionally exposes `role` as a writable field — no change needed there.
