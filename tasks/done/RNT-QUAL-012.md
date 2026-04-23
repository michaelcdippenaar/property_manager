---
id: RNT-QUAL-012
stream: rentals
title: "Fix admin SPA TypeScript errors and missing main.css so npm run build exits 0"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: done
assigned_to: null
depends_on: []
asana_gid: "1214227879465027"
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Make `npm run build` and `npx vue-tsc --noEmit` in `admin/` exit 0 so CI can gate on a clean TypeScript build and sourcemap generation.

## Acceptance criteria
- [x] `admin/src/assets/main.css` is present, committed, and contains valid CSS (or the import is removed/redirected)
- [x] `npx vue-tsc --noEmit` exits 0 with zero errors (covers `ImportMeta.env`, `@sentry/vue` types, TipTap `Editor` type incompatibilities)
- [x] `npm run build` in `admin/` exits 0 (tsc clean + vite build + sourcemaps generated)
- [x] No regressions in runtime admin SPA behaviour

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

### 2026-04-23 — implementer

No code changes required. This task is a duplicate of RNT-QUAL-027 (`tasks/done/RNT-QUAL-027.md`), which was promoted from the same discovery (`2026-04-22-admin-spa-build-broken.md`) and is already `done` as of commit `d34b601`.

Smoke checks run and verified:
- `admin/src/assets/main.css` exists and contains valid Tailwind/CSS — present in tree since `d34b601`.
- `npx vue-tsc --noEmit` exits 0, zero errors.
- `npm run build` exits 0, 2303 modules transformed, sourcemaps generated in `dist/assets/`.

All acceptance criteria were satisfied by RNT-QUAL-027. No new code changes committed. Reviewer should note this is a duplicate and may wish to close/archive after review rather than progressing to testing.

### 2026-04-23 — reviewer: closed as duplicate (review passed)

Confirmed duplicate of RNT-QUAL-027 (done, commit `d34b601`). Both tasks were promoted from the same discovery `2026-04-22-admin-spa-build-broken.md`. All four acceptance criteria independently verified by reviewer:

1. `admin/src/assets/main.css` — EXISTS, contains valid Tailwind + Google Fonts import.
2. `npx vue-tsc --noEmit` — EXIT 0, zero errors.
3. `npm run build` — EXIT 0, 2303 modules transformed, sourcemaps present in `dist/assets/`.
4. No code changes in this task's commit; no regressions possible.

Security pass (no new code): no new endpoints, no PII logged, no raw SQL, no user input. Nothing to flag.

Closed directly to done as a duplicate; tester pass not required (identical scope fully tested under RNT-QUAL-027).
