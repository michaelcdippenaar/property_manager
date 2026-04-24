---
id: RNT-SEC-039
stream: rentals
title: "Audit log hardening: RBAC regression tests + AuditContextMiddleware for signal-triggered events"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: in-progress
assigned_to: implementer
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

2026-04-24 (reviewer) — Review requested changes. 31/31 tests pass locally. What I verified OK:
- Thread-local correctness: `finally` block clears context on both normal and exception paths; `test_context_cleared_even_on_view_exception` covers the raise path. `_EMPTY_CTX` singleton is read-only in callers so the sentinel cannot be mutated.
- Signal out-of-request path: `get_audit_context()` returns `_EMPTY_CTX` when no request has run, so `_write_event` called from a Celery task / management command degrades cleanly to `actor=None, ip=None, user_agent=""` with no AttributeError.
- RBAC role coverage: all 9 roles in `apps.accounts.models.User.Role` (ADMIN, AGENCY_ADMIN, AGENT, ESTATE_AGENT, MANAGING_AGENT, TENANT, OWNER, SUPPLIER — plus anonymous) are exercised. `OWNER` is the correct codebase mapping for the task's "landlord" — confirmed against `User.Role` enum (no `LANDLORD` member exists). Acceptable.
- Middleware is placed after `AuthenticationMiddleware` as required.

**Blocker — POPIA audit-trail integrity: X-Forwarded-For is spoofable as implemented.**

1. `backend/apps/audit/middleware.py:114-126` (`_get_client_ip`) unconditionally trusts `HTTP_X_FORWARDED_FOR` and takes the FIRST (leftmost) entry. That is the attacker-controlled position in the standard append-chain (`client_ip, proxyA_ip, proxyB_ip`). Any request with `X-Forwarded-For: 1.2.3.4` directly to the app — or through a proxy that does not strip/overwrite the client-supplied header — will persist `1.2.3.4` into `AuditEvent.ip_address`. This poisons the exact RHA/FICA dispute cross-reference use case called out in the original handoff and is a POPIA audit-integrity regression.

2. The inline comment on line 120 ("In production the load-balancer / reverse-proxy rewrites this header so we can trust the first entry") is factually wrong for the standard Caddy/nginx/ALB setups used here. Standard proxies **append** to XFF, they do not rewrite. The first entry is client-supplied.

3. The repo already has a hardened helper that solves exactly this problem: `backend/utils/http.py::get_client_ip(request)`. It is gated on `NUM_PROXIES` and optionally `TRUSTED_PROXY_IPS`, walks the rightmost `NUM_PROXIES` hops, and has unit tests in `backend/utils/tests/test_http.py`. The middleware must use it.

### Required fixes

1. **Replace `AuditContextMiddleware._get_client_ip`** with a call to `utils.http.get_client_ip(request)`. Delete the private helper and its wrong comment. This inherits the existing `NUM_PROXIES` / `TRUSTED_PROXY_IPS` trust configuration and guarantees a single code path for "real client IP" across the codebase.
2. **Update `test_x_forwarded_for_used_as_ip`** to reflect the correct behaviour. With default `NUM_PROXIES=1` and `XFF="203.0.113.5, 10.0.0.1"`, the expected client IP is `203.0.113.5` (rightmost minus 1 hop = index `-2` = `203.0.113.5`, i.e. the leftmost here because there are only 2 entries) — confirm against `utils.http.get_client_ip` semantics rather than hard-coding "first entry".
3. **Add a spoofing-negative test**: a request with `NUM_PROXIES=0` and `HTTP_X_FORWARDED_FOR="1.2.3.4"` must record `REMOTE_ADDR`, not `1.2.3.4`. This is the regression guard for the vulnerability above.

Re-run `cd backend && pytest apps/audit/ -xvs` after the change; all 31+ tests must still be green.

Move back to `in-progress/` once fixed.
