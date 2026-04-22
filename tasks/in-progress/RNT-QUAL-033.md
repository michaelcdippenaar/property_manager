---
id: RNT-QUAL-033
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
asana_gid: "1214200406476871"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Prevent fully-onboarded tenants from seeing the welcome screen every time they open a new tab, by persisting the "seen welcome" flag durably (server-side or at minimum localStorage keyed by user ID).

## Acceptance criteria
- [ ] Welcome redirect is suppressed permanently once the tenant has dismissed it — durable across new tabs and browser restarts
- [ ] Preferred: `seen_welcome_at` DateTimeField added to `User` or `Tenant` model; set via lightweight API call when `goHome()` is invoked; router guard checks this field from the user profile response
- [ ] Acceptable fallback: `localStorage` key scoped to user ID (no backend change); PM must explicitly approve this approach
- [ ] No regression: first-time tenants still see the welcome screen

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
