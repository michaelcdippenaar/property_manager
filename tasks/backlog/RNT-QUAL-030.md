---
id: RNT-QUAL-030
stream: rentals
title: "Ensure backend/logs/ exists on fresh checkout so Django boots cleanly"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214200629050472"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Prevent the cryptic `ValueError: Unable to configure handler 'maintenance_chat_file'` that stops Django (and pytest) from booting when `backend/logs/` is absent in a fresh checkout or CI environment.

## Acceptance criteria
- [ ] `backend/logs/` is created automatically (via `docker-entrypoint.sh`, `Makefile setup` target, or `.gitkeep` committed) OR the `maintenance_chat_file` FileHandler falls back to `NullHandler` when the directory is absent
- [ ] CI pipeline does not require a manual `mkdir backend/logs` step
- [ ] `cd backend && pytest --co -q` succeeds on a fresh checkout without pre-creating the directory
- [ ] Solution documented in `README` or `CONTRIBUTING` if a manual step is intentionally kept

## Files likely touched
- `backend/config/settings/base.py` (optional NullHandler fallback)
- `deploy/docker-entrypoint.sh` or `Makefile`
- `backend/logs/.gitkeep` (if gitkeep approach chosen)

## Test plan
**Manual:**
- Clone repo to a temp directory, remove `backend/logs/`, run `cd backend && pytest --co -q` — expect success

## Handoff notes
Promoted from discovery `2026-04-22-missing-logs-dir-breaks-django-setup.md` (found during RNT-SEC-002).
