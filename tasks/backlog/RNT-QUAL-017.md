---
id: RNT-QUAL-017
stream: rentals
title: "Make tenant welcome-screen redirect durable across tabs and sessions"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214227879926041"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Prevent fully-onboarded tenants from seeing the welcome screen every time they open a new tab by persisting the "welcome seen" state durably.

## Acceptance criteria
- [ ] Welcome redirect is suppressed permanently once the tenant has dismissed it — durable across new tabs and sessions
- [ ] Preferred implementation: `seen_welcome_at` DateTimeField on the User or Tenant model; set via a lightweight PATCH/POST API call when `goHome()` is invoked in the router guard; router guard checks this field on each navigation
- [ ] Acceptable fallback: `localStorage` keyed by user ID (no backend change, cleared on logout — must be explicitly accepted by PM before implementing)
- [ ] Existing new-tenant first-login welcome flow is unaffected

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
