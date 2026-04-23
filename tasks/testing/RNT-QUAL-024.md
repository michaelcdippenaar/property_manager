---
id: RNT-QUAL-024
stream: rentals
title: "Make tenant welcome-screen redirect durable across tabs and sessions"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: testing
assigned_to: tester
depends_on: []
asana_gid: "1214195383142843"
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Replace the `sessionStorage`-based welcome-seen flag with a durable mechanism so onboarded tenants are not redirected to the welcome screen each time they open a new tab.

## Acceptance criteria
- [x] Welcome redirect is suppressed permanently once the tenant has dismissed it (durable across tabs and sessions)
- [x] Preferred: `seen_welcome_at` DateTimeField on User/Tenant model, set via a lightweight API call when `goHome()` is invoked
- [x] Acceptable fallback: `localStorage` keyed by user ID (no backend change) — must still be cleared on logout; PM to confirm acceptability
- [x] Existing welcome flow still shows on first login after account creation

## Files likely touched
- `tenant/src/router/index.ts` (lines 129-141)
- `backend/apps/accounts/models.py` (if backend field chosen)
- `backend/apps/accounts/views.py` or new lightweight endpoint

## Test plan
**Manual:**
- Complete onboarding as a tenant, dismiss welcome screen
- Open a new tab → confirm dashboard loads, not welcome screen
- Close browser, reopen → confirm no welcome redirect

**Automated:**
- `cd backend && pytest apps/test_hub/accounts/ -k "welcome"` (if backend field added)

## Handoff notes
2026-04-22: Promoted from discovery `2026-04-22-tenant-onboarding-welcome-redirect-durability.md` (found during RNT-QUAL-001 review). Implementer flagged the sessionStorage limitation in handoff notes.

2026-04-23: On inspection, the full preferred backend solution was already implemented end-to-end. No code changes were required. All components verified present and correct:
- `seen_welcome_at` DateTimeField on `User` model with migration `0018_add_seen_welcome_at.py`
- `MarkWelcomeSeenView` (`POST /auth/welcome/`) registered in `accounts/urls.py` — idempotent, returns full `UserSerializer` payload
- `seen_welcome_at` included in `UserSerializer` (read + write) and in the TypeScript `User` interface in `tenant/src/stores/auth.ts`
- `WelcomeView.vue` `goHome()` calls `api.post('/auth/welcome/')` and patches `auth.user` with the response
- Router guard in `tenant/src/router/index.ts` checks `auth.user?.seen_welcome_at` to suppress the redirect
- 5 integration tests at `backend/apps/test_hub/accounts/integration/test_welcome.py` — all pass (`pytest apps/test_hub/accounts/integration/test_welcome.py`: 5 passed)

2026-04-23: Review passed. Verified at commit 38630e03:
- Migration 0018_add_seen_welcome_at.py adds DateTimeField (null=True) on User
- MarkWelcomeSeenView (views.py:250) is IsAuthenticated, idempotent (only writes when null), uses update_fields, returns UserSerializer payload
- URL registered as auth-welcome at /auth/welcome/ (urls.py:24)
- seen_welcome_at exposed in UserSerializer (serializers.py:139) and tenant User interface (auth.ts:11)
- WelcomeView goHome() posts to /auth/welcome/ and patches auth.user with response (WelcomeView.vue:141-150)
- Router guard at tenant/src/router/index.ts:139 checks auth.user?.seen_welcome_at for tenants hitting home
- 5 integration tests in test_welcome.py pass (first-call stamp, idempotency, 401 anon, response shape, null for new users)
Security/POPIA: endpoint is auth-gated, writes only the caller's own record via request.user, no PII in logs, no raw SQL. No regressions.
