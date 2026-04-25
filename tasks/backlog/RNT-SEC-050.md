---
id: RNT-SEC-050
stream: RNT-SEC
title: "Add email OTP as a login 2FA channel alongside TOTP"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214278001275994"
created: 2026-04-25
updated: 2026-04-25
---

## Goal

Extend the login 2FA flow to support email OTP as a user-selectable second factor alongside the existing TOTP path, using the already-built `OTPService` with its `email` channel.

## Acceptance criteria

- [ ] 1. New `two_fa_method` field on `User` model: enum choices `totp` (default) and `email`. Django migration included (`00XX_add_two_fa_method.py`).
- [ ] 2. New endpoint `POST /api/v1/auth/2fa/email-send/` — accepts the partial 2FA JWT, issues a 6-digit OTP via `OTPService(purpose="login_2fa")`, returns HTTP 200. Throttled via `OTPSendThrottle`.
- [ ] 3. New endpoint `POST /api/v1/auth/2fa/email-verify/` — accepts partial 2FA JWT + 6-digit code, verifies via `OTPService.verify(...)`, returns full `access` + `refresh` JWT pair on success. Reuses the `_make_two_fa_token` pattern from `totp_views.py`.
- [ ] 4. `LoginView` in `views.py` branches on `user.two_fa_method`: `email` path returns partial token with `"next": "email-verify"` hint in the response body; `totp` path is unchanged.
- [ ] 5. New Vue view `admin/src/views/auth/EmailOtpVerifyView.vue` mirroring `TotpVerifyView.vue`. Router branches on the `next` hint returned from login.
- [ ] 6. Settings preference UI: admin user settings security tab exposes a toggle to switch `two_fa_method` between `totp` and `email`. Backed by a writable `two_fa_method` field on `UserSerializer`.
- [ ] 7. Pytest test file `backend/apps/accounts/tests/test_email_2fa.py` covering: happy path for both new endpoints, bad code, expired code, and throttle-hit scenarios. Vue unit test for `EmailOtpVerifyView.vue`.
- [ ] 8. Audit log entries emitted: `2fa_email_sent` (on successful send), `2fa_email_verified` (on successful verify), `2fa_email_failed` (on bad/expired code or throttle).

## Files likely touched

- `backend/apps/accounts/models.py` — add `two_fa_method` field
- `backend/apps/accounts/migrations/00XX_add_two_fa_method.py` — new migration
- `backend/apps/accounts/views.py` — `LoginView` branch on `two_fa_method`
- `backend/apps/accounts/totp_views.py` — factor out `_make_two_fa_token` as shared helper if not already importable
- `backend/apps/accounts/email_2fa_views.py` — new file: `Email2FASendView`, `Email2FAVerifyView`
- `backend/apps/accounts/serializers.py` — expose `two_fa_method` as writable on `UserSerializer`
- `backend/apps/accounts/urls.py` — register two new routes
- `backend/apps/accounts/tests/test_email_2fa.py` — new test file
- `admin/src/views/auth/EmailOtpVerifyView.vue` — new view
- `admin/src/router/index.ts` — add route, branch logic on `next` hint
- `admin/src/views/settings/SecurityTab.vue` — `two_fa_method` toggle UI
- `admin/src/api/auth.ts` — `sendEmailOtp()` and `verifyEmailOtp()` methods

## Test plan

**Manual:**
- Log in as a user with `two_fa_method = email`; confirm 2FA code email is received and login completes successfully.
- Log in as a user with `two_fa_method = totp`; confirm existing TOTP flow is unchanged.
- Submit a wrong code at `/auth/2fa/email-verify/`; confirm 400 + `2fa_email_failed` audit entry.
- Submit an expired code (wait >300 s or manually expire in DB); confirm 400 error.
- Hit `/auth/2fa/email-send/` 6 times within an hour; confirm throttle (429) kicks in.
- Toggle `two_fa_method` in settings UI; confirm subsequent logins use the new method.

**Automated:**
- `cd backend && pytest apps/accounts/tests/test_email_2fa.py -v`
- Vue unit: `pnpm --filter admin test EmailOtpVerifyView`

## Handoff notes

(Each agent appends a dated entry here on handoff. Do not edit prior entries.)
