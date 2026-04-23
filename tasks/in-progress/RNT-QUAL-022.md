---
id: RNT-QUAL-022
stream: rentals
title: "Ensure backend/logs/ directory exists at startup to prevent Django boot failure"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214195382944651"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Prevent the `ValueError: Unable to configure handler 'maintenance_chat_file'` startup crash that occurs on fresh checkouts without a `backend/logs/` directory.

## Acceptance criteria
- [ ] `backend/logs/` is created by a bootstrap/setup script (Makefile, docker-entrypoint, or CI step), OR the `FileHandler` falls back to `NullHandler` when `DEBUG=True`/in test mode
- [ ] CI pipeline does not require a manual `mkdir backend/logs` step
- [ ] Full pytest suite runs from a clean checkout without the ValueError
- [ ] `README` or `CONTRIBUTING` documents any remaining manual step (if kept)

## Files likely touched
- `backend/config/settings/base.py` (logging config, ~line 280-284)
- `Makefile` or `docker-entrypoint.sh` (mkdir step)
- `.github/workflows/ci.yml` (ensure logs dir created before pytest)

## Test plan
**Manual:**
- Fresh checkout (no `backend/logs/`): `cd backend && pytest` — confirm no ValueError at startup

**Automated:**
- CI run on fresh checkout — suite boots and runs

## Handoff notes
2026-04-22: Promoted from discovery `2026-04-22-missing-logs-dir-breaks-django-setup.md` (found during RNT-SEC-002 tester run). Took significant debugging time — the error is cryptic and pre-empts all tests.
