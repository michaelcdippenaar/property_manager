---
id: RNT-SEC-039
stream: rentals
title: "Audit log hardening: RBAC regression tests + AuditContextMiddleware for signal-triggered events"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214237326490411"
created: 2026-04-23
updated: 2026-04-24
---

## Goal
Close two residual gaps from RNT-SEC-008: add RBAC regression tests for the audit endpoints, and introduce a thread-local context middleware so signal-triggered audit events carry actor/IP/user-agent attribution.

## Acceptance criteria
- [x] `APIClient` tests in `backend/apps/audit/tests/test_audit_chain.py` assert 200 for `admin`/`agency_admin` and 403 for `agent`, `estate_agent`, `managing_agent`, `tenant`, `landlord`, `supplier` against both `GET /api/v1/audit/events/` and `GET /api/v1/audit/timeline/.../`
- [x] `apps.audit.middleware.AuditContextMiddleware` stashes `request.user`, `REMOTE_ADDR`, `HTTP_USER_AGENT` into thread-local storage for the duration of each request
- [x] `_write_event` in `backend/apps/audit/signals.py` reads from the thread-local when `actor`/`ip`/`user_agent` are not explicitly passed
- [x] Middleware registered in `MIDDLEWARE` in `backend/config/settings/base.py`

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

2026-04-24 (implementer): All four ACs delivered. New file `backend/apps/audit/middleware.py` introduces `AuditContextMiddleware` (thread-local store + clear in finally block; honours X-Forwarded-For for real-IP). `_write_event` in `signals.py` falls back to `get_audit_context()` for all three attribution fields only when they are not explicitly supplied by the caller — existing callers that pass explicit values are unaffected. Middleware inserted after `AuthenticationMiddleware` in `base.py` so `request.user` is always resolved before context capture. 15 new tests added across two classes (`TestAuditEndpointRBAC`, `TestAuditContextMiddleware`); all 31 audit tests pass green. Note: the task AC says "landlord" but the codebase uses `User.Role.OWNER` — the test uses `OWNER` and the Handoff notes explain the mapping so the reviewer is not surprised.
