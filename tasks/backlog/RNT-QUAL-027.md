---
id: RNT-QUAL-027
stream: rentals
title: "Fix admin SPA build: missing main.css + 30+ TypeScript errors"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214200629245786"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Make `npm run build` in `admin/` exit 0 (tsc clean + vite build) so CI's `vue-tsc --noEmit` step and the OPS-010 sourcemap check pass.

## Acceptance criteria
- [ ] `admin/src/assets/main.css` is present and committed (or the import is removed/redirected)
- [ ] `npx vue-tsc --noEmit` exits 0 with zero errors across all `admin/src/` files
- [ ] `npm run build` exits 0 (tsc + vite build pipeline)
- [ ] Key error classes resolved: `ImportMeta.env` missing type, `@sentry/vue` import mismatch, TipTap `Editor` type incompatibility

## Files likely touched
- `admin/src/assets/main.css` (create or remove import)
- `admin/src/plugins/sentry.ts`
- `admin/src/composables/useTiptapEditor.ts`
- `admin/env.d.ts` (add `ImportMeta` env type augmentation)
- `admin/tsconfig.json`

## Test plan
**Manual:**
- `cd admin && npm run build` must complete without errors

**Automated:**
- `cd admin && npx vue-tsc --noEmit` — expect 0 errors
- CI `admin-sourcemap-check` job must pass

## Handoff notes
Promoted from discovery `2026-04-22-admin-spa-build-broken.md` (found during OPS-010).
