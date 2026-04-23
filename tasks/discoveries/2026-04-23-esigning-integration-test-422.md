---
discovered_by: rentals-implementer
discovered_during: RNT-QUAL-032
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found

8 esigning integration tests in `test_esigning.py` and `test_esigning_full.py` fail consistently across the full suite with `422 != 201` — the submission create endpoint is returning HTTP 422 (Unprocessable Entity) instead of 201 (Created).

## Why it matters

These are integration tests covering the core e-signing submission creation flow (including sequential signing, parallel mode, multiple signers, and initials fields). Their consistent failure means the creation endpoint has a validation regression. Any QA run or CI pipeline that includes `apps/test_hub/esigning/` will report 8 failures that are unrelated to the current task.

## Where I saw it

- `backend/apps/test_hub/esigning/integration/test_esigning.py::ESigningListCreateTests::test_create_success`
- `backend/apps/test_hub/esigning/integration/test_esigning.py::ESigningListCreateTests::test_docuseal_error`
- `backend/apps/test_hub/esigning/integration/test_esigning.py::SequentialSigningTests::test_create_parallel_mode`
- `backend/apps/test_hub/esigning/integration/test_esigning.py::SequentialSigningTests::test_create_sequential_default`
- `backend/apps/test_hub/esigning/integration/test_esigning.py::SequentialSigningTests::test_sequential_signer_order_preserved`
- `backend/apps/test_hub/esigning/integration/test_esigning.py::SequentialSigningTests::test_sequential_three_signers_create`
- `backend/apps/test_hub/esigning/integration/test_esigning_full.py::SubmissionCreateTests::test_create_generates_initials_fields`
- `backend/apps/test_hub/esigning/integration/test_esigning_full.py::SubmissionCreateTests::test_create_with_multiple_signers`

## Suggested acceptance criteria (rough)

- [ ] All 8 tests pass in the full esigning suite run
- [ ] The `/api/v1/esigning/submissions/` POST endpoint accepts valid create payloads and returns 201
- [ ] Root cause of 422 identified (likely a serializer validation change or required field added without test fixture update)

## Why I didn't fix it in the current task

Out of scope — RNT-QUAL-032 is strictly about throttle cache isolation. Fixing the 422 regression would require investigating the esigning submission serializer and test fixtures, which doubles the diff and crosses into a separate concern.
