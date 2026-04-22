---
id: RNT-SEC-023
stream: rentals
title: "CSP nonce hardening: remove unsafe-inline/unsafe-eval from script-src and style-src"
feature: "security_headers"
lifecycle_stage: null
priority: P2
effort: L
v1_phase: "1.1"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214195407615213"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Replace `unsafe-inline` and `unsafe-eval` in `SecurityHeadersMiddleware` with a per-request CSP nonce so that Mozilla Observatory grades the app A or A+.

## Acceptance criteria
- [ ] Django `SecurityHeadersMiddleware` generates a cryptographically random nonce per request and injects it into the template context and the `Content-Security-Policy` header (`script-src 'nonce-<value>'`, `style-src 'nonce-<value>'`).
- [ ] `'unsafe-inline'` is removed from `script-src` in the production CSP config.
- [ ] `'unsafe-eval'` is removed from `script-src` in the production CSP config.
- [ ] Admin SPA Vite build is configured to emit the nonce attribute on all inline `<script>` and `<style>` tags (via `vite-plugin-csp` or equivalent).
- [ ] Vue 3 runtime compilation is disabled in production (only template-compiled output ships), eliminating the need for `unsafe-eval`.
- [ ] Mozilla Observatory scan of the admin SPA origin returns grade A or A+.
- [ ] Existing Playwright / pytest auth flows still pass (no CSP-blocked resources in browser console).

## Files likely touched
- `backend/config/middleware/security_headers.py` (lines 64–68: script_src / style_src)
- `backend/config/settings/base.py` (CSP settings if extracted)
- `admin/vite.config.ts` (nonce plugin, disable runtime compiler)
- `admin/index.html` (nonce placeholder injection)
- `admin/src/main.ts` (ensure no `new Function` / eval usage at runtime)

## Test plan
**Manual:**
- Run `curl -I https://<staging-domain>/` and inspect `Content-Security-Policy` header — confirm no `unsafe-inline` or `unsafe-eval` in `script-src`.
- Open admin SPA in Chrome; check DevTools Console for any CSP-blocked resource errors.
- Submit a Mozilla Observatory scan (`https://observatory.mozilla.org/`) on the staging origin; confirm grade A or A+.

**Automated:**
- `cd backend && pytest apps/accounts/tests/ -k "csp"` (add a unit test asserting nonce present and unsafe directives absent in response headers).
- Playwright smoke: `mcp__tremly-e2e__login_agent` — verify no console errors after login page load.

## Handoff notes
2026-04-22 (rentals-pm): Promoted from discovery `2026-04-22-csp-nonce-hardening.md`. Found by rentals-implementer during RNT-SEC-009. `unsafe-inline`/`unsafe-eval` were kept as placeholders for Vue 3 + Vite runtime compatibility; nonce approach requires coordinated Django + Vite changes and was correctly deferred out of RNT-SEC-009 scope. Targeting v1.1 phase.
