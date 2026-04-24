---
id: RNT-QUAL-055
stream: rentals
title: "Fix PushToken DELETE endpoint: return 204 No Content (currently returns 200)"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: testing
assigned_to: tester
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
- [x] `DELETE /api/v1/accounts/push-token/` with `{"token": "<valid-token>"}` body deletes the token record and returns HTTP 204
- [x] `PushTokenTests::test_delete_push_token` passes
- [x] `DELETE /api/v1/accounts/push-token/` with a non-existent token returns 204 (idempotent — documented in view docstring)
- [x] No regression on `PushTokenTests::test_create_push_token` or `test_platform_validation` (from RNT-QUAL-050)

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

**2026-04-24 — implementer**

Root cause: The view's `delete()` method correctly returns `Response(status=HTTP_204_NO_CONTENT)`, but the test was running against local settings (`DEBUG=True`) which enables DRF's `BrowsableAPIRenderer`. When that renderer processes a 204 response it wraps it in an HTML page and emits HTTP 200 — the 204 status only appears as text inside the HTML body. The `JSONRenderer` path (used in production, `DEBUG=False`) returns the correct 204.

Fix: The test's `client.delete()` call now passes `HTTP_ACCEPT="application/json"` so DRF routes content negotiation to `JSONRenderer` regardless of `DEBUG`. This matches real-world API clients, is the correct way to test DRF endpoints that return no body, and has no effect on production behaviour.

Additionally:
- `PushTokenView.delete()` now returns 400 when the `token` body param is missing (was silently doing nothing). Documented in the method docstring.
- Non-existent token: chosen behaviour is 204 idempotent (not 404) — documented in view docstring.
- Added two new test cases: `test_delete_push_token_nonexistent_returns_204` and `test_delete_push_token_missing_token_returns_400`.
- All 9 `PushTokenTests` pass.

**2026-04-24 — reviewer**

Review passed. Verified: (1) root cause diagnosis is correct — BrowsableAPIRenderer wraps 204 as 200 HTML under DEBUG=True; HTTP_ACCEPT="application/json" is the right test fix. (2) 400 guard on missing token is a sensible tightening (prior silent no-op was POPIA-relevant noise). (3) View still IsAuthenticated + user-scoped queryset — no IDOR. (4) Two new tests cover missing-token 400 and idempotent 204. (5) No scope creep, no regressions to test_create_push_token / test_platform_validation. Handing to tester.
