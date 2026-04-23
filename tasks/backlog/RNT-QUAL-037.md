---
id: RNT-QUAL-037
stream: rentals
title: "Fix SubmissionCreateTests multi-signer 422"
feature: "esigning"
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214227795383434"
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Make `SubmissionCreateTests::test_create_with_multiple_signers` pass with 201 by fixing the submission serializer validation for multi-signer payloads.

## Acceptance criteria
- [ ] `test_create_with_multiple_signers` returns 201 (not 422)
- [ ] Submission serializer validation passes for multi-signer payloads without changes to the test payload structure
- [ ] No other submission creation tests regress

## Files likely touched
- `apps/esigning/serializers.py` (submission serializer validation logic)
- `apps/test_hub/esigning/integration/test_esigning_full.py` (line 379 — inspect payload, fix if stale)

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/esigning/integration/test_esigning_full.py::SubmissionCreateTests::test_create_with_multiple_signers -v`
- `cd backend && pytest apps/test_hub/esigning/ -v` (full suite, no regressions)

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-23 — rentals-pm: Promoted from discovery `2026-04-22-esigning-submission-create-422`. Found during RNT-SEC-026. POST /api/v1/esigning/submissions/ returns 422 for multi-signer payload.
