---
discovered_by: rentals-reviewer
discovered_during: RNT-SEC-003
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT-SEC
---

## What I found
`TOTP_REQUIRED_ROLES` in `backend/apps/accounts/models.py` does not include `Role.ACCOUNTANT` or `Role.VIEWER`. Both roles exist in the User model and can be granted access to financial/lease data through the admin SPA.

## Why it matters
Accountants in particular have access to financial data (rent rolls, payment records). If those accounts are compromised, financial data is at risk without 2FA. Omitting them is inconsistent with the intent of RNT-SEC-003 to require 2FA for "every user role that can modify property, lease, or financial data."

## Where I saw it
- `backend/apps/accounts/models.py:32` — Role definitions (ACCOUNTANT, VIEWER present)
- `backend/apps/accounts/models.py:435` — TOTP_REQUIRED_ROLES (ACCOUNTANT, VIEWER absent)

## Suggested acceptance criteria (rough)
- [ ] Confirm whether ACCOUNTANT and VIEWER roles should be in TOTP_REQUIRED_ROLES (PM decision)
- [ ] If yes, add them and add a migration if role-to-required mapping is stored on the model
- [ ] Update test suite to cover ACCOUNTANT login gate

## Why I didn't fix it in the current task
Out of scope for RNT-SEC-003; requires a PM decision on whether ACCOUNTANT/VIEWER warrant mandatory 2FA. The current task's acceptance criteria does not list these roles explicitly.
