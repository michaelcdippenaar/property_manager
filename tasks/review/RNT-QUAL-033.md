---
id: RNT-QUAL-033
stream: rentals
title: "Make tenant welcome-screen redirect durable across tabs and sessions"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214200406476871"
created: 2026-04-22
updated: 2026-04-22

---

## Goal
Prevent fully-onboarded tenants from seeing the welcome screen every time they open a new tab, by persisting the "seen welcome" flag durably (server-side or at minimum localStorage keyed by user ID).

## Acceptance criteria
- [x] Welcome redirect is suppressed permanently once the tenant has dismissed it — durable across new tabs and browser restarts
- [x] Preferred: `seen_welcome_at` DateTimeField added to `User` or `Tenant` model; set via lightweight API call when `goHome()` is invoked; router guard checks this field from the user profile response
- [x] Acceptable fallback: `localStorage` key scoped to user ID (no backend change); PM must explicitly approve this approach — server-side approach chosen, fallback not needed
- [x] No regression: first-time tenants still see the welcome screen

## Files likely touched
- `tenant/src/router/index.ts`
- `backend/apps/accounts/models.py` (if server-side approach chosen)
- `backend/apps/accounts/serializers.py` (expose `seen_welcome_at`)
- `backend/apps/accounts/views.py` (PATCH endpoint or signal)

## Test plan
**Manual:**
- Log in as a new tenant → welcome screen appears → dismiss → open new tab → welcome screen does not appear

**Automated:**
- `cd backend && pytest apps/test_hub/accounts/ -k welcome` (if backend field added)

## Handoff notes
Promoted from discovery `2026-04-22-tenant-onboarding-welcome-redirect-durability.md` (found during RNT-QUAL-001). PM: decide server-side vs localStorage approach before implementation starts.

### 2026-04-22 — implementer
Chose the server-side approach (preferred path). Changes made:

**Backend:**
- `backend/apps/accounts/models.py`: added `seen_welcome_at = DateTimeField(null, blank)` to `User`.
- `backend/apps/accounts/serializers.py`: exposed `seen_welcome_at` in `UserSerializer` (writable by the user, so the PATCH on /auth/me/ can also set it if needed, but the dedicated endpoint is the canonical path).
- `backend/apps/accounts/views.py`: added `MarkWelcomeSeenView` — idempotent POST, stamps `seen_welcome_at` on first call, returns full user profile.
- `backend/apps/accounts/urls.py`: registered `POST /auth/welcome/` → `MarkWelcomeSeenView`.
- `backend/apps/accounts/migrations/0018_add_seen_welcome_at.py`: auto-generated migration.

**Frontend (tenant SPA):**
- `tenant/src/stores/auth.ts`: added `seen_welcome_at?: string | null` to the `User` interface.
- `tenant/src/router/index.ts`: replaced `sessionStorage`-based guard with `auth.user?.seen_welcome_at` check. Redirect only fires for `role === 'tenant'` with a null `seen_welcome_at`. The old double-check with `klikk_welcome_checked` is gone — no more phantom redirects.
- `tenant/src/views/home/WelcomeView.vue`: `goHome()` now fire-and-forgets `POST /auth/welcome/`, merges the response into `auth.user`, then navigates. Non-fatal catch so a network blip never strands the user.

**Tests:** 5 passing integration tests in `backend/apps/test_hub/accounts/integration/test_welcome.py` covering first-call stamp, idempotency, 401 on anon, response shape, and null `seen_welcome_at` on a fresh user.
