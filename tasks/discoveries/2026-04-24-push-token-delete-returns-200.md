---
discovered_by: rentals-implementer
discovered_during: RNT-QUAL-050
discovered_at: 2026-04-24
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found
`PushTokenTests::test_delete_push_token` is failing with `200 != 204`. The `DELETE /api/v1/accounts/push-token/` endpoint returns HTTP 200 but the test expects 204. This is a pre-existing failure unrelated to the RNT-QUAL-050 platform validation fix.

## Why it matters
Token deletion is a privacy-sensitive operation (POPIA — devices should be deregistered on logout/uninstall). Returning 200 on DELETE is non-standard and the test documents the correct expected behaviour (204 No Content).

## Where I saw it
- `backend/apps/accounts/views.py:256-260` — `PushTokenView.delete()` returns `Response(status=status.HTTP_204_NO_CONTENT)` — looks correct in code, but the test is still failing. Likely a routing or DRF DELETE body-parsing issue where the `token` param isn't being read from the DELETE request body, so no record is deleted and the response differs.
- `backend/apps/test_hub/accounts/integration/test_auth.py:232-237`

## Suggested acceptance criteria (rough)
- [ ] `DELETE /api/v1/accounts/push-token/` with `{"token": "..."}` body deletes the token and returns 204
- [ ] `PushTokenTests::test_delete_push_token` passes

## Why I didn't fix it in the current task
Out of scope — RNT-QUAL-050 is scoped to platform field validation only. Fixing the DELETE behaviour would expand the diff and risks touching the test that RNT-QUAL-050 acceptance criteria says must not regress.
