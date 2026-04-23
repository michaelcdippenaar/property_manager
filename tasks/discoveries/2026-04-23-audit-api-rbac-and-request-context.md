---
discovered_by: rentals-reviewer
discovered_during: RNT-SEC-008
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-SEC
---

## What I found
Two small gaps in the RNT-SEC-008 audit log that are out of scope for that ticket but worth follow-up:

1. No automated test asserts that `GET /api/v1/audit/events/` and `/audit/timeline/...` return 403 for non-admin roles (agent, estate_agent, managing_agent, tenant, landlord, supplier). The permission class is correct in code, but there is no regression guard.
2. Audit events written via Django signals have no actor / IP / user-agent because signals have no request context. Signal-triggered events therefore carry null attribution — acceptable for v1 but weakens evidentiary value for RHA/FICA disputes.

## Why it matters
(1) If someone later swaps the permission class or refactors the viewset, a silent privilege escalation would reach the evidence log — the tamper-evident design relies on the log being read-protected as much as write-protected. (2) Without actor/IP on signal events, we cannot say *who* triggered a mandate/lease change from the DB log alone; we must cross-reference request logs.

## Where I saw it
- `backend/apps/audit/tests/test_audit_chain.py` — no `APIClient` test class
- `backend/apps/audit/signals.py:147-209` — `_write_event` accepts actor/ip/user_agent but signal callers don't pass them

## Suggested acceptance criteria (rough)
- [ ] Add APIClient tests covering 200 for admin/agency_admin and 403 for agent/estate_agent/managing_agent/tenant/landlord/supplier against both audit endpoints
- [ ] Add a thread-local request-context middleware (`apps.audit.middleware.AuditContextMiddleware`) that stashes `request.user`, `REMOTE_ADDR`, `HTTP_USER_AGENT` for the duration of the request; `_write_event` reads from it when called from a signal

## Why I didn't fix it in the current task
RNT-SEC-008 acceptance criteria are all met by the current diff. The implementer already flagged item (2) as a deferred hardening, and item (1) is additional defence-in-depth that expands scope.
