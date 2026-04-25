---
id: RNT-QUAL-064
stream: rentals-quality
title: "Move localhost CORS/CSRF origins out of base.py into local.py only"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214274171298356"
created: 2026-04-24
updated: 2026-04-24
---

## Goal

Remove localhost entries from `base.py` `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` so production never trusts localhost origins, eliminating a recurring external-audit finding.

## Acceptance criteria

- [ ] `backend/config/settings/base.py` defines `CORS_ALLOWED_ORIGINS = []` and `CSRF_TRUSTED_ORIGINS = []` (or omits them) — no localhost entries.
- [ ] `backend/config/settings/local.py` (or `dev.py`) extends those lists with the localhost entries currently in `base.py` (ports 5173, 5174, 5178, 9000).
- [ ] `prod.py` is not affected (it should already rely on env-var injection; confirm no localhost entries remain in production path).
- [ ] Existing local development workflow is unaffected — admin SPA at `localhost:5173` still functions.

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
