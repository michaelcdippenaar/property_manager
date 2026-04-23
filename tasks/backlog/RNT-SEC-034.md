---
id: RNT-SEC-034
stream: rentals
title: "Replace TOTP with pluggable OTP provider (email dev / SMS prod)"
feature: "two_factor_auth"
lifecycle_stage: null
priority: P0
effort: L
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: [DEC-019]
asana_gid: "1214227840418702"
created: 2026-04-23
updated: 2026-04-23
---

## Goal

Replace the current Google Authenticator TOTP second-factor with a settings-selectable OTP provider: email OTP for dev/staging (free), SMS OTP for production (gateway-backed), behind a clean `OTP_PROVIDER` env-var interface.

## Acceptance criteria

- [ ] `UserTOTP` and `TOTPRecoveryCode` models deprecated and removed (new migration); existing enrolled users are force-reset to OTP on next login.
- [ ] `backend/apps/accounts/otp/providers.py` defines a `BaseOTPProvider` interface and two concrete implementations: `EmailOTPProvider` and `SMSOTPProvider`.
- [ ] `OTP_PROVIDER` env var (`email` | `sms`) selects the active provider; defaults to `email` in `settings/development.py` and `sms` in `settings/production.py`.
- [ ] SMS provider decided in DEC-019 is integrated; credentials injected via env vars, never hardcoded.
- [ ] Login flow (`two_fa_token` JWT exchange endpoint) uses the selected provider — no TOTP logic remains.
- [ ] Google Authenticator QR-code enrol UI removed from admin portal; replaced with "Send code" + "Enter code" screens.
- [ ] Resend cooldown enforced (configurable, default 60 seconds between resends).
- [ ] Rate limits enforced: max resend attempts per user per hour; max failed verifications before temporary lockout (parameters from DEC-019 answer).
- [ ] Fallback behaviour (SMS → email or hard error) implemented per DEC-019 answer.
- [ ] Grace period / force-reset strategy for any existing TOTP-enrolled users implemented per DEC-019 answer.
- [ ] OTP code length and validity window configurable via settings (defaults: 6 digits, 5 minutes).
- [ ] Full test coverage: unit tests for both providers (email mock, SMS mock), integration tests for login 2FA exchange, rate-limit tests, lockout tests.
- [ ] `README` / `docs/auth.md` updated to document new OTP flow and env vars.

## Files likely touched

- `backend/apps/accounts/models.py` (deprecate/remove UserTOTP, TOTPRecoveryCode)
- `backend/apps/accounts/migrations/` (new migration removing TOTP models)
- `backend/apps/accounts/otp/__init__.py` (new)
- `backend/apps/accounts/otp/providers.py` (new: BaseOTPProvider, EmailOTPProvider, SMSOTPProvider)
- `backend/apps/accounts/otp/views.py` (new: send-code, verify-code endpoints)
- `backend/apps/accounts/auth_views.py` (2FA login exchange — swap TOTP check for provider call)
- `backend/apps/accounts/serializers.py` (remove TOTP serializers, add OTP serializers)
- `backend/apps/accounts/urls.py` (update routes)
- `backend/config/settings/base.py` (OTP_PROVIDER, OTP_LENGTH, OTP_VALIDITY_SECONDS, etc.)
- `backend/config/settings/development.py` (OTP_PROVIDER = 'email')
- `backend/config/settings/production.py` (OTP_PROVIDER = 'sms')
- `admin/src/views/auth/` (remove QR enrol screen, add SendOTP.vue + EnterOTP.vue)
- `backend/apps/accounts/tests/test_otp.py` (new)
- `backend/apps/accounts/tests/test_auth_views.py` (update 2FA tests)

## Test plan

**Manual:**
1. Dev: log in as any user with 2FA enabled → receive OTP by email → enter code → access granted.
2. Dev: request resend before cooldown expires → error shown.
3. Dev: enter wrong code N times → account temporarily locked.
4. Prod (staging with SMS provider): log in → receive SMS → enter code → access granted.
5. Confirm no TOTP QR enrol screen anywhere in admin portal.

**Automated:**
- `cd backend && pytest apps/accounts/tests/test_otp.py -v`
- `cd backend && pytest apps/accounts/tests/test_auth_views.py -v`

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-23 rentals-pm: Task authored. Blocked on DEC-019 — do not start implementation until MC answers OTP provider, budget, fallback, and grace period questions.
