---
id: RNT-SEC-040
stream: rentals
title: "Remove OTP code from email subject line — POPIA minimum-necessity fix"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214235771718649"
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Stop leaking the plaintext OTP code into the email subject line, which exposes it to SMTP relay logs, SES CloudWatch logs, and push-notification caches — violating POPIA minimum-necessary disclosure.

## Acceptance criteria
- [x] Subject in `backend/apps/accounts/otp/channels/email.py` changed to a generic string, e.g. `"Your Klikk verification code"` (no `{code}` interpolated)
- [x] OTP code remains in the email body only
- [x] Test updated to assert `code` is NOT present in `msg.subject`
- [x] Test asserts `code` IS present in `msg.body`

## Files likely touched
- `backend/apps/accounts/otp/channels/email.py` (line 26)
- `backend/apps/accounts/tests/test_otp.py` (or wherever the email channel test lives)

## Test plan
**Manual:**
- Trigger OTP send → check received email subject does not contain the numeric code

**Automated:**
- `cd backend && pytest apps/accounts/tests/ -k otp -v`

## Handoff notes
2026-04-23: Promoted from discovery `2026-04-23-otp-code-in-email-subject.md` (found during RNT-021). `EmailChannel.send` at `email.py:26` builds subject as `f"Your Klikk verification code: {code}"`. POPIA s23 minimum-necessity: authentication credentials should not be in relay-accessible metadata. Quick fix — two lines of code + one test assertion.

2026-04-23 (implementer): Changed `email.py:30` subject from `f"Your Klikk verification code: {code}"` to the static string `"Your Klikk verification code"`. Replaced `test_email_subject_contains_code` with two new tests: `test_email_subject_does_not_contain_code` (asserts code absent from subject, per POPIA) and `test_email_subject_is_generic` (asserts generic wording present). Existing `test_email_body_contains_code` confirms code is still delivered in the body. All 12 tests in `test_otp_email_channel.py` pass; 3 ERRORs are a pre-existing duplicate test-database conflict from a concurrent session and are unrelated to this change.
