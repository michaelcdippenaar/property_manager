---
id: RNT-QUAL-064
stream: rentals-quality
title: "Move localhost CORS/CSRF origins out of base.py into local.py only"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: testing
assigned_to: tester
depends_on: []
asana_gid: "1214274171298356"
created: 2026-04-24
updated: 2026-04-25
---

## Goal

Remove localhost entries from `base.py` `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` so production never trusts localhost origins, eliminating a recurring external-audit finding.

## Acceptance criteria

- [x] `backend/config/settings/base.py` defines `CORS_ALLOWED_ORIGINS = []` and `CSRF_TRUSTED_ORIGINS = []` (or omits them) — no localhost entries.
- [x] `backend/config/settings/local.py` (or `dev.py`) extends those lists with the localhost entries currently in `base.py` (ports 5173, 5174, 5178, 9000).
- [x] `prod.py` is not affected (it should already rely on env-var injection; confirm no localhost entries remain in production path).
- [x] Existing local development workflow is unaffected — admin SPA at `localhost:5173` still functions.

## Files likely touched

- `backend/config/settings/base.py` (lines 30-35, 231-239)
- `backend/config/settings/local.py`

## Test plan

**Manual:**
- `DEBUG=False` server: confirm a localhost CORS preflight returns 403.
- `DEBUG=True` local server: confirm admin SPA loads without CORS errors.

**Automated:**
- `cd backend && python manage.py check` passes with `DJANGO_SETTINGS_MODULE=config.settings.prod`.

## Handoff notes

Promoted from discovery `2026-04-24-cors-localhost-in-base-settings.md` (2026-04-24). P2 — low-severity misconfiguration but a standard audit finding; clean up before v1 launch.

2026-04-24 (implementer): Removed `_CSRF_DEV_DEFAULTS` and the localhost entries from `_CORS_DEV_DEFAULTS` in `base.py`. `CORS_ALLOWED_ORIGINS` now starts from `_CORS_BASE_ORIGINS` (production + staging only); `CSRF_TRUSTED_ORIGINS` is an empty list plus any `CSRF_TRUSTED_ORIGINS` env-var entries. All localhost/127.0.0.1/capacitor entries (ports 5173, 5174, 5178, 9000, LAN 9501) are re-added in `local.py` after the `from .base import *`. Staging and production settings are unaffected. Added `TestProductionNoLocalhostOrigins` regression class in `backend/config/tests/test_security_headers.py` covering base and production CORS/CSRF. Smoke-checked: base module has zero localhost entries; local module has all expected entries.

2026-04-25 (reviewer): Review passed. Verified: (1) grep of base.py shows zero localhost/127.0.0.1/capacitor entries in CORS/CSRF lists — only env-var defaults and ALLOWED_HOSTS as expected; (2) local.py extends (not replaces) both lists via `list(CORS_ALLOWED_ORIGINS) + _CORS_LOCAL` and `list(CSRF_TRUSTED_ORIGINS) + _CSRF_LOCAL` — prod env-var-injected origins survive in dev; (3) all 56 tests in test_security_headers.py pass including all 4 new TestProductionNoLocalhostOrigins tests; (4) CORS_ALLOW_ALL_ORIGINS = True in local.py means dev workflow is unaffected regardless. No security concerns, no regressions found.
