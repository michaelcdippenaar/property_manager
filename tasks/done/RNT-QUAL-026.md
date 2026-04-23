---
id: RNT-QUAL-026
stream: rentals
title: "Patch time.sleep in test_hub gotenberg unit tests to fix CI regression"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: testing
assigned_to: tester
depends_on: []
asana_gid: "1214197286171511"
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Backport the `@patch("time.sleep")` decorator to `test_hub/esigning/unit/test_gotenberg.py` so the retry-backoff path introduced by RNT-QUAL-002 does not add 7+ seconds of real sleep to every CI run.

## Acceptance criteria
- [x] `TestHtmlToPdf.test_raises_on_http_error` decorated with `@patch("apps.esigning.gotenberg.time.sleep")` (or equivalent patch path)
- [x] All other `TestHtmlToPdf` tests in `test_gotenberg.py` audited; any that exercise the retry path also patched
- [x] Total wall-clock runtime for `backend/apps/test_hub/esigning/unit/` remains under 2 seconds in CI
- [x] No test logic changed — only sleep patching added

## Files likely touched
- `backend/apps/test_hub/esigning/unit/test_gotenberg.py`

## Test plan
**Manual:**
- `cd backend && python -m pytest apps/test_hub/esigning/unit/test_gotenberg.py -v --tb=short` — must pass in under 2 seconds

**Automated:**
- CI `pytest` step for `test_hub/esigning/unit/` — runtime regression check

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-22 — Promoted from discovery `2026-04-22-gotenberg-test-hub-sleep-regression.md` found during RNT-QUAL-002 review. The fix was applied to `backend/apps/leases/tests/test_pdf_resilience.py` but not backported to the test_hub counterpart. Simple patch decorator addition only — no logic changes needed.

2026-04-23 — Audit of `test_gotenberg.py` confirmed the `@patch("apps.esigning.gotenberg.time.sleep")` decorator was already present on `test_raises_on_http_error` (lines 60-61). All other `TestHtmlToPdf` tests set `mock_response.ok = True` so they never reach the retry/sleep path — no additional patching needed. Ran `pytest apps/test_hub/esigning/unit/test_gotenberg.py --no-cov` locally: 10 passed in 0.05s, well within the 2-second threshold. No code changes required; task was already in the correct state.

2026-04-23 — Review passed. Independently verified: `@patch("apps.esigning.gotenberg.time.sleep")` present at lines 60-61 of `backend/apps/test_hub/esigning/unit/test_gotenberg.py`; all other `TestHtmlToPdf` tests use `ok=True` and bypass the retry path. Ran test suite locally: 10 passed in 0.07s. All four acceptance criteria satisfied. No code changes, no security surface, no POPIA concerns. Approved.
