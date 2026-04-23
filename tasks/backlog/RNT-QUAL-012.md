---
id: RNT-QUAL-012
stream: rentals
title: "Fix admin SPA TypeScript errors and missing main.css so npm run build exits 0"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214227879465027"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Make `npm run build` and `npx vue-tsc --noEmit` in `admin/` exit 0 so CI can gate on a clean TypeScript build and sourcemap generation.

## Acceptance criteria
- [ ] `admin/src/assets/main.css` is present, committed, and contains valid CSS (or the import is removed/redirected)
- [ ] `npx vue-tsc --noEmit` exits 0 with zero errors (covers `ImportMeta.env`, `@sentry/vue` types, TipTap `Editor` type incompatibilities)
- [ ] `npm run build` in `admin/` exits 0 (tsc clean + vite build + sourcemaps generated)
- [ ] No regressions in runtime admin SPA behaviour

## Files likely touched
- `admin/src/assets/main.css` (create or fix import)
- `admin/src/plugins/sentry.ts` (fix `@sentry/vue` type import)
- `admin/src/composables/useTiptapEditor.ts` (fix `Editor` type)
- Multiple files with `ImportMeta.env` — add `/// <reference types="vite/client" />` or update `tsconfig.json`
- `admin/tsconfig.json`

## Test plan
**Manual:**
- `cd admin && npm run build` — exit code 0, `dist/` populated with `.map` files
- `cd admin && npx vue-tsc --noEmit` — exit code 0, zero errors

**Automated:**
- CI `admin-sourcemap-check` job (added by OPS-010) should pass

## Handoff notes
Promoted from discovery: `2026-04-22-admin-spa-build-broken.md` (OPS-010). Blocking the CI sourcemap check added by OPS-010 and any future `vue-tsc` CI step.
