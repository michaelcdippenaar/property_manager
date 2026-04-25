---
id: RNT-SEC-048
stream: rentals-security
title: "Add throttle_classes to ChangePasswordView (brute-force / takeover risk)"
feature: ""
lifecycle_stage: null
priority: P0
effort: S
v1_phase: "1.0"
status: testing
assigned_to: tester
depends_on: []
asana_gid: "1214273972208295"
created: 2026-04-24
updated: 2026-04-24
---

## Goal

Rate-limit `ChangePasswordView` so an attacker holding a short-lived access token cannot brute-force `current_password` to take over the account permanently.

## Acceptance criteria

- [x] `ChangePasswordView` has `throttle_classes` set (e.g. `AuthAnonThrottle` or a dedicated `PasswordChangeThrottle` keyed per user).
- [x] Throttle is consistent with the pattern used by `LoginView`, `OTPSendView`, `OTPVerifyView`, `PasswordResetRequestView`, `PasswordResetConfirmView`, and `AcceptInviteView` in the same file.
- [x] A test confirms a 429 is returned after the threshold is exceeded.
- [x] The Google-OAuth branch (`has_usable_password() is False`) is not affected by this change.

## Files likely touched

- `backend/apps/accounts/views.py` (line 361 -- `ChangePasswordView`)
- `backend/apps/accounts/tests/` (throttle test)

## Test plan

**Manual:**
- POST `/api/v1/auth/change-password/` with wrong `current_password` more than the throttle limit; expect 429 on subsequent attempts.

**Automated:**
- `cd backend && pytest apps/accounts/tests/test_change_password.py -v`

## Handoff notes

Promoted from discovery `2026-04-24-change-password-no-throttle.md` (2026-04-24). P0 -- auth surface, account takeover risk.

### 2026-04-24 -- implementer

Added `PasswordChangeThrottle(SimpleRateThrottle)` to `backend/apps/accounts/throttles.py`, keyed on `request.user.pk` at `password_change` scope (5/min configured in `DEFAULT_THROTTLE_RATES`). Wired to `ChangePasswordView.throttle_classes`. Rate added to `backend/config/settings/base.py`. Two pytest tests in `backend/apps/accounts/tests/test_change_password.py` pass: (1) 429 on the 4th call at 3/min; (2) OAuth branch returns 200. Tests patch `SimpleRateThrottle.THROTTLE_RATES` directly to avoid import-order issues (same pattern as `test_rate_limits.py`).
### 2026-04-24 -- reviewer

Review passed. Checked: (1) throttle keyed on user.pk not IP; (2) 5/min rate consistent with sibling scopes; (3) both pytest tests green (2 passed); (4) OAuth branch 200 confirmed by test. No PII logged, no raw SQL, unauthenticated requests return None key (safe). Pattern matches LoginHourlyThrottle exactly. Approved.
