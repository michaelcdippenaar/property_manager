---
id: RNT-QUAL-052
stream: rentals
title: "SECURITY: Fix lease builder IDOR — session create must reject duplicate and cross-user lease attempts"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214246426569538"
created: 2026-04-24
updated: 2026-04-24
---

## Goal
The lease builder session-create endpoint no longer raises `AttributeError` on duplicate session or IDOR (cross-user lease access) attempts — it silently succeeds. This is a potential security regression: an agent must not be able to create a lease builder session for a lease they do not own.

## Acceptance criteria
- [ ] `POST /api/v1/leases/builder/session/` with an existing session for the same lease returns 400 (or 409 Conflict), not 200
- [ ] `POST /api/v1/leases/builder/session/` with a lease owned by a different agent returns 403 (IDOR guard)
- [ ] `apps/test_hub/leases/integration/test_builder.py::LeaseBuilderSessionCreateTests::test_create_session_with_existing_lease` passes
- [ ] `apps/test_hub/leases/integration/test_builder.py::LeaseBuilderSessionCreateTests::test_idor_create_session_any_lease` passes
- [ ] No regression on normal session creation flow

## Files likely touched
- `backend/apps/leases/builder_views.py` (or equivalent session create endpoint)
- `backend/apps/leases/builder_services.py` (session create logic)
- `backend/apps/test_hub/leases/integration/test_builder.py`

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/leases/integration/test_builder.py::LeaseBuilderSessionCreateTests -v`

**Manual:**
- Attempt to create a second session for a lease with an active session → 400 returned
- Attempt to access another agent's lease → 403 returned

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-24 — rentals-pm: Promoted from discovery `2026-04-23-test-hub-remaining-regressions-post-infra-fix.md`. Marked P1 (potential security — IDOR risk). Previously the `AttributeError` incidentally blocked the IDOR path; removal of that error exposed the missing permission check. Treat as a security regression until verified.
