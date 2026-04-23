---
id: RNT-SEC-030
stream: rentals
title: "Add ACCOUNTANT and VIEWER roles to TOTP_REQUIRED_ROLES if approved"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: blocked
assigned_to: rentals-pm
depends_on: [DEC-018]
asana_gid: "1214202102067961"
created: 2026-04-22
updated: 2026-04-23
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
