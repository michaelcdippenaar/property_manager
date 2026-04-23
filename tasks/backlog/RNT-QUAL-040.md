---
id: RNT-QUAL-040
stream: rentals
title: "Fix e-signing submission create endpoint returning 422 instead of 201 (8 integration test failures)"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214229833048160"
created: 2026-04-23
updated: 2026-04-23
---

## Goal

Restore the e-signing submission create endpoint to return HTTP 201 so that the 8 consistently-failing integration tests in `test_esigning.py` and `test_esigning_full.py` pass again.

## Acceptance criteria
- [ ] `POST /api/v1/esigning/submissions/` with a valid create payload returns 201 (not 422)
- [ ] Root cause of 422 identified — likely a serializer validation change or a required field added without updating test fixtures
- [ ] All 8 previously-failing tests pass:
  - `ESigningListCreateTests::test_create_success`
  - `ESigningListCreateTests::test_docuseal_error`
  - `SequentialSigningTests::test_create_parallel_mode`
  - `SequentialSigningTests::test_create_sequential_default`
  - `SequentialSigningTests::test_sequential_signer_order_preserved`
  - `SequentialSigningTests::test_sequential_three_signers_create`
  - `SubmissionCreateTests::test_create_generates_initials_fields`
  - `SubmissionCreateTests::test_create_with_multiple_signers`
- [ ] Full esigning integration suite passes with no regressions

## Files likely touched
- `backend/apps/esigning/serializers.py` (or equivalent submission create serializer)
- `backend/apps/test_hub/esigning/integration/test_esigning.py`
- `backend/apps/test_hub/esigning/integration/test_esigning_full.py`
- Any fixture files used by the esigning tests

## Test plan
**Manual:**
- `POST /api/v1/esigning/submissions/` with a minimal valid payload — expect 201

**Automated:**
- `cd backend && pytest apps/test_hub/esigning/integration/ -v` — all 8 tests must be green

## Handoff notes
(2026-04-23 rentals-pm) Promoted from discovery `2026-04-23-esigning-integration-test-422.md`. Discovered during RNT-QUAL-032 (throttle cache isolation) — failures are pre-existing and unrelated to that task. Likely a serializer validation change introduced without updating test fixtures.
