---
id: RNT-QUAL-055
stream: rentals
title: "Fix PushToken DELETE endpoint: return 204 No Content (currently returns 200)"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214252955502720"
created: 2026-04-24
updated: 2026-04-24
---

## Goal
Ensure `DELETE /api/v1/accounts/push-token/` returns HTTP 204 No Content when a token is successfully deleted, and the existing test `PushTokenTests::test_delete_push_token` passes.

## Context
Discovered during RNT-QUAL-050 implementation. The view at `backend/apps/accounts/views.py:256-260` (`PushTokenView.delete()`) appears to return `Response(status=status.HTTP_204_NO_CONTENT)` in code, but the test `test_delete_push_token` is failing with `200 != 204`. Likely a routing or DRF DELETE body-parsing issue where the `token` param is not being read from the DELETE request body — so no record is deleted and the response path differs. Token deletion is privacy-sensitive under POPIA (device deregistration on logout/uninstall).

## Acceptance criteria
- [ ] `DELETE /api/v1/accounts/push-token/` with `{"token": "<valid-token>"}` body deletes the token record and returns HTTP 204
- [ ] `PushTokenTests::test_delete_push_token` passes
- [ ] `DELETE /api/v1/accounts/push-token/` with a non-existent token returns 404 (or 204 if idempotent — document the chosen behaviour in the view docstring)
- [ ] No regression on `PushTokenTests::test_create_push_token` or `test_platform_validation` (from RNT-QUAL-050)

## Files likely touched
- `backend/apps/accounts/views.py` (`PushTokenView.delete()`)
- `backend/apps/test_hub/accounts/integration/test_auth.py` (line ~232–237)

## Test plan
**Manual:**
- Authenticate as a tenant, register a push token via POST, then DELETE it — confirm 204 response and token removed from DB

**Automated:**
- `cd backend && pytest apps/test_hub/accounts/integration/test_auth.py::PushTokenTests -v`

## Handoff notes
Promoted from discovery `2026-04-24-push-token-delete-returns-200.md`. Pre-existing failure, out of scope for RNT-QUAL-050 which targeted platform field validation only. Small isolated fix.
