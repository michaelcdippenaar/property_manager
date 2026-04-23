---
id: RNT-SEC-017
stream: rentals
title: "Add ACCOUNTANT and VIEWER roles to TOTP_REQUIRED_ROLES"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: null
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Require TOTP 2FA for ACCOUNTANT and VIEWER roles, consistent with the intent of RNT-SEC-003 to protect all roles that can access financial or lease data.

## Acceptance criteria
- [ ] `TOTP_REQUIRED_ROLES` in `backend/apps/accounts/models.py` includes `Role.ACCOUNTANT` and `Role.VIEWER`
- [ ] If the role-to-required mapping is stored in the database, a migration is provided
- [ ] Test suite updated to cover ACCOUNTANT login gate (login without TOTP → 403; login with TOTP → 200)
- [ ] VIEWER login gate tested similarly
- [ ] No regressions for existing TOTP-required roles

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
