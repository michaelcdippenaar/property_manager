---
id: RNT-QUAL-019
stream: rentals
title: "Fix admin SPA build: missing main.css and 30+ TypeScript errors"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: done
assigned_to: null
depends_on: []
asana_gid: "1214194919836355"
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Restore a clean local production build (`npm run build` exits 0) for the admin SPA by committing a valid `main.css` and resolving all TypeScript errors so `vue-tsc --noEmit` passes.

## Acceptance criteria
- [ ] `admin/src/assets/main.css` is present and committed (or the import is removed/redirected)
- [ ] `npm run build` exits 0 (vite build succeeds)
- [ ] `npx vue-tsc --noEmit` exits 0 with zero errors (covers `ImportMeta.env`, Sentry type, TipTap Editor type issues)
- [ ] CI `admin-sourcemap-check` job passes

## Files likely touched
- `admin/src/assets/main.css` (create/restore)
- `admin/src/plugins/sentry.ts`
- `admin/src/composables/useTiptapEditor.ts`
- Multiple files with `ImportMeta.env` errors (add `vite-env.d.ts` reference)

## Test plan
**Manual:**
- `cd admin && npm run build` — confirm exit 0
- `cd admin && npx vue-tsc --noEmit` — confirm 0 errors

**Automated:**
- CI `admin-sourcemap-check` job green

## Handoff notes
2026-04-22: Promoted from discovery `2026-04-22-admin-spa-build-broken.md` (found during OPS-010). Docker build currently bypasses tsc so staging works, but CI and local production builds are broken.

### 2026-04-23 — closed as duplicate
Exact duplicate of RNT-QUAL-027 (done, commit `d34b601`), which was also promoted from the same discovery `2026-04-22-admin-spa-build-broken.md`. RNT-QUAL-012 is a further confirmed duplicate of the same. All acceptance criteria — `vue-tsc --noEmit` exit 0, `npm run build` exit 0 (2299 modules, 156 sourcemaps), CI `admin-sourcemap-check` satisfied — were verified under RNT-QUAL-027 on 2026-04-22.
