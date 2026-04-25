---
id: RNT-QUAL-068
stream: rentals-quality
title: "Log (don't swallow) exceptions in test_hub views to improve E2E triage signal"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214274243223426"
created: 2026-04-24
updated: 2026-04-24
---

## Goal

Replace the four silent `except Exception: pass` blocks in `test_hub/views.py` with logging so E2E failures surface their real cause rather than returning empty data.

## Acceptance criteria

- [ ] `backend/apps/test_hub/views.py:92-103`: each `except Exception: pass` replaced with `logger.exception(...)` (or `logger.warning` with `exc_info=True`).
- [ ] `backend/apps/test_hub/views.py:511-512`: same replacement.
- [ ] Where a swallow is genuinely intentional, a one-line comment is added explaining why.
- [ ] A module-level `logger` is present (add if missing).
- [ ] No E2E test regressions — existing test scenarios still pass.

## Files likely touched

- `backend/apps/test_hub/views.py` (lines 92-103, 511-512)

## Test plan

**Manual:**
- Trigger a view that hits a swallowed exception; confirm the error appears in Django test logs.

**Automated:**
- `cd backend && pytest apps/test_hub/tests/`

## Handoff notes

Promoted from discovery `2026-04-24-test-hub-views-silent-exceptions.md` (2026-04-24). P2 — improves QA signal during launch hardening; makes green E2E runs more trustworthy.
