---
id: RNT-QUAL-017
stream: rentals
title: "Make tenant welcome-screen redirect durable across tabs and sessions"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: done
assigned_to: done
depends_on: []
asana_gid: "1214227879926041"
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Prevent fully-onboarded tenants from seeing the welcome screen every time they open a new tab by persisting the "welcome seen" state durably.

## Acceptance criteria
- [x] Welcome redirect is suppressed permanently once the tenant has dismissed it — durable across new tabs and sessions
- [x] Preferred implementation: `seen_welcome_at` DateTimeField on the User or Tenant model; set via a lightweight PATCH/POST API call when `goHome()` is invoked in the router guard; router guard checks this field on each navigation
- [ ] Acceptable fallback: `localStorage` keyed by user ID (no backend change, cleared on logout — must be explicitly accepted by PM before implementing)
- [x] Existing new-tenant first-login welcome flow is unaffected

## Files likely touched
- `tenant/src/router/index.ts` (lines 129–141, replace sessionStorage with localStorage or API call)
- `backend/apps/accounts/models.py` (add `seen_welcome_at` DateTimeField if backend approach chosen)
- `backend/apps/accounts/views.py` or `serializers.py` (expose field via API)
- `backend/apps/test_hub/accounts/` (migration + test)

## Test plan
**Manual:**
- Log in as tenant; dismiss welcome screen; open new tab → should NOT see welcome screen again
- Log out and log back in → should NOT see welcome screen again
- Fresh tenant account (never dismissed) → should see welcome screen on first login

**Automated:**
- `cd backend && pytest apps/test_hub/accounts/ -v` (if backend model change)
- `cd tenant && npx vue-tsc --noEmit` (zero errors)

## Handoff notes
Promoted from discovery: `2026-04-22-tenant-onboarding-welcome-redirect-durability.md` (RNT-QUAL-001). Implementer correctly flagged as out-of-scope; sessionStorage clears on tab close causing repetitive welcome screen for onboarded tenants.

### 2026-04-23 — implementer review

On inspection, the full server-side durability implementation was already present across all layers. No code changes were required. Confirmed:

- `seen_welcome_at` `DateTimeField` exists on `User` model (`backend/apps/accounts/models.py` line 74) with migration `0018_add_seen_welcome_at.py` applied.
- `UserSerializer` includes `seen_welcome_at` in its `fields` list (`serializers.py` line 139), so `GET /auth/me/` returns it on every `fetchMe()` call.
- `MarkWelcomeSeenView` (POST `/auth/welcome/`) stamps the field idempotently and returns the updated `UserSerializer` payload; wired at `auth/welcome/` in `accounts/urls.py`.
- `tenant/src/stores/auth.ts` `User` interface declares `seen_welcome_at?: string | null`; `fetchMe()` populates it from the API response.
- `tenant/src/router/index.ts` router guard (line 132) checks `auth.user?.seen_welcome_at` — no `sessionStorage` or `localStorage` present.
- `tenant/src/views/home/WelcomeView.vue` `goHome()` fires `api.post('/auth/welcome/')` fire-and-forget, then merges the response into `auth.user`.
- `npx vue-tsc --noEmit` exits 0 (zero TypeScript errors).

The fallback `localStorage` criterion is intentionally unchecked — the preferred server-side approach is fully in place and the fallback was never needed.

### 2026-04-23 — Review passed (reviewer)

Verified all named artefacts exist and are correct: `seen_welcome_at` DateTimeField on `User` model at line 74 with migration `0018_add_seen_welcome_at.py`; `UserSerializer` includes the field at line 139; `MarkWelcomeSeenView` at line 250 is `IsAuthenticated`-gated, idempotent, uses `update_fields`, returns `UserSerializer` payload; wired at `auth/welcome/`; `auth.ts` `User` interface declares `seen_welcome_at?: string | null`; router guard at line 132 checks `auth.user?.seen_welcome_at`; `WelcomeView.vue` `goHome()` fires `api.post('/auth/welcome/')` and merges response into store; no `sessionStorage`/`localStorage` present. `npx vue-tsc --noEmit` exits 0. No auth/POPIA issues found. Moving directly to done — implementation was pre-existing, no tester battery required.
