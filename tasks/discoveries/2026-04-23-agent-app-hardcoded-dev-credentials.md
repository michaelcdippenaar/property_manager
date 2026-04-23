---
discovered_by: rentals-reviewer
discovered_during: RNT-010
discovered_at: 2026-04-23
priority_hint: P1
suggested_prefix: RNT-SEC
---

## What I found
`agent-app/src/pages/LoginPage.vue` hard-codes a real-looking email (`mc@tremly.com`) and password (`Number55dip`) as default values for the login + password-reset forms when `import.meta.env.DEV` is true (lines 119, 120, 129).

## Why it matters
- A real-looking credential pair is committed to a public-ish repo. Even if it is a dev-only default, credential reuse or a stale account elsewhere could turn this into an account takeover.
- Leaks the product owner's email to anyone who clones the repo.
- New devs get surprising behaviour — their login form pre-fills with someone else's creds.

## Where I saw it
- `agent-app/src/pages/LoginPage.vue:119`
- `agent-app/src/pages/LoginPage.vue:120`
- `agent-app/src/pages/LoginPage.vue:129`

## Suggested acceptance criteria (rough)
- [ ] Remove hard-coded email/password defaults from LoginPage.vue
- [ ] If dev-mode pre-fill is desired, source it from `process.env.DEV_LOGIN_EMAIL` / `DEV_LOGIN_PASSWORD` (optional, documented in `.env.development.example`, empty by default)
- [ ] Rotate the exposed password on the real account if it is still live
- [ ] Same check for admin/ and web_app/ LoginPage equivalents

## Why I didn't fix it in the current task
Out of scope — RNT-010 is a DX task to add `.env.*.example` files, not a credential-hygiene pass. Found while grepping `import.meta.env` usage to verify env coverage.
