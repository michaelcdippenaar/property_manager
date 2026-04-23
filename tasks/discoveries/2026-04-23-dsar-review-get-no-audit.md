---
discovered_by: rentals-reviewer
discovered_during: RNT-SEC-041
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-SEC
---

## What I found
The new `GET /api/v1/popia/dsar-queue/<id>/review/` endpoint (introduced in RNT-SEC-041) reads retention flags for RTBF requests but does not emit an `_log_audit` entry. The existing `POST` approve/deny branches do log.

## Why it matters
POPIA s24/PAIA expect a trail of who accessed a data subject's profile info — retention flags are a proxy for "does this user have lease/payment records" and reading them repeatedly by an operator leaves no audit trace. Low severity (admin/agency_admin only) but asymmetric with the POST paths.

## Where I saw it
- `backend/apps/popia/views.py:393-406` (DSARReviewView.get)
- Compare with `_log_audit("popia.dsar_approved", ...)` at line 437

## Suggested acceptance criteria (rough)
- [ ] GET DSARReviewView emits `popia.dsar_review_opened` audit event with `{dsar_id, request_type, retention_flags_computed: bool}`
- [ ] No PII in the payload (don't log flag values beyond computed/not-computed)

## Why I didn't fix it in the current task
Out of scope — RNT-SEC-041 is strictly a UI guardrail; audit coverage of read paths is a separate hardening item.
