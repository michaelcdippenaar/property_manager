---
discovered_by: rentals-reviewer
discovered_during: RNT-001
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found
`_notify_staff` and `_email_signed_copy_to_signers` in `backend/apps/esigning/webhooks.py` receive the `ESigningSubmission` object from webhook dispatch code that does not call `select_related("lease__unit__property", "mandate__property")`. The helper functions now access `submission.mandate.property` (post RNT-001 fix), triggering additional DB queries per invocation.

## Why it matters
For mandate completions these helpers are called back-to-back inside `handle_signing_complete`. Without prefetched relations each call hits the DB for `mandate` and then `property`. Low traffic now but will cause N+1 churn as mandate volume grows, and it's easy to fix.

## Where I saw it
- `backend/apps/esigning/webhooks.py` — `_notify_staff` (~line 297) and `_email_signed_copy_to_signers` (~line 373) both access `submission.mandate.property`
- The `esigning_submissions_for_user` helper in `views.py` already does `select_related("lease__unit__property", "mandate__property")`, but `handle_signing_complete` fetches the submission via a different queryset that lacks these relations.

## Suggested acceptance criteria (rough)
- [ ] `handle_signing_complete` (or its queryset fetch) adds `select_related("lease__unit__property", "mandate__property")` before dispatching to helpers
- [ ] Unit test confirms no extra queries fired when processing a mandate completion event (use `django.test.utils.override_settings` or `assertNumQueries`)

## Why I didn't fix it in the current task
Out of scope for RNT-001 (functional bug fixes only). No functional breakage — performance/query efficiency concern only.
