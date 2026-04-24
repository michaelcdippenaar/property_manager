---
id: RNT-SEC-030
stream: rentals
title: "Add ACCOUNTANT and VIEWER roles to TOTP_REQUIRED_ROLES if approved"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
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

**2026-04-24 — rentals-pm: UNBLOCKED — DEC-018 answered.**

DEC-018 answered (2026-04-24 — MC): TOTP only, no SMS. Enforced for: staff, agency_admin, agent. Owner role: optional (first-login prompt, allow skip). ACCOUNTANT and VIEWER: NOT added to TOTP_REQUIRED_ROLES for v1.0.

Updated acceptance criteria:
- [ ] `TOTP_REQUIRED_ROLES` confirmed to include only `Role.STAFF`, `Role.AGENCY_ADMIN`, `Role.AGENT` (already implemented in RNT-SEC-003 — verify no regression)
- [ ] ACCOUNTANT and VIEWER are NOT in `TOTP_REQUIRED_ROLES` — no change needed, confirm by test
- [ ] Owner role receives a first-login 2FA prompt ("We recommend enabling 2FA") with a "Skip for now" option — implement if not already present
- [ ] No migration required for ACCOUNTANT/VIEWER exclusion
- [ ] Test suite covers: agent login requires TOTP; owner login shows optional prompt but is not blocked; accountant/viewer login has no 2FA gate

Task moved to backlog/ for dispatch.
