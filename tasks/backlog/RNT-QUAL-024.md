---
id: RNT-QUAL-024
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
asana_gid: "1214195383142843"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Replace the `sessionStorage`-based welcome-seen flag with a durable mechanism so onboarded tenants are not redirected to the welcome screen each time they open a new tab.

## Acceptance criteria
- [ ] Welcome redirect is suppressed permanently once the tenant has dismissed it (durable across tabs and sessions)
- [ ] Preferred: `seen_welcome_at` DateTimeField on User/Tenant model, set via a lightweight API call when `goHome()` is invoked
- [ ] Acceptable fallback: `localStorage` keyed by user ID (no backend change) — must still be cleared on logout; PM to confirm acceptability
- [ ] Existing welcome flow still shows on first login after account creation

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
