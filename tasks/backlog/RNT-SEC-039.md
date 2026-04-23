---
id: RNT-SEC-039
stream: rentals
title: "Audit log hardening: RBAC regression tests + AuditContextMiddleware for signal-triggered events"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214237326490411"
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Close two residual gaps from RNT-SEC-008: add RBAC regression tests for the audit endpoints, and introduce a thread-local context middleware so signal-triggered audit events carry actor/IP/user-agent attribution.

## Acceptance criteria
- [ ] `APIClient` tests in `backend/apps/audit/tests/test_audit_chain.py` assert 200 for `admin`/`agency_admin` and 403 for `agent`, `estate_agent`, `managing_agent`, `tenant`, `landlord`, `supplier` against both `GET /api/v1/audit/events/` and `GET /api/v1/audit/timeline/.../`
- [ ] `apps.audit.middleware.AuditContextMiddleware` stashes `request.user`, `REMOTE_ADDR`, `HTTP_USER_AGENT` into thread-local storage for the duration of each request
- [ ] `_write_event` in `backend/apps/audit/signals.py` reads from the thread-local when `actor`/`ip`/`user_agent` are not explicitly passed
- [ ] Middleware registered in `MIDDLEWARE` in `backend/config/settings/base.py`

## Files likely touched
- `backend/apps/audit/tests/test_audit_chain.py`
- `backend/apps/audit/middleware.py` (new)
- `backend/apps/audit/signals.py`
- `backend/config/settings/base.py`

## Test plan
**Manual:**
- Trigger a mandate/lease change via the API as a regular agent; confirm the resulting audit event has non-null `actor`, `ip`, `user_agent` in the DB

**Automated:**
- `cd backend && pytest apps/audit/tests/ -v`

## Handoff notes
2026-04-23: Promoted from discovery `2026-04-23-audit-api-rbac-and-request-context.md` (found during RNT-SEC-008). Item (1): no APIClient RBAC tests on audit endpoints — silent privilege escalation risk. Item (2): signal-triggered events carry null attribution — cross-reference with request logs needed for RHA/FICA disputes. Both are defence-in-depth items that did not block RNT-SEC-008 AC.
