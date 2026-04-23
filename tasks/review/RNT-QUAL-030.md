---
id: RNT-QUAL-030
stream: rentals
title: "Ensure backend/logs/ exists on fresh checkout so Django boots cleanly"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214200629050472"
created: 2026-04-22
updated: 2026-04-23 (re-review)
---

## Goal
Prevent the cryptic `ValueError: Unable to configure handler 'maintenance_chat_file'` that stops Django (and pytest) from booting when `backend/logs/` is absent in a fresh checkout or CI environment.

## Acceptance criteria
- [x] `backend/logs/` is created automatically (via `docker-entrypoint.sh`, `Makefile setup` target, or `.gitkeep` committed) OR the `maintenance_chat_file` FileHandler falls back to `NullHandler` when the directory is absent
- [x] CI pipeline does not require a manual `mkdir backend/logs` step
- [x] `cd backend && pytest --co -q` succeeds on a fresh checkout without pre-creating the directory
- [x] Solution documented in `README` or `CONTRIBUTING` if a manual step is intentionally kept

## Files likely touched
- `backend/config/settings/base.py` (optional NullHandler fallback)
- `deploy/docker-entrypoint.sh` or `Makefile`
- `backend/logs/.gitkeep` (if gitkeep approach chosen)

## Test plan
**Manual:**
- Clone repo to a temp directory, remove `backend/logs/`, run `cd backend && pytest --co -q` — expect success

## Handoff notes
Promoted from discovery `2026-04-22-missing-logs-dir-breaks-django-setup.md` (found during RNT-SEC-002).

**2026-04-23 — implementer**

Three-part fix:

1. **`backend/logs/.gitkeep`** — tracks the directory in git so a standard `git checkout` creates it.
2. **`.gitignore`** — added `backend/logs/*.jsonl` so runtime log files (maintenance_chat.jsonl, agent_test_history.jsonl) are excluded from version control.
3. **`backend/config/settings/base.py`** — added `os.makedirs(os.path.dirname(MAINTENANCE_CHAT_LOG), exist_ok=True)` immediately after `MAINTENANCE_CHAT_LOG` is resolved. This ensures the directory is auto-created even when `MAINTENANCE_CHAT_LOG` is overridden via env var pointing to a non-existent path (e.g. CI, Docker, shallow clone without .gitkeep).

No documentation change needed: the solution is self-healing — no manual step required for any workflow.

Smoke-checks passed: `django.setup()` succeeds with the directory present, and also with it absent (makedirs creates it). `pytest --co -q` collected 1500 tests cleanly.

**2026-04-23 — reviewer: changes requested**

The approach is correct (`.gitkeep` + `makedirs` + `.gitignore` rule), but the `.gitignore` step is incomplete and carries a POPIA risk:

1. **`backend/logs/maintenance_chat.jsonl` and `backend/logs/agent_test_history.jsonl` are still tracked in git.** Running `git ls-files backend/logs/` shows both files are indexed (`git status` shows them as modified). The new `backend/logs/*.jsonl` rule in `.gitignore` only prevents *untracked* files from being staged; it does not stop git from tracking files that were committed before the rule was added. A `git rm --cached` is required to remove them from the index without deleting them from disk. Required fix: run `git rm --cached backend/logs/maintenance_chat.jsonl backend/logs/agent_test_history.jsonl` and commit that removal alongside the existing changes. After this, the `.gitignore` rule will be effective.

2. **POPIA concern:** `maintenance_chat.jsonl` contains tenant maintenance conversation data. As long as it remains tracked, every future commit in which chat activity occurs will bake that data into the repository history. Remove from index promptly.

No other issues found. The `.gitkeep`, `makedirs` placement in `base.py`, and `.gitignore` pattern are all correct — only the `git rm --cached` step is missing.

**2026-04-23 — implementer (re-review fix)**

Ran `git rm --cached backend/logs/maintenance_chat.jsonl backend/logs/agent_test_history.jsonl` to remove both files from the index. `git ls-files backend/logs/` now shows only `.gitkeep`. The files remain on disk and are now properly ignored by the `backend/logs/*.jsonl` rule added in the original commit. POPIA risk resolved — tenant chat data will no longer be baked into future commits.
