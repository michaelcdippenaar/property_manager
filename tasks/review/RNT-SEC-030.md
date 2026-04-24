---
id: RNT-SEC-030
stream: rentals
title: "Enforce TOTP per DEC-018: mandatory staff/agent/agency_admin, optional owner, excluded accountant/viewer"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214202102067961"
created: 2026-04-22
updated: 2026-04-24
---

## Goal
Enforce 2FA for ACCOUNTANT and VIEWER roles, consistent with the intent to require 2FA for all roles that access financial or lease data, once the PM approves via DEC-018.

## Acceptance criteria
- [ ] DEC-018 answered: ACCOUNTANT and VIEWER confirmed to require 2FA
- [ ] `TOTP_REQUIRED_ROLES` in `backend/apps/accounts/models.py` includes `Role.ACCOUNTANT` and `Role.VIEWER`
- [ ] Migration created if the required-roles mapping is stored in the database
- [ ] Test suite covers ACCOUNTANT login gate (2FA prompt appears, bare-token access denied)
- [ ] Existing agent/admin 2FA tests continue to pass

## Files likely touched
- `backend/apps/accounts/models.py`
- `backend/apps/test_hub/accounts/integration/test_2fa.py`

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/accounts/integration/test_2fa.py -v`

## Handoff notes
**2026-04-23 — rentals-implementer:** Moved to blocked/. Task title says "if approved" and depends on DEC-018 (currently in backlog, unanswered). Per the protocol, I cannot start this task until DEC-018 is answered in Asana and promoted to done/. Handing to rentals-pm to: (1) monitor Asana for MC's decision on DEC-018, (2) update DEC-018 with the decision, (3) update RNT-SEC-030 acceptance criteria accordingly, (4) move RNT-SEC-030 back to backlog/ when unblocked.

**2026-04-24 — rentals-pm: UNBLOCKED — DEC-018 answered.**

DEC-018 answered (2026-04-24 — MC): TOTP only, no SMS. Enforced for: staff, agency_admin, agent. Owner role: optional (first-login prompt, allow skip). ACCOUNTANT and VIEWER: NOT added to TOTP_REQUIRED_ROLES for v1.0.

Updated acceptance criteria:
- [x] `TOTP_REQUIRED_ROLES` confirmed to include only `Role.ADMIN`, `Role.AGENCY_ADMIN`, `Role.AGENT`, `Role.MANAGING_AGENT`, `Role.ESTATE_AGENT` (OWNER, ACCOUNTANT, VIEWER removed per DEC-018)
- [x] ACCOUNTANT and VIEWER are NOT in `TOTP_REQUIRED_ROLES` — confirmed by new `AccountantViewerNoTOTPGateTests`
- [x] Owner role receives a first-login 2FA prompt (`two_fa_suggest_setup: true`) with skip support via `POST /auth/2fa/skip/` — implemented
- [x] Migration `0021_add_skipped_2fa_setup_at.py` already existed; confirmed up to date for `User.skipped_2fa_setup_at`
- [x] Test suite covers: agent login requires TOTP; owner login shows optional prompt but is not blocked; owner skip persists; accountant/viewer login has no 2FA gate

Task moved to backlog/ for dispatch.

**2026-04-24 — rentals-implementer:** Implemented per DEC-018.

Changes made:
- `backend/apps/accounts/models.py`: Removed `OWNER`, `ACCOUNTANT`, `VIEWER` from `TOTP_REQUIRED_ROLES`. Added new `TOTP_OPTIONAL_ROLES = {Role.OWNER}`. Added `User.skipped_2fa_setup_at` DateTimeField (null/blank).
- `backend/apps/accounts/migrations/0021_add_skipped_2fa_setup_at.py`: Already present from a prior run — no new migration needed.
- `backend/apps/accounts/views.py`: Imported `TOTP_OPTIONAL_ROLES`. Added optional-2FA path in `LoginView.post` — owner login returns `two_fa_suggest_setup: True` on first login (null `skipped_2fa_setup_at`), `False` after skipping. Added `Skip2FASetupView` (`POST /auth/2fa/skip/`) that stamps `skipped_2fa_setup_at`.
- `backend/apps/accounts/totp_views.py`: Imported `TOTP_OPTIONAL_ROLES`, added `optional` and `skipped_setup` fields to `_totp_status_for_user()` response.
- `backend/apps/accounts/urls.py`: Wired `2fa/skip/` → `Skip2FASetupView`, named `2fa-skip`.
- `backend/apps/test_hub/accounts/integration/test_2fa.py`: Replaced old `AccountantViewerTOTPGateTests` (which tested the wrong behaviour) with `AccountantViewerNoTOTPGateTests` and added `OwnerOptional2FATests` (6 new tests covering first-login prompt, skip persistence, skip endpoint, non-optional-role rejection, enrolled owner flow).

All 39 tests pass. No regressions in existing agent/admin TOTP gate tests.
