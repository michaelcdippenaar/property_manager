---
id: RNT-QUAL-015
stream: rentals
title: "Ensure backend/logs/ directory exists at startup so Django does not crash on fresh checkout"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: done
assigned_to: null
depends_on: []
asana_gid: "1214229862711371"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Eliminate the `ValueError: Unable to configure handler 'maintenance_chat_file'` crash on fresh checkouts by ensuring `backend/logs/` exists before Django boots.

## Acceptance criteria
- [ ] `backend/logs/` is created automatically by a bootstrap script (`Makefile`, `docker-entrypoint.sh`, or CI setup step), OR the `FileHandler` is replaced with a `NullHandler` when `LOG_TO_FILE=False` / in test mode
- [ ] A fresh `git clone` + `pytest` run does not require a manual `mkdir backend/logs` step
- [ ] CI pipeline does not require a manual directory creation step
- [ ] If a manual step is kept, `README` or `CONTRIBUTING` documents it clearly

## Files likely touched
- `backend/config/settings/base.py` (logging config, ~line 280)
- `Makefile` or `docker-entrypoint.sh` (add `mkdir -p backend/logs`)
- `.github/workflows/ci.yml` (add `mkdir -p backend/logs` step if not handled elsewhere)

## Test plan
**Manual:**
- Fresh checkout (no `backend/logs/`); run `cd backend && pytest` — Django boots without error

**Automated:**
- CI run from clean state passes without manual intervention

## Handoff notes
Promoted from discovery: `2026-04-22-missing-logs-dir-breaks-django-setup.md` (RNT-SEC-002). Blocks full test suite on fresh checkouts with a cryptic, hard-to-diagnose error.

### 2026-04-23 — rentals-pm

Duplicate of RNT-QUAL-030, already shipped. `.gitkeep` committed, `os.makedirs` guard added to `base.py`, JSONL files removed from git index; 1500 tests collected cleanly on fresh checkout. Closing as duplicate.
