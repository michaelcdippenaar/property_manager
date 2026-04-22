---
discovered_by: rentals-implementer
discovered_during: RNT-SEC-009
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT-SEC
---

## What I found
`SecurityHeadersMiddleware` (new in RNT-SEC-009) includes `'unsafe-inline'` and `'unsafe-eval'`
in `script-src` and `'unsafe-inline'` in `style-src`. These are needed for Vue 3 + Vite's
runtime compilation and Tailwind scoped styles. They weaken CSP's XSS protection significantly.

## Why it matters
Mozilla Observatory will dock points for `unsafe-inline`/`unsafe-eval` in script-src, capping
the grade at B. A nonce-based approach (or hash-based for inline scripts) would push to A/A+.

## Where I saw it
- `backend/config/middleware/security_headers.py` lines 64–68 (script_src / style_src)

## Suggested acceptance criteria (rough)
- [ ] Django injects a per-request CSP nonce into the template context
- [ ] Admin SPA Vite build is configured to use the nonce (vite-plugin-csp or equivalent)
- [ ] `unsafe-inline` and `unsafe-eval` removed from `script-src` in production
- [ ] Mozilla Observatory grade improves to A

## Why I didn't fix it in the current task
Requires coordinated changes to the Vite build pipeline, Vue app bootstrapping, and Django
template rendering. Would at least triple the diff size and constitutes a separate workstream.
