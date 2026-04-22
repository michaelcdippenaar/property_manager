---
discovered_by: rentals-reviewer
discovered_during: OPS-002
discovered_at: 2026-04-22
priority_hint: P1
suggested_prefix: OPS
---

## What I found
`admin/vite.config.ts` sets `build.sourcemap: true` unconditionally. Vite's default for `sourcemap: true` generates inline or adjacent `.js.map` files that are deployed alongside the bundle and are publicly accessible. The Sentry plugin needs source maps to exist, but they must not be reachable by end-users.

## Why it matters
Exposing source maps in production reveals the full, un-minified admin SPA source code — including route names, API paths, business logic, and any string constants — to anyone who opens DevTools or fetches the `.map` file directly. This is a meaningful information-disclosure risk for a multi-tenant SaaS admin portal.

## Where I saw it
- `admin/vite.config.ts:32` — `sourcemap: true`

## Suggested acceptance criteria (rough)
- [ ] Change `sourcemap: true` to `sourcemap: 'hidden'` so map files are generated for upload but the `//# sourceMappingURL=` comment is stripped from deployed JS bundles.
- [ ] Verify `@sentry/vite-plugin` still picks up the hidden maps and uploads them successfully in CI.
- [ ] Confirm the built `dist/` directory no longer contains reachable `*.map` references in the JS output.

## Why I didn't fix it in the current task
Out of scope; the fix is a one-word change but has a CI verification step that belongs in a focused task.
