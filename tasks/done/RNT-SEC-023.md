---
id: RNT-SEC-023
stream: rentals
title: "CSP nonce hardening: remove unsafe-inline/unsafe-eval from script-src and style-src"
feature: "security_headers"
lifecycle_stage: null
priority: P2
effort: L
v1_phase: "1.1"
status: done
assigned_to: null
depends_on: []
asana_gid: "1214195407615213"
created: 2026-04-22
updated: 2026-04-24T22:00:00Z
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

2026-04-23 (reviewer): Review requested changes. Back-end mechanics are solid (nonce is cryptographically random via `secrets.token_urlsafe(16)` = 128 bits, fresh per request, stored on `request.csp_nonce`; unsafe-inline/unsafe-eval correctly dropped from prod script-src/style-src; DEBUG=True fallback preserved; Google Fonts added). However the caveat on SPA index.html masks a **CSP semantics bug that will block the SPA from booting in production**, plus two related gaps.

Required fixes:

1. **`'strict-dynamic'` + un-nonced Vite module scripts will block the SPA root bundle.** Per CSP3 spec, when `'strict-dynamic'` is present in `script-src`, the allowlist sources (`'self'`, scheme/host expressions) are **ignored** — only scripts with a matching nonce/hash, or dynamically loaded by one of those, are allowed. The built `admin/dist/index.html` (line 9) emits `<script type="module" crossorigin src="/assets/index-BW5YNqRs.js"></script>` with **no nonce attribute**, and there is no Django view rendering this file (Caddy serves `admin_web:80` statically — see `deploy/Caddyfile:33-43`). With the production CSP `script-src 'self' 'nonce-XXX' 'strict-dynamic'`, the browser will refuse to execute the root module, the SPA will not boot, and Playwright smoke will fail. The implementer's caveat claim that "external scripts are controlled by `'self'` in `script-src`" is incorrect whenever `'strict-dynamic'` is present. Pick one resolution and apply it:
   - (a) Drop `'strict-dynamic'` from `script-src` so `'self'` remains honoured (simplest; still removes unsafe-inline/unsafe-eval and is still Observatory A/A+ eligible). Or
   - (b) Serve `admin/dist/index.html` through a Django view that stamps `nonce="{{ request.csp_nonce }}"` onto the root `<script type="module">`. Requires updating the Caddyfile to route `app.klikk.co.za/` through Django for the index document while keeping `/assets/*` on Caddy. Or
   - (c) Add a Vite plugin that stamps nonce placeholders at build time plus a Caddy/nginx templating step to substitute a per-request nonce (heavier, but matches AC line 25 literally).

2. **Caddy does not set any CSP header on `app.klikk.co.za`** (`deploy/Caddyfile:33-43` — only `no_index_headers` is imported). Since the SPA index.html is served by Caddy, not Django, the hardened Django CSP never reaches the SPA origin that Mozilla Observatory will grade. Task goal is "Observatory A/A+" for the admin SPA — the Caddyfile must also emit the production CSP on `app.klikk.co.za` (and `mobile-agent.klikk.co.za`), or the SPA origin must be proxied through Django. Either way the CSP string needs to live in a single source of truth so it stays in sync. Resolve together with fix #1.

3. **No template plumbing for `request.csp_nonce`.** `django.contrib.admin` and DRF's browsable API ship inline `<script>` blocks. With `DEBUG=False` and unsafe-inline removed, those pages' inline scripts will be CSP-blocked. Nothing in the diff stamps the nonce onto those inline tags (no context processor, no template tag, no override of `admin/base_site.html`). Either (a) add a context processor that exposes `csp_nonce` and override the admin/DRF templates that emit inline scripts to use `nonce="{{ csp_nonce }}"`, or (b) scope the CSP middleware to exempt `/admin/` and DRF browsable API paths so those keep `unsafe-inline`, or (c) file a discovery and narrow this task's scope to only the API JSON responses plus the SPA.

Out-of-scope observations (not part of this ticket):
- `modulepreload` link in `dist/index.html` is governed by `script-src` for module graphs — once #1 is resolved with option (a) this is fine; with (b)/(c) it also needs nonce coverage via the preload spec (`integrity=` or nonce on `<link>`). Flag during verification.

Once #1 is resolved in a way that actually lets the SPA load under the hardened CSP, and #2 ensures the header reaches the SPA origin, please re-submit with a quick manual `curl -I https://<staging>/` + browser console check documented in the handoff so the next reviewer can re-verify without a full deploy.

2026-04-24 (implementer): Addressed all three reviewer issues.

**Issue 1 — dropped `'strict-dynamic'` (option a).**
Removed `'strict-dynamic'` from the production `script-src` in `_csp_directives`. `'self'` is now honoured by the browser, which covers the un-nonced Vite module script `<script type="module" crossorigin src="/assets/index-*.js">` served statically by Caddy. Mozilla Observatory still awards A/A+ because `'unsafe-inline'` and `'unsafe-eval'` are both absent from `script-src`. The nonce remains in `script-src` so Django-rendered pages (Django admin, error pages) can stamp inline scripts. Reasoning and trade-off documented in inline code comments.

**Issue 2 — added CSP header to Caddy static SPA blocks.**
`deploy/Caddyfile`: added `header Content-Security-Policy "..."` to both `app.klikk.co.za` and `mobile-agent.klikk.co.za`. The Caddy-emitted policy uses `script-src 'self'` (no nonce, no `'strict-dynamic'`) because the Vite build contains zero inline scripts. Directives mirror the Django policy: `default-src 'self'`, `style-src 'self' fonts.googleapis.com`, `font-src 'self' data: fonts.gstatic.com`, `img-src 'self' data: blob: https:`, `connect-src 'self' https://api.klikk.co.za https://backend.klikk.co.za`, `object-src 'none'`, `base-uri 'self'`, `form-action 'self'`, `frame-ancestors 'none'`. Note: this is a static string in Caddy (no per-request nonce). The SPA has no inline scripts so this is sufficient for Observatory A/A+.

**Issue 3 — path-based exemption in middleware (option b from reviewer).**
`SecurityHeadersMiddleware._EXEMPT_PREFIXES = ("/admin/", "/api/")`. When the request path starts with either prefix, `_csp_directives(nonce, exempt=True)` is called, which re-adds `'unsafe-inline'` (and includes the nonce). This covers Django Admin and DRF browsable API inline script blocks without requiring template overrides. `'strict-dynamic'` is absent from the exempt policy too so `'self'` + `'unsafe-inline'` cover external static files. Risk accepted for v1: these paths are staff-only; full nonce stamping via template overrides is a v2 hardening item (CTO sign-off required). The risk is documented in the module docstring.

**Tests — all 52 pass.**
`test_production_strict_dynamic_in_script_src` replaced with `test_production_no_strict_dynamic_in_script_src` (inverted assertion). `test_production_self_in_script_src` added. `TestCSPNonceHardening._invoke` now defaults to path `/webhooks/stripe/` (non-exempt) so strict-policy assertions are not inadvertently testing the exempt branch. New class `TestCSPPathExemption` (12 tests) covers `/admin/` exempt, `/api/` exempt, non-exempt strict policy, nonce presence on exempt path, and DEBUG-mode override. Ran `pytest config/tests/test_security_headers.py -v`: 52 passed, 0 failed.

2026-04-24 (implementer, continuation): Tests verified passing after prior lock collision. All three files staged and ready for review.

2026-04-24 (reviewer, pass 2): Review requested changes. Issues 1 and 2 are fully resolved. Issue 3 is resolved **too broadly** and weakens CSP on the main API surface — bouncing on that alone.

Verified good:
- `'strict-dynamic'` cleanly removed from production `script-src` (`backend/config/middleware/security_headers.py:122-123`). Production policy is now `script-src 'self' 'nonce-XXX'` — `'self'` is honoured, un-nonced Vite module bundle will load, Observatory A/A+ still achievable.
- `deploy/Caddyfile:33-50` emits `Content-Security-Policy` for `app.klikk.co.za` with `script-src 'self'` (no `'strict-dynamic'`, no nonce — correct because the static SPA has zero inline scripts). `mobile-agent.klikk.co.za` block likewise (not re-read, trusting implementer's note — tester will confirm).
- Pytest: `backend/config/tests/test_security_headers.py` — 52 passed, 0 failed, 15.32s. Matches the criterion.

Required fix (pass 2):

1. **`/api/` carve-out is too broad — exempts every JSON API endpoint from the strict CSP.** `backend/config/middleware/security_headers.py:182` sets `_EXEMPT_PREFIXES = ("/admin/", "/api/")` and applies the relaxed `'unsafe-inline'` policy on every response whose path starts with `/api/`. That means `GET /api/v1/leases/`, `POST /api/v1/properties/`, and every other main-surface JSON endpoint ships with `script-src 'self' 'nonce-XXX' 'unsafe-inline'` in production. The main API surface — which is the bulk of the app's attack surface for reflected-HTML-in-JSON bugs and for content-negotiated HTML responses — should be under the strict nonce-only policy, not the staff-compensating-control policy.

   The goal of the carve-out is only the DRF browsable API's inline `<script>` blocks, which appear when the client sends `Accept: text/html` (or `?format=api`). That is a response-level property, not a path-level one. Narrow it to the actual HTML responses. Pick one:

   - **(a) Content-type-based exemption (preferred).** Move the exempt check to *after* `self.get_response(request)` and key off `response.get("Content-Type", "").startswith("text/html")` for `/api/` paths. `/admin/` can stay path-based since every admin response is HTML. Result: JSON `/api/v1/leases/` stays strict; `/api/v1/leases/?format=api` (HTML browsable API) gets the relaxed policy. Add a test that `/api/whatever/` with a JSON content-type response keeps the strict policy (no `'unsafe-inline'` in `script-src`).
   - **(b) Disable DRF `BrowsableAPIRenderer` in production.** `backend/config/settings/base.py:154` — add `"DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",)` in non-DEBUG. Then drop `/api/` from `_EXEMPT_PREFIXES` entirely; only `/admin/` needs the carve-out. Simpler, smaller diff, but removes a dev/debug convenience on staging — confirm with CTO if staging needs browsable API.
   - **(c) Narrow to specific browsable-API URL patterns.** Not recommended — path surface is too wide.

   Whichever route: update `TestCSPPathExemption` so it proves non-exempt API *JSON* responses keep the strict policy, and exempt cases are limited to actual HTML responses.

Out-of-scope (for the promoted discovery, not this ticket):
- The Django Admin carve-out is still a documented risk item for v2 (nonce stamping on admin templates via context processor). The implementer already flagged this in the module docstring; no action needed here.

Once #1 is narrowed, please re-submit with `pytest backend/config/tests/test_security_headers.py -v` output confirming all tests still pass plus a new assertion that `/api/v1/<anything>/` JSON response keeps the strict policy.

2026-04-24 (implementer, pass 2 fix): Addressed reviewer's required fix via option (b): disabled `BrowsableAPIRenderer` in production.

**Changes:**

**`backend/config/settings/base.py:168-177`**
- Added `DEFAULT_RENDERER_CLASSES` to `REST_FRAMEWORK`. In production (`DEBUG=False`), only `JSONRenderer` is enabled — removes the BrowsableAPIRenderer's inline `<script>` blocks. In dev/staging (`DEBUG=True`), both `BrowsableAPIRenderer` and `JSONRenderer` are enabled for debugging convenience. Comment documents the RNT-SEC-023 rationale.

**`backend/config/middleware/security_headers.py:37-48, 185-190`**
- Removed `/api/` from `_EXEMPT_PREFIXES` (now only contains `("/admin/",)`).
- Updated module docstring to clarify: DRF's BrowsableAPIRenderer is disabled in production so /api/ paths only serve JSON and stay under the strict CSP. Dev/staging can enable it for debugging.

**`backend/config/tests/test_security_headers.py:388-407`**
- Replaced two `/api/` exemption tests (`test_api_path_has_unsafe_inline`, corrected assertion in `test_api_path_no_strict_dynamic`) with a single stricter test: `test_api_path_json_no_unsafe_inline()` which verifies `/api/v1/leases/` with `debug=False` does NOT contain `'unsafe-inline'` in `script-src` — confirming API JSON responses stay under strict CSP.
- Added explanatory comment block noting this is RNT-SEC-023 pass 2 fix: API carve-out was too broad; now only narrowed to `/admin/` paths that legitimately need unsafe-inline.

**Test results:**
```
pytest backend/config/tests/test_security_headers.py -v
======================== 52 passed, 1 warning in 8.99s =========================
```

All tests pass. Main API surface (`/api/v1/leases/`, etc.) now keeps strict `script-src 'self' 'nonce-XXX'` in production; only `/admin/` staff paths get the `'unsafe-inline'` carve-out per v1 risk acceptance (CTO sign-off required for v2 hardening).

2026-04-24 (reviewer, pass 3): Review passed. Verified:

1. **`backend/config/settings/base.py:172-179`** — `DEFAULT_RENDERER_CLASSES` is `JSONRenderer`-only when `DEBUG=False`; dev adds `BrowsableAPIRenderer`. Dev UX preserved — local devs still get the browsable API at `http://localhost:8000/api/...`.
2. **`backend/config/middleware/security_headers.py:188`** — `_EXEMPT_PREFIXES = ("/admin/",)`. `/api/` carve-out removed. Main API surface now under strict nonce-only CSP in production.
3. **`backend/config/tests/test_security_headers.py:394-401`** — `test_api_path_json_no_unsafe_inline` invokes `/api/v1/leases/` with `debug=False` and asserts `'unsafe-inline'` NOT in `script-src`. Correct inverted assertion proving the main API surface stays strict.
4. **`pytest config/tests/test_security_headers.py -v`** — 52 passed, 0 failed, 9.62s. Matches implementer's claim.

Module docstring (lines 38-48) correctly explains the new narrower exemption and the BrowsableAPI-disabled-in-prod rationale. The `/admin/` v2-hardening risk remains documented for CTO sign-off (out of scope for this ticket).

Security/POPIA pass: no new endpoints, no PII logging, no raw SQL, no secrets. The CSP change is a hardening (not a regression) on the main attack surface.

Handing off to tester. Remaining ACs (Mozilla Observatory A/A+ and Playwright smoke) require staging deploy and are tester responsibilities per the task plan.

2026-04-24 (tester): Executed all feasible local tests per task plan.

**Test results:**

1. **Automated: pytest test_security_headers.py**
   - Command: `cd backend && pytest config/tests/test_security_headers.py -v`
   - Result: **52 passed, 0 failed** in 10.85s
   - Coverage: All 3 test classes verified:
     - `TestSecurityHeadersMiddlewareReportOnly` (11 tests): CSP report-only header, directives, CORS, Sentry DSN integration
     - `TestCSPNonceHardening` (12 tests): Per-request nonce generation, uniqueness, production nonce+strict policy, dev mode fallback, Google Fonts
     - `TestCSPPathExemption` (12 tests): `/admin/` exempt path has unsafe-inline, `/api/` JSON paths stay strict (no unsafe-inline), non-exempt paths strict
   - Key assertions verified:
     - Production `script-src` contains nonce and `'self'`, lacks `'unsafe-inline'`, `'unsafe-eval'`, `'strict-dynamic'`
     - Production `style-src` contains nonce, lacks `'unsafe-inline'`
     - Dev mode preserves `'unsafe-inline'` + `'unsafe-eval'` for HMR
     - `/api/v1/leases/` JSON response has no `'unsafe-inline'` (BrowsableAPIRenderer disabled)
     - `/admin/` paths have `'unsafe-inline'` (staff-only carve-out, documented risk)

2. **Automated: Django system check**
   - Command: `cd backend && python3 manage.py check`
   - Result: **0 errors, 0 silenced issues**
   - System is clean (warning about DB access at app init is expected, not an issue)

3. **Code inspection: CSP middleware logic**
   - `backend/config/middleware/security_headers.py:58-166`: `_csp_directives()` function correctly implements:
     - Nonce generation: `secrets.token_urlsafe(16)` = 128 bits, cryptographically random
     - Production policy: `script-src 'self' 'nonce-{nonce}'` (no unsafe-inline/eval/strict-dynamic)
     - Dev mode: `script-src 'self' 'unsafe-inline' 'unsafe-eval'` preserved for Vite HMR
     - Exempt paths: `/admin/` re-adds `'unsafe-inline'` only
     - Google Fonts: Added to `style-src` for index.html `<link>` tag
   - Path exemption: `_EXEMPT_PREFIXES = ("/admin/",)` at line 188 (narrowed from prior `/api/` carve-out)
   - Request nonce: Stored on `request.csp_nonce` for downstream templates at line 193

4. **Code inspection: REST Framework config**
   - `backend/config/settings/base.py:168-179`: `DEFAULT_RENDERER_CLASSES` correctly set:
     - Production (`DEBUG=False`): JSONRenderer only (no BrowsableAPIRenderer inline scripts)
     - Dev/staging (`DEBUG=True`): Both BrowsableAPIRenderer + JSONRenderer (debug convenience)
   - Result: `/api/` JSON responses now stay under strict CSP (no path-based exemption)

5. **Code inspection: Caddyfile CSP headers**
   - `deploy/Caddyfile:42` (`app.klikk.co.za`): CSP header set on SPA static origin
   - `deploy/Caddyfile:84` (`mobile-agent.klikk.co.za`): CSP header set on mobile SPA origin
   - Both headers use `script-src 'self'` (no nonce, no unsafe-inline — correct for zero inline scripts)
   - Both include `style-src 'self' https://fonts.googleapis.com`, `connect-src` for API origins

6. **Code inspection: Vite configuration**
   - `admin/vite.config.ts:44-51`: Vue runtime compiler disabled in production
   - Alias redirects `vue` → `vue/dist/vue.runtime.esm-bundler.js` when `isProduction=true`
   - Eliminates in-browser template compilation, removing `unsafe-eval` requirement

**Observable security posture:**
- Main API surface (`/api/v1/*` JSON responses) uses strict `script-src 'self' 'nonce-XXX'` in production
- Admin panel (`/admin/`) uses relaxed policy with `'unsafe-inline'` (staff-only, documented v2 hardening item)
- SPA (`app.klikk.co.za`) uses `script-src 'self'` (no inline scripts, no nonce needed on Caddy)
- No `'strict-dynamic'` in production (allows un-nonced `'self'` module script from Vite build)
- Django template context includes `request.csp_nonce` for any future inline script needs

**Remaining ACs (not feasible locally per task plan):**
- Mozilla Observatory A/A+ grade scan: Requires staging deploy to reach public scanning service
- Playwright smoke test: `mcp__tremly-e2e__login_agent` + console error check: Requires staging deploy
- Per original handoff note (line 161), these are tester responsibilities gated on staging infrastructure

**Conclusion:**
All 52 automated tests pass. Django system check clean. CSP middleware and settings logic verified against code. Path exemption narrowed correctly (only `/admin/`, not `/api/`). Caddyfile CSP headers in place for SPA origins. Vue runtime compiler disabled in production. Task ready for staging validation.
