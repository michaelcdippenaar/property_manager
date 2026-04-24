---
id: RNT-QUAL-054
stream: rentals
title: "Remove hard-coded test signer (mc@tremly.com) from ESigningPanel.vue before production"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214246263099480"
created: 2026-04-24
updated: 2026-04-24
---

## Goal
`admin/src/views/leases/ESigningPanel.vue` line 839 contains a hard-coded default signer block with `email: 'mc@tremly.com'` and phone `'0821234567'`, labelled "Pre-populated test defaults (remove before production)". This must be removed or guarded behind a dev-only env check before the admin SPA ships to production.

## Acceptance criteria
- [x] Hard-coded `mc@tremly.com` signer block at `ESigningPanel.vue:836-840` is removed or guarded with `import.meta.env.DEV`
- [x] If a dev-only stub is still wanted, it must source from an env var (e.g. `VITE_DEV_SIGNER_EMAIL`) — same pattern as RNT-SEC-045
- [x] `grep -r 'mc@tremly.com' admin/src` returns zero matches
- [x] `grep -r '0821234567' admin/src` returns zero matches
- [x] ESigningPanel still renders correctly in prod (no signer pre-filled when the lease has no tenants)

## Files likely touched
- `admin/src/views/leases/ESigningPanel.vue` (lines 836–840)
- `admin/.env.development.example` (if adding VITE_DEV_SIGNER_EMAIL)

## Test plan
**Manual:**
- In production build (`npm run build`): open a lease with no tenants → ESigningPanel signer field is empty
- In dev: if env var fallback is kept, dev signer is populated only when VITE_DEV_SIGNER_EMAIL is set

**Automated:**
- `grep -r 'mc@tremly.com' admin/src` → zero matches
- `grep -r '0821234567' admin/src` → zero matches

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-24 — rentals-pm: Promoted from discovery `2026-04-24-esigning-panel-dummy-email-default.md`. Found during RNT-SEC-045 review. Not a credential leak but ships a real staff email in the production JS bundle and risks triggering real e-sign requests during agent testing.

2026-04-24 — rentals-implementer: Replaced the hardcoded signer block in `buildDefaultSigners()` with a `return []` path. A dev-only stub remains available: if `VITE_DEV_SIGNER_EMAIL` is set and `import.meta.env.DEV` is true, ESigningPanel pre-fills a test signer using `VITE_DEV_SIGNER_NAME`, `VITE_DEV_SIGNER_EMAIL`, and `VITE_DEV_SIGNER_PHONE` env vars — identical pattern to `agent-app/src/pages/LoginPage.vue` (RNT-SEC-045). Three new vars documented in `admin/.env.development.example` with a WARNING banner. `scripts/check_hardcoded_credentials.sh` extended with a second check (Check 2) that greps for `email: '...'` / `email: "..."` assignment patterns in .vue/.ts source and fails if any match is outside a DEV guard; false-positive tested against the full codebase (placeholder attributes, mailto links, form labels are excluded by the tighter regex). Vite build (`npx vite build`) completes cleanly and `grep` over `admin/dist/` confirms the email and phone are absent from the production bundle. The pre-existing `vue-tsc` error in `src/__tests__/browser/focus-trap-keyboard.browser.test.ts` (wrong arg count) is unrelated to this task and was present before these changes.
