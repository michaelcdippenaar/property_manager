---
id: RNT-SEC-009
stream: rentals
title: "CORS, CSRF, cookie, and security-headers hardening pass"
feature: ""
lifecycle_stage: null
priority: P1
effort: S
v1_phase: "1.0"
status: backlog
asana_gid: "1214177462239447"
assigned_to: null
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Close the common web-app browser-side attack surface before production: locked CORS origins, SameSite+Secure cookies, proper CSP, HSTS, and anti-clickjacking.

## Acceptance criteria
- [ ] `CORS_ALLOWED_ORIGINS` = explicit list (no `*`, no regex wildcards in prod)
- [ ] Session & CSRF cookies: `Secure`, `HttpOnly` (session), `SameSite=Lax` minimum (`Strict` on admin)
- [ ] `SECURE_HSTS_SECONDS = 31536000`, `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`, `SECURE_HSTS_PRELOAD = True` (after domain is stable)
- [ ] `X-Frame-Options: DENY` (or CSP `frame-ancestors 'none'`)
- [ ] Content-Security-Policy (report-only first, then enforce): default-src 'self'; restrict scripts/styles/images/fonts/connect to known origins
- [ ] `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` minimal
- [ ] Verify with Mozilla Observatory → grade B or better

## Files likely touched
- `backend/config/settings.py`
- `backend/config/middleware/security_headers.py` (new or extend)

## Test plan
**Manual:**
- `curl -I https://app.klikk.co.za` → headers present
- Run Mozilla Observatory scan → grade ≥ B

**Automated:**
- `pytest backend/config/tests/test_security_headers.py`

## Handoff notes
