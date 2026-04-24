---
id: RNT-QUAL-054
stream: rentals
title: "Remove hard-coded test signer (mc@tremly.com) from ESigningPanel.vue before production"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214246263099480"
created: 2026-04-24
updated: 2026-04-24
---

## Goal
`admin/src/views/leases/ESigningPanel.vue` line 839 contains a hard-coded default signer block with `email: 'mc@tremly.com'` and phone `'0821234567'`, labelled "Pre-populated test defaults (remove before production)". This must be removed or guarded behind a dev-only env check before the admin SPA ships to production.

## Acceptance criteria
- [ ] Hard-coded `mc@tremly.com` signer block at `ESigningPanel.vue:836-840` is removed or guarded with `import.meta.env.DEV`
- [ ] If a dev-only stub is still wanted, it must source from an env var (e.g. `VITE_DEV_SIGNER_EMAIL`) — same pattern as RNT-SEC-045
- [ ] `grep -r 'mc@tremly.com' admin/src` returns zero matches
- [ ] `grep -r '0821234567' admin/src` returns zero matches
- [ ] ESigningPanel still renders correctly in prod (no signer pre-filled when the lease has no tenants)

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
