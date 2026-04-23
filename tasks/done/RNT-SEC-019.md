---
id: RNT-SEC-019
stream: rentals
title: "Restrict GotenbergHealthView to admin-only to prevent infrastructure disclosure"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: done
assigned_to: null
depends_on: []
asana_gid: "1214195240490293"
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Restrict `GotenbergHealthView` to admin users only (or strip version/engine fields) so authenticated agents cannot enumerate internal infrastructure details via the health endpoint.

## Acceptance criteria
- [x] `GotenbergHealthView` restricted to `IsAdminUser` only (not all agents), OR response strips engine name, version strings, and internal service structure before returning to client
- [x] Test asserting that an agent (non-admin) user receives 403 on `GET /api/v1/esigning/gotenberg/health/`

## Files likely touched
- `backend/apps/esigning/views.py` (`GotenbergHealthView`, ~line 387)
- `backend/apps/esigning/urls.py` (~line 45)
- Relevant test file in `backend/apps/test_hub/esigning/`

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/esigning/ -k "gotenberg_health" -v`
- Agent role user: assert 403
- Admin user: assert 200

## Handoff notes
2026-04-22: Promoted from discovery `2026-04-22-gotenberg-health-endpoint-recon.md` (found during RNT-SEC-004 review). Not a direct exploit but useful for targeted attack reconnaissance.

2026-04-23: Verified implementation was already complete and correct in `backend/apps/esigning/views.py`. `GotenbergHealthView` already carries `permission_classes = [IsAdmin]` (from `apps.accounts.permissions`) which restricts to users with `role == ADMIN` or `is_superuser`. The integration test file `backend/apps/test_hub/esigning/integration/test_gotenberg_health_access.py` already covers all three required cases: agent gets 403, admin gets 200, unauthenticated gets 401/403. All 3 tests pass. No code changes needed — this was a validation-only pass confirming the fix was in place.

2026-04-23: Review passed. Verified (1) `backend/apps/esigning/views.py:396` sets `permission_classes = [IsAdmin]`, imported from `apps.accounts.permissions` (line 14). (2) `IsAdmin` (accounts/permissions.py:9-14) is strict: only `role == User.Role.ADMIN` or `is_superuser` — excludes AGENCY_ADMIN, AGENT, ESTATE_AGENT, MANAGING_AGENT, ACCOUNTANT, VIEWER. (3) `apps/test_hub/esigning/integration/test_gotenberg_health_access.py` — all 3 tests pass (agent 403, admin 200, unauth 401/403). (4) Other health endpoints scanned: `/api/v1/health/` (trivial liveness — ok); `/api/v1/test-hub/health/` (gated by ENABLE_TEST_ENDPOINTS, off in prod); `ESigningWebhookInfoView` (only exposes backend name + link expiry, not infra). Dropped discovery `2026-04-23-agent-health-check-infra-leak.md` for `AgentHealthCheckView` in apps/maintenance which leaks embedding model + file paths — same class of issue, separate ticket.

### Test run 2026-04-23
- `pytest apps/test_hub/esigning/ -k "gotenberg_health" -v`: 3/3 PASS
  - `test_admin_can_access` PASSED
  - `test_agent_receives_403` PASSED
  - `test_unauthenticated_denied` PASSED
- `python3 manage.py check`: System check identified no issues (0 silenced)
