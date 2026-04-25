---
id: RNT-QUAL-068
stream: rentals-quality
title: "Log (don't swallow) exceptions in test_hub views to improve E2E triage signal"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: done
assigned_to: null
depends_on: []
asana_gid: "1214274243223426"
created: 2026-04-24
updated: 2026-04-24
---

## Goal

Replace the four silent `except Exception: pass` blocks in `test_hub/views.py` with logging so E2E failures surface their real cause rather than returning empty data.

## Acceptance criteria

- [x] `backend/apps/test_hub/views.py:92-103`: each `except Exception: pass` replaced with `logger.warning(... exc_info=True)`.
- [x] `backend/apps/test_hub/views.py:511-512`: same replacement; added one-line comment explaining RAG is optional.
- [x] Where a swallow is genuinely intentional, a one-line comment is added explaining why.
- [x] A module-level `logger` is present (`logger = logging.getLogger(__name__)` at line 34).
- [x] No E2E test regressions — existing test scenarios still pass.

## Files likely touched

- `backend/apps/test_hub/views.py` (lines 92-103, 511-512)

## Test plan

**Manual:**
- Trigger a view that hits a swallowed exception; confirm the error appears in Django test logs.

**Automated:**
- `cd backend && pytest apps/test_hub/tests/`

## Handoff notes

Promoted from discovery `2026-04-24-test-hub-views-silent-exceptions.md` (2026-04-24). P2 — improves QA signal during launch hardening; makes green E2E runs more trustworthy.

### 2026-04-24 — implementer

Added `import logging` and `logger = logging.getLogger(__name__)` at module level. Replaced three silent `except Exception: pass` blocks in `trigger_run` (parse-count loop) with `logger.warning(... exc_info=True)`, and replaced the silent `except Exception: pass` in `HealthDashboardView.get` (RAG import) with a `logger.warning` plus a comment explaining RAG is optional. All other `except Exception` blocks left untouched — they return error responses or are intentional auth guards.

Added `backend/apps/test_hub/tests/` package with `test_views_logging.py`: four tests covering the three parse-count warning paths and the RAG import warning path.

Note: views.py logging changes were committed as part of RNT-QUAL-067 (commit 026d5767) since both tasks touched the same file. caplog tests in commit 9553947b. This commit is the task file handoff only.

### 2026-04-24 — reviewer (changes requested)

`pytest apps/test_hub/tests/test_views_logging.py -v --no-cov` → 4 FAILED, 1 passed.

The four `TestParseCountLogging` tests all crash at `views.py:59` with `AttributeError: 'WSGIRequest' object has no attribute 'data'`.

Root cause: `_invoke` builds the request with `APIRequestFactory().post(...)` and passes it straight to `viewset.trigger_run(request)`. `APIRequestFactory.post` returns a raw `WSGIRequest`; `request.data` is a DRF attribute that only exists after `initialize_request` wraps it. Fix required (pick one):

1. Replace direct `trigger_run` call with `viewset.initialize_request(request)` before calling the action, **or**
2. Use `APIClient` + a real URL dispatch so DRF wraps the request automatically, **or**
3. Patch `request.data` on the mock request before passing it in (simplest for a unit test — `request.data = {"module": None}`).

The production code (views.py) and the RAG test are correct. Only the four parse-count tests need fixing. Re-submit once all 5 tests are green.

### 2026-04-25 — implementer (fix-forward)

`initialize_request` requires `action_map` (set by router dispatch) so option (b) wasn't viable without a full URL stack. Applied option (a) instead: set `request.data = {"module": None}` directly on the WSGIRequest before passing it to `trigger_run`. All 5 tests now pass (`pytest apps/test_hub/tests/test_views_logging.py -v --no-cov`). Production code unchanged.

### 2026-04-24 — reviewer (round 2 — approved)

5/5 tests green. Full suite: 1581 passed (net +4 from this task's new tests), 5 pre-existing failures in `test_permissions.py` (predating this task, unrelated). Production `views.py` unchanged from round 1. `request.data = {"module": None}` patch is the correct minimal fix — `initialize_request` legitimately requires router-set `action_map`. All acceptance criteria met.
