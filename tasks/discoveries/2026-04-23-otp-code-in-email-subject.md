---
discovered_by: rentals-reviewer
discovered_during: RNT-021
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-SEC
---

## What I found

`EmailChannel.send` in `backend/apps/accounts/otp/channels/email.py` puts the plaintext OTP code directly in the email subject line: `f"Your Klikk verification code: {code}"`. The code also appears in the body, which is expected — but the subject leaks it to SMTP relay access logs, email server headers, and email client notification previews.

## Why it matters

Any party with access to email infrastructure logs (relay, SES CloudWatch logs, email client push-notification caches) can read the OTP without opening the message body. POPIA requires minimum necessary disclosure of authentication credentials.

## Where I saw it

- `backend/apps/accounts/otp/channels/email.py:26`

## Suggested acceptance criteria (rough)

- [ ] Subject changed to a generic string, e.g. "Your Klikk verification code" (no code in subject)
- [ ] OTP code remains prominent in the email body only
- [ ] Test updated to assert code is NOT in `msg.subject`

## Why I didn't fix it in the current task

Out of scope — the current task AC does not specify subject content, and changing the subject would alter the email channel and its test, doubling the review surface.
