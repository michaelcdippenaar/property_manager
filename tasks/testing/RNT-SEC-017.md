---
id: RNT-SEC-017
stream: rentals
title: "Add ACCOUNTANT and VIEWER roles to TOTP_REQUIRED_ROLES"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: testing
assigned_to: tester
depends_on: []
asana_gid: null
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Require TOTP 2FA for ACCOUNTANT and VIEWER roles, consistent with the intent of RNT-SEC-003 to protect all roles that can access financial or lease data.

## Acceptance criteria
- [x] `TOTP_REQUIRED_ROLES` in `backend/apps/accounts/models.py` includes `Role.ACCOUNTANT` and `Role.VIEWER`
- [x] If the role-to-required mapping is stored in the database, a migration is provided — N/A: `TOTP_REQUIRED_ROLES` is a Python set constant, no DB migration needed
- [x] Test suite updated to cover ACCOUNTANT login gate (login without TOTP → 403; login with TOTP → 200)
- [x] VIEWER login gate tested similarly
- [x] No regressions for existing TOTP-required roles

## Files likely touched
- `backend/apps/accounts/models.py` (line 435, `TOTP_REQUIRED_ROLES`)
- `backend/apps/test_hub/accounts/` (TOTP tests for new roles)
- `backend/apps/accounts/migrations/` (if DB migration needed)

## Test plan
**Manual:**
- Log in as ACCOUNTANT without TOTP configured → should be required to set up TOTP before accessing the app
- Log in as ACCOUNTANT with TOTP → normal access

**Automated:**
- `cd backend && pytest apps/test_hub/accounts/ -k totp -v`

## Handoff notes
Promoted from discovery: `2026-04-22-totp-accountant-viewer-roles.md` (RNT-SEC-003). Accountants have access to financial data (rent rolls, payment records); omitting them from TOTP requirement is inconsistent with RNT-SEC-003 intent.

**2026-04-23 — implementer**
- Added `User.Role.ACCOUNTANT` and `User.Role.VIEWER` to `TOTP_REQUIRED_ROLES` set in `backend/apps/accounts/models.py` (line 439).
- No DB migration needed: `TOTP_REQUIRED_ROLES` is a Python set constant, not persisted to the database.
- Added `AccountantViewerTOTPGateTests` class to `backend/apps/test_hub/accounts/integration/test_2fa.py` with 8 tests covering both roles across in-grace, past-grace (hard-blocked), enrolled (two_fa_required), and successful TOTP verify flows.
- All 37 tests in the 2FA suite pass (0 regressions).

**2026-04-23 — reviewer (approved)**
1. `TOTP_REQUIRED_ROLES` in `backend/apps/accounts/models.py` lines 446-447 confirmed: `User.Role.ACCOUNTANT` and `User.Role.VIEWER` both present.
2. 8 new tests in `AccountantViewerTOTPGateTests` cover all four branches per role: in-grace (access + enroll flag), past-grace (hard-blocked, no access token), enrolled (two_fa_required + two_fa_token, no access), and full TOTP verify flow (access + refresh tokens issued). Test structure mirrors existing `LoginTwoFAGateTests` — consistent with codebase conventions.
3. No DB migration required — confirmed `TOTP_REQUIRED_ROLES` is a Python set constant.
4. Security pass: no new endpoints introduced; change is purely additive to the set constant; no raw SQL, no PII logged, no secrets. Auth gate logic not modified — only the membership set widens.
5. No regressions flagged — implementer reports all 37 2FA suite tests pass.

Review passed.
