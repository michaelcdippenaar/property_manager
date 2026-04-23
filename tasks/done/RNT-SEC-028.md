---
id: RNT-SEC-028
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
asana_gid: "1214200406225875"
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Prevent any authenticated agent from mapping internal infrastructure (Chromium, LibreOffice versions) via `GET /api/v1/esigning/gotenberg/health/` by restricting access or stripping sensitive fields.

## Acceptance criteria
- [x] `GotenbergHealthView` restricted to `IsAdmin` only (not agents) — `permission_classes` changed from `[IsAgentOrAdmin]` to `[IsAdmin]`
- [x] Test asserts a non-admin agent user receives HTTP 403 on `GET /api/v1/esigning/gotenberg/health/`
- [x] Admin users can still access the endpoint for operational monitoring

## Files likely touched
- `backend/apps/esigning/views.py`
- `backend/apps/test_hub/esigning/` (new test)

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/esigning/ -k gotenberg`

## Handoff notes
Promoted from discovery `2026-04-22-gotenberg-health-endpoint-recon.md` (found during RNT-SEC-004). Information-disclosure vector: agents can map internal service versions.

### 2026-04-23 — implementer

**What was done:**

- `backend/apps/esigning/views.py`: Changed `GotenbergHealthView.permission_classes` from `[IsAgentOrAdmin]` to `[IsAdmin]` (imported from `apps.accounts.permissions`). Also removed the now-redundant `can_manage_esigning()` guard inside the handler body since `IsAdmin` is stricter and handles the check at the DRF permission layer. Added a docstring explaining the rationale (infrastructure disclosure).
- `backend/apps/test_hub/esigning/integration/test_gotenberg_health_access.py`: New test class `TestGotenbergHealthAccessControl` with three cases: agent gets 403, admin gets 200 (health_check mocked), unauthenticated gets 401/403. All 13 gotenberg-keyed tests pass (`pytest apps/test_hub/esigning/ -k gotenberg`).

**Caveats for reviewer:**

- The `IsAdmin` permission class grants access to `User.Role.ADMIN` or `is_superuser`. Agency admins (`AGENCY_ADMIN`) and managing agents (`MANAGING_AGENT`) are excluded — this is intentional; the health endpoint exposes Chromium/LibreOffice version strings that have no operational value to those roles.
- The `can_manage_esigning()` inner guard was removed from `GotenbergHealthView.get()` because `IsAdmin` is a superset of that check (admin always satisfies `can_manage_esigning`). No behaviour change for admin users.

### 2026-04-23 — reviewer

**Review passed.**

Checked: (1) `permission_classes = [IsAdmin]` confirmed in `backend/apps/esigning/views.py` line 396 — satisfies AC1. (2) `IsAdmin` definition in `apps/accounts/permissions.py` correctly gates on `User.Role.ADMIN or is_superuser`; `AGENCY_ADMIN`/`MANAGING_AGENT` exclusion is intentional and correct. (3) Inner `can_manage_esigning()` guard removal is safe — `IsAdmin` is strictly more restrictive, no behaviour change for admin users. (4) New test file `test_gotenberg_health_access.py` covers all three cases (agent 403, admin 200, unauthenticated 401/403) — satisfies AC2 and AC3. (5) Mock patch target `apps.esigning.gotenberg.health_check` is correct because the view's import is deferred inside `get()`, resolved from the module at call time — consistent with existing gotenberg unit test patterns. (6) No PII logged, no raw SQL, no auth bypass. Security pass clean.

### 2026-04-23 — tester

**Test run:** `pytest apps/test_hub/esigning/ -k gotenberg` — 13 selected, 13 passed.

- `test_agent_receives_403` PASS
- `test_admin_can_access` PASS
- `test_unauthenticated_denied` PASS
- All 10 existing gotenberg unit tests PASS

All acceptance criteria verified. No failures.
