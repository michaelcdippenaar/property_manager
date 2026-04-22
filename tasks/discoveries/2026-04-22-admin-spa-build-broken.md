---
discovered_by: rentals-implementer
discovered_during: OPS-010
discovered_at: 2026-04-22
priority_hint: P1
suggested_prefix: RNT-QUAL
---

## What I found
`npm run build` in `admin/` fails with two blockers: (1) `src/assets/main.css` is listed in `.gitignore` or was never committed — it exists as a path in the `ls` output as a directory entry but is not a real file (`head` returns "No such file or directory"), causing Rollup to abort; (2) there are 30+ TypeScript errors across `src/` (missing `ImportMeta.env`, stale Sentry type declarations, incompatible TipTap `Editor` types, etc.). The Docker build uses `npx vite build` (bypasses tsc), so staging builds currently succeed, but CI's `vue-tsc --noEmit` step and the new `admin-sourcemap-check` CI job added by OPS-010 will fail until these are resolved.

## Why it matters
No local production build is possible; the OPS-010 sourcemap CI check cannot verify `.map` file generation locally. If CI ever switches to `npm run build` (which includes `vue-tsc`), the pipeline will be broken.

## Where I saw it
- `admin/src/assets/main.css` — file missing from working tree
- `admin/src/plugins/sentry.ts:12` — `Cannot find module '@sentry/vue'` (TS error, module exists at runtime)
- `admin/src/composables/useTiptapEditor.ts:115` — TipTap `Editor` type incompatibility
- Multiple `Property 'env' does not exist on type 'ImportMeta'` across ~10 files

## Suggested acceptance criteria (rough)
- [ ] `src/assets/main.css` is present and committed (or the import is moved/removed)
- [ ] `npm run build` exits 0 (tsc clean + vite build)
- [ ] `npx vue-tsc --noEmit` exits 0 with zero errors

## Why I didn't fix it in the current task
Out of scope — OPS-010 is a one-line sourcemap config change. Fixing 30+ TS errors and a missing CSS file is a separate QA/hardening task.
