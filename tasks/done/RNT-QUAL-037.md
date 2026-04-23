---
id: RNT-QUAL-037
stream: rentals
title: "Fix SubmissionCreateTests multi-signer 422"
feature: "esigning"
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: testing
assigned_to: tester
depends_on: []
asana_gid: "1214227795383434"
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Make `SubmissionCreateTests::test_create_with_multiple_signers` pass with 201 by fixing the submission serializer validation for multi-signer payloads.

## Acceptance criteria
- [x] `test_create_with_multiple_signers` returns 201 (not 422)
- [x] Submission serializer validation passes for multi-signer payloads without changes to the test payload structure
- [x] No other submission creation tests regress

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

2026-04-23 — implementer: Root cause was not serializer validation but the RHA compliance gate in the view. The view calls `run_rha_checks(lease)` and raises 422 if blocking flags exist. Test leases created without `primary_tenant` always trigger `MISSING_PRIMARY_TENANT` (blocking). Fixed by adding `primary_tenant=self.create_person(...)` in the `setUp` of `SubmissionCreateTests` (test_esigning_full.py). The same pattern was found in `ESigningListCreateTests` and `SequentialSigningTests` in test_esigning.py — those were also already failing with 422; fixed as an in-scope sub-issue since the change is identical and trivial (<5 min). Full esigning suite: 237 passed, 3 xfailed, 0 failures. No production code changed — fix is test infrastructure only.

2026-04-23 — reviewer: Review passed. Verified root cause (RHA gate blocks on missing primary_tenant_id — rha_check.py:66-72, severity=blocking). create_lease() already accepted primary_tenant as a first-class parameter (test_case.py:145). Fix is test-infrastructure only — identical 3-line setUp change across SubmissionCreateTests (test_esigning_full.py), ESigningListCreateTests, and SequentialSigningTests (test_esigning.py). No production code modified. In-scope extension to other two classes justified and low-risk. All AC met. No security or POPIA surface. Promoted to testing.
