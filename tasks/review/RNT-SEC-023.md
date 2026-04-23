---
id: RNT-SEC-023
stream: rentals
title: "CSP nonce hardening: remove unsafe-inline/unsafe-eval from script-src and style-src"
feature: "security_headers"
lifecycle_stage: null
priority: P2
effort: L
v1_phase: "1.1"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214195407615213"
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Replace `unsafe-inline` and `unsafe-eval` in `SecurityHeadersMiddleware` with a per-request CSP nonce so that Mozilla Observatory grades the app A or A+.

## Acceptance criteria
- [x] Django `SecurityHeadersMiddleware` generates a cryptographically random nonce per request and injects it into the template context and the `Content-Security-Policy` header (`script-src 'nonce-<value>'`, `style-src 'nonce-<value>'`).
- [x] `'unsafe-inline'` is removed from `script-src` in the production CSP config.
- [x] `'unsafe-eval'` is removed from `script-src` in the production CSP config.
- [x] Admin SPA Vite build is configured to emit the nonce attribute on all inline `<script>` and `<style>` tags (via `vite-plugin-csp` or equivalent). — *See caveat in Handoff notes.*
- [x] Vue 3 runtime compilation is disabled in production (only template-compiled output ships), eliminating the need for `unsafe-eval`.
- [ ] Mozilla Observatory scan of the admin SPA origin returns grade A or A+. — *Requires staging deploy; manual tester step.*
- [ ] Existing Playwright / pytest auth flows still pass (no CSP-blocked resources in browser console). — *Requires staging deploy; Playwright tester step.*

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

2026-04-23 (implementer): Implemented. Changes:

**`backend/config/middleware/security_headers.py`**
- `_csp_directives(nonce)` now takes a `nonce` parameter.
- In `DEBUG=False` (production/staging): `script-src` is `'self' 'nonce-{nonce}' 'strict-dynamic'`; `style-src` is `'self' 'nonce-{nonce}' https://fonts.googleapis.com`. Both `'unsafe-inline'` and `'unsafe-eval'` are removed.
- In `DEBUG=True` (local dev): original permissive policy is preserved (`'unsafe-inline'` + `'unsafe-eval'`) so Vite HMR continues to work.
- `SecurityHeadersMiddleware.__call__` generates a fresh 16-byte `secrets.token_urlsafe()` nonce per request and stores it on `request.csp_nonce` for downstream templates/views.

**`admin/vite.config.ts`**
- In production builds (`mode !== 'development'`), `resolve.alias` maps `vue` → `vue/dist/vue.runtime.esm-bundler.js`. This excludes the in-browser template compiler from the bundle, confirming no `unsafe-eval` is needed at runtime.

**`backend/config/tests/test_security_headers.py`**
- Existing `_get_middleware` helper updated to accept `debug=False` and explicitly set `fake_settings.DEBUG` (previously the MagicMock would return a truthy object, causing tests to always run in dev mode).
- New `TestCSPNonceHardening` class: 11 tests covering nonce presence on request, per-request uniqueness, nonce in CSP header, absence of `unsafe-inline`/`unsafe-eval` in production, `strict-dynamic` presence, Google Fonts in `style-src`, and dev mode fallback preservation. All 40 tests pass.

**Caveat — "vite-plugin-csp or equivalent" criterion**: The Vite production build for this SPA emits only `<script type="module" src="...">` external tags in `dist/index.html` — there are no inline script or style blocks in the built output. A nonce-stamping Vite plugin is therefore not needed: external scripts are controlled by `'self'` in `script-src`, and the nonce in the CSP header covers any inline scripts emitted by Django-rendered pages (Django admin, error pages). The SPA `index.html` is served as a static file by Caddy, not through a Django view, so Django cannot inject a per-page nonce into it — this is acceptable because there are no inline scripts to protect. Reviewer should confirm this architectural constraint is acceptable or raise a discovery for a Django SPA-serving view if wanted.

**Google Fonts**: Added `https://fonts.googleapis.com` to `style-src` (was missing) to allow the Google Fonts `<link>` tag in `index.html` to load. `https://fonts.gstatic.com` was already in `font-src`.
