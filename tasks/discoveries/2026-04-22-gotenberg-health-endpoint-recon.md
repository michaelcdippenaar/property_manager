---
discovered_by: rentals-reviewer
discovered_during: RNT-SEC-004
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT-SEC
---

## What I found
`GET /api/v1/esigning/gotenberg/health/` (`GotenbergHealthView`) is protected by `IsAgentOrAdmin + can_manage_esigning`, but it proxies Gotenberg's `/health` response verbatim, which includes engine names, version info, and internal service structure. This is an information-disclosure vector if an agent account is ever compromised.

## Why it matters
Any authenticated agent can map internal infrastructure (Chromium, LibreOffice presence, version strings). Not a direct exploit, but useful in a targeted attack. Should be gated the same way as test endpoints or limited to admin-only.

## Where I saw it
- `backend/apps/esigning/views.py:387` — `GotenbergHealthView`
- `backend/apps/esigning/urls.py:45` — `gotenberg/health/` route

## Suggested acceptance criteria (rough)
- [ ] Restrict `GotenbergHealthView` to `IsAdminUser` only (not agents), OR gate it behind `ENABLE_TEST_ENDPOINTS`, OR strip version/engine fields from the response before returning to the client.
- [ ] Add a test asserting agents (non-admin) receive 403.

## Why I didn't fix it in the current task
Out of scope for RNT-SEC-004, which only targeted explicitly labelled test/debug endpoints. GotenbergHealthView is an operational monitoring endpoint and the right scope/access decision needs a product call.
