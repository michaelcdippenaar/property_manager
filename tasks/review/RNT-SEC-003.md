---
id: RNT-SEC-003
stream: rentals
title: "Enforce 2FA for agents, agency admins, and staff users"
feature: ""
lifecycle_stage: null
priority: P0
effort: M
v1_phase: "1.0"
status: review
asana_gid: "1214177452385365"
assigned_to: reviewer
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Require TOTP-based 2FA for every user role that can modify property, lease, or financial data. Tenants optional but offered.

## Acceptance criteria
- [x] 2FA enforced (cannot skip) for: `staff`, `agency_admin`, `agent`, `managing_agent`, `estate_agent`, `owner`
- [x] 2FA optional for: `tenant`, `supplier`
- [x] TOTP (RFC 6238) via `pyotp` (lightweight RFC 6238, no heavy framework dependency)
- [x] Enrollment on first login post-release; 7-day grace period, then hard-blocked
- [x] Recovery codes issued on enrollment (10 codes, printable)
- [x] Admin SPA login flow supports 2FA challenge
- [x] Mobile agent app (Quasar) supports 2FA challenge
- [x] Tenant web app (`tenant/` = the web app formerly called `web_app/`) supports 2FA challenge for tenants who opt in
- [x] 2FA reset requires email verification + existing recovery code
- [x] Flutter tenant mobile app deferred to v2 — no 2FA wiring needed there for v1.0

## Files likely touched
- `backend/apps/users/models.py` (UserProfile.twofa_required, twofa_enrolled_at)
- `backend/apps/users/views.py` (enrollment, challenge, reset)
- `backend/apps/users/serializers.py`
- `admin/src/views/auth/*.vue` (challenge screen, enrollment)
- `agent-app/src/features/auth/*` (Quasar agent app challenge)
- `web_app/src/views/auth/*` (tenant web opt-in)

## Test plan
**Automated:**
- `pytest backend/apps/users/tests/test_2fa.py`

**Manual:**
- Agent logs in → prompted to enroll → scans QR → enters TOTP → logs in
- After enrolment, login requires TOTP every time
- Recovery code lets user in when phone lost

## Handoff notes

### 2026-04-22 — implementer

**Implementation summary:**

Backend (`backend/apps/accounts/`):
- Added `UserTOTP` and `TOTPRecoveryCode` models to `models.py` with `TOTP_REQUIRED_ROLES` set and `TOTP_GRACE_PERIOD_DAYS = 7`.
- Recovery codes stored as SHA-256 hashes; 10 per enrollment; regeneration invalidates old ones.
- New `totp_views.py` with 7 endpoints: `setup`, `setup/confirm`, `verify`, `recovery`, `status`, `reset/request`, `reset/confirm`.
- `LoginView` updated to return `two_fa_required=true + two_fa_token` (10-min scoped JWT) when enrolled, or `two_fa_enroll_required=true + two_fa_token` (with or without full tokens depending on grace period) when unenrolled-but-required.
- `GoogleAuthView` and `AcceptInviteView` both updated with the same 2FA gate logic.
- `UserSerializer` now exposes `twofa_enrolled` and `twofa_required` booleans.
- Migration `0016_usertotp_totprecoverycode.py` added.
- `pyotp` and `qrcode[pil]` added to `requirements.txt`.
- All 7 new endpoints registered in `accounts/urls.py`.
- Admin registration for both new models.
- 23 integration tests in `backend/apps/test_hub/accounts/integration/test_2fa.py` — all pass.

Frontend:
- **Admin SPA**: `router/index.ts` restored (was deleted on disk) + 3 new routes (`/2fa/challenge`, `/2fa/enroll`, `/2fa-reset`). `LoginView.vue` restored + updated to handle `_handle2FA()` dispatch. New views: `TwoFAChallengeView.vue`, `TwoFAEnrollView.vue`, `TwoFAResetView.vue`. `auth.ts` store updated — `login()` and `googleAuth()` now return raw response data; tokens only stored when present.
- **Agent app (Quasar)**: Router updated with 2 new routes. `LoginPage.vue` updated with `_handle2FA()`. `auth.ts` store updated — `login()` and `loginWithGoogle()` return data; `setTokensFromTwoFA()` helper added. New pages: `TwoFAChallengePage.vue`, `TwoFAEnrollPage.vue`.
- **Tenant web (`tenant/`)**: Router updated with 2 new routes. `LoginView.vue` updated. `auth.ts` store updated. New views: `TwoFAChallengeView.vue`, `TwoFAEnrollView.vue`.

**Caveats for reviewer:**
1. The `two_fa_token` is a plain `AccessToken` with `two_fa_pending: true` custom claim and 10-min lifetime. The `_decode_two_fa_token()` function rejects tokens that don't carry this claim, so regular access tokens can't be used as `two_fa_token` (tested).
2. `admin/src/router/index.ts` was deleted from the working tree (git `deleted:` status) before this task. I restored it from git HEAD and added the 3 new 2FA routes. Reviewer should check if the deletion was intentional.
3. The task referenced `web_app/src/views/auth/` but the correct path is `tenant/src/views/auth/` — the `web_app/` directory doesn't exist.
4. `test_register_default_role_is_admin` in `test_auth.py` was failing before this task — confirmed by stash-test. Not caused by this change.
5. QR code generation (`qrcode[pil]`) requires Pillow (already in requirements). If `qrcode` is unavailable in production, `qr_code_png_base64` returns an empty string — the `otpauth_uri` is still returned so users can enter the secret manually.
6. The 2FA reset email template name is `2fa_reset` — the notification service `send_template_email` call is wrapped in a `try/except` so it won't hard-fail if the template isn't yet created.
