---
discovered_by: ux-onboarding
discovered_during: UX-002
discovered_at: 2026-04-23
priority_hint: P0
suggested_prefix: UX
---

## What I found
The tenant web app (`tenant/`) has no invite-accept / password-set screen. The backend `UserInviteAcceptView` exists and the email sends an `invite_url`, but there is no route in the tenant router that handles that URL. A new tenant who clicks their invite link lands on the generic login screen with no context and no way to set a password.

## Why it matters
This is the very first interaction a new tenant has with the platform. A broken or missing invite-accept flow means tenants cannot self-register. The agent must manually set the password out-of-band, which is both a security risk and a support cost. Every single new tenant is affected.

## Where I saw it
- `tenant/src/router/index.ts` — no `/invite/:token` or `/accept-invite` route exists
- `backend/apps/accounts/views.py:381` — `UserInviteAcceptView` (GET + POST) is implemented
- `content/emails/invite_tenant.md` — email sends `invite_url` CTA but destination route is missing

## Suggested acceptance criteria (rough)
- [ ] Route `/invite/:token` added to tenant router
- [ ] GET: pre-fills email (read-only) from backend, prompts for full name + password
- [ ] POST: accepts invite, logs user in, redirects to welcome screen
- [ ] Expired / cancelled invite shows a clear error with agent contact prompt
- [ ] Covered by at least one integration test

## Why I didn't fix it in the current task
This is a new feature (missing route + view), not a UX copy fix. Out of scope for the audit task; requires implementation work.
