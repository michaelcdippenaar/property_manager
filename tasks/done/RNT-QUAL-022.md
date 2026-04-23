---
id: RNT-QUAL-022
stream: rentals
title: "Ensure backend/logs/ directory exists at startup to prevent Django boot failure"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: done
assigned_to: null
depends_on: []
asana_gid: "1214195382944651"
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Prevent the `ValueError: Unable to configure handler 'maintenance_chat_file'` startup crash that occurs on fresh checkouts without a `backend/logs/` directory.

## Acceptance criteria
- [x] `backend/logs/` is created by a bootstrap/setup script (Makefile, docker-entrypoint, or CI step), OR the `FileHandler` falls back to `NullHandler` when `DEBUG=True`/in test mode
- [x] CI pipeline does not require a manual `mkdir backend/logs` step
- [x] Full pytest suite runs from a clean checkout without the ValueError
- [x] `README` or `CONTRIBUTING` documents any remaining manual step (if kept)

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

2026-04-23: All acceptance criteria already satisfied by commit `9c3f5896` (task RNT-QUAL-030, now `done`), which was implemented before this task was claimed. Specifically:
- `backend/logs/.gitkeep` tracked in git ensures the directory exists on all fresh checkouts.
- `os.makedirs(os.path.dirname(MAINTENANCE_CHAT_LOG), exist_ok=True)` added at `backend/config/settings/base.py` line 272 ensures the directory is created at Django boot even when the git-tracked `.gitkeep` is missing (e.g. env-var override of `MAINTENANCE_CHAT_LOG` pointing elsewhere).
- `backend/logs/*.jsonl` added to `.gitignore` to keep runtime log files out of version control.
- CI pipeline makes no `mkdir` call and works on a fresh checkout because the `.gitkeep` is committed.
- No manual steps are required, so criterion 4 (document manual steps) is satisfied trivially — there are none.

No code changes were needed in this task. Reviewer: verify the above commit is in main and criteria pass.


2026-04-23: Review passed. Verified commit 9c3f5896 is in main: backend/logs/.gitkeep tracked, os.makedirs at backend/config/settings/base.py:272 creates dir before LOGGING config is applied, backend/logs/*.jsonl in .gitignore line 37. All 4 acceptance criteria satisfied without code changes in this task. No security/POPIA concerns (logging config only, no new endpoints or user input). Handing off to tester.

2026-04-23: Test run — all checks pass.
- PASS: backend/logs/.gitkeep confirmed tracked in git (`git ls-files backend/logs/` → `backend/logs/.gitkeep`).
- PASS: os.makedirs at backend/config/settings/base.py:272 confirmed present.
- PASS: backend/logs/*.jsonl in .gitignore confirmed at line 37.
- PASS: Django setup completes cleanly — `django.setup()` prints "Django setup OK" with no ValueError.
- PASS: pytest collection succeeds — 1703 tests collected with no ValueError at startup. (Pre-existing failures in unrelated account tests are not caused by this task's changes.)
- All 4 acceptance criteria verified satisfied.
