---
id: RNT-SEC-048
stream: rentals-security
title: "Add throttle_classes to ChangePasswordView (brute-force / takeover risk)"
feature: ""
lifecycle_stage: null
priority: P0
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214273972208295"
created: 2026-04-24
updated: 2026-04-24
---

## Goal

Rate-limit `ChangePasswordView` so an attacker holding a short-lived access token cannot brute-force `current_password` to take over the account permanently.

## Acceptance criteria

- [ ] `ChangePasswordView` has `throttle_classes` set (e.g. `AuthAnonThrottle` or a dedicated `PasswordChangeThrottle` keyed per user).
- [ ] Throttle is consistent with the pattern used by `LoginView`, `OTPSendView`, `OTPVerifyView`, `PasswordResetRequestView`, `PasswordResetConfirmView`, and `AcceptInviteView` in the same file.
- [ ] A test confirms a 429 is returned after the threshold is exceeded.
- [ ] The Google-OAuth branch (`has_usable_password() is False`) is not affected by this change.

## Files likely touched

- `backend/apps/accounts/views.py` (line 361 — `ChangePasswordView`)
- `backend/apps/accounts/tests/` (throttle test)

## Test plan

**Manual:**
- POST `/api/v1/accounts/change-password/` with wrong `current_password` more than the throttle limit; expect 429 on subsequent attempts.

**Automated:**
- `cd backend && pytest apps/accounts/tests/ -k change_password`

## Handoff notes

Promoted from discovery `2026-04-24-change-password-no-throttle.md` (2026-04-24). P0 — auth surface, account takeover risk.
