---
id: RNT-QUAL-026
stream: rentals
title: "Patch time.sleep in test_hub gotenberg unit tests to fix CI regression"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214197286171511"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Backport the `@patch("time.sleep")` decorator to `test_hub/esigning/unit/test_gotenberg.py` so the retry-backoff path introduced by RNT-QUAL-002 does not add 7+ seconds of real sleep to every CI run.

## Acceptance criteria
- [ ] `TestHtmlToPdf.test_raises_on_http_error` decorated with `@patch("apps.esigning.gotenberg.time.sleep")` (or equivalent patch path)
- [ ] All other `TestHtmlToPdf` tests in `test_gotenberg.py` audited; any that exercise the retry path also patched
- [ ] Total wall-clock runtime for `backend/apps/test_hub/esigning/unit/` remains under 2 seconds in CI
- [ ] No test logic changed — only sleep patching added

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
