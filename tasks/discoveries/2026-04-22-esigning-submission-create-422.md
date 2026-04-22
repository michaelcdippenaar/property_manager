---
discovered_by: rentals-tester
discovered_during: RNT-SEC-026
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found
`SubmissionCreateTests::test_create_with_multiple_signers` in `apps/test_hub/esigning/integration/test_esigning_full.py` is returning 422 Unprocessable Content instead of 201. The e-signing submission creation endpoint is rejecting the test payload.

## Why it matters
Multi-signer e-signing submission creation may be broken, which would affect the core signing workflow.

## Where I saw it
- `apps/test_hub/esigning/integration/test_esigning_full.py:379`
- `POST /api/v1/esigning/submissions/` returning 422

## Suggested acceptance criteria (rough)
- [ ] `test_create_with_multiple_signers` passes with 201
- [ ] Submission serializer validation passes for multi-signer payloads

## Why I didn't fix it in the current task
Out of scope. This task covers IP extraction utility only.
