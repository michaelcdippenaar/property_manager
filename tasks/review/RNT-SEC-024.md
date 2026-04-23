---
id: RNT-SEC-024
stream: security
title: "Formally review and pipeline the RHA compliance gate shipped in commit eed71cb"
feature: "lease_management"
lifecycle_stage: 8
priority: P1
effort: M
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: [RNT-015]
asana_gid: "1214197140899873"
created: 2026-04-22
updated: 2026-04-23T16:30:00Z
---

## Goal
Put the RHA compliance gate code (`rha_check.py`, migration `0018`, `ESigningPanel.vue` changes) that shipped in commit `eed71cb` through the standard implement → review → testing pipeline, confirm the migration is safe, and verify the `rhaOverride` bypass path has correct role checks.

## Acceptance criteria
- [x] `rha_check.py` (253 lines) reviewed for correctness, error handling, and edge cases
- [x] Migration `0018_add_rha_flags_to_lease.py` reviewed: no destructive changes to existing lease records, indexes appropriate, reversible
- [x] `ESigningPanel.vue` `rhaOverride` path confirmed to require `staff` or `agency_admin` role (backend + frontend check)
- [x] `test_rha_gate.py` (315 lines) reviewed — coverage adequate, no false-negatives in the test suite
- [x] Any issues found during review are fixed and re-reviewed before this task moves to testing
- [ ] After testing sign-off, a note is added to the git history tying `eed71cb` to this task ID as the formal review record

## Files likely touched
- `backend/apps/leases/rha_check.py`
- `backend/apps/leases/migrations/0018_add_rha_flags_to_lease.py`
- `backend/apps/leases/tests/test_rha_gate.py`
- `admin/src/views/leases/ESigningPanel.vue`

## Test plan
**Manual:**
- Attempt `rhaOverride` as a tenant-role user — must be rejected (403 or UI option hidden)
- Attempt `rhaOverride` as `agency_admin` — must succeed
- Run migration on a copy of production schema — verify zero data loss on existing lease rows

**Automated:**
- `cd backend && pytest apps/leases/tests/test_rha_gate.py -v`
- `cd backend && python manage.py migrate --run-syncdb` on a clean DB

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-22 — Promoted from discovery `2026-04-22-rha-gate-unreviewed-code-in-sec-commit.md` filed by the reviewer during RNT-SEC-013. The RHA gate (rha_check.py, migration 0018, ESigningPanel changes) was bundled into the RNT-SEC-013 commit without a task or review trail. This task is the formal remediation: a full review pass of everything in eed71cb that was not part of RNT-SEC-013's scope.

2026-04-23 — implementer (RNT-SEC-024) full review pass. Two bugs found and fixed:

BUG 1 (blocking — silent RHA flags in UI): `ESigningPanel.vue` `loadRhaFlags()` read `data.rha_flags` and `data.rha_override`, but the `rha-check` endpoint returns `data.flags` and `data.override`. Similarly `submitOverride()` read `data.rha_override` but the `rha-override` endpoint returns `data.override`. Result: the RHA compliance panel never showed any flags to the agent. Fixed by updating both fetch functions to use the correct keys.

BUG 2 (missing frontend role gate): The "Override as authorised user" button and form had a comment saying staff/agency_admin only, but no `v-if` guard on the DOM element. Any logged-in user could see and attempt the override (the backend would reject them with 403, but the UI should not expose the control at all). Fixed by importing `useAuthStore`, adding a `canRecordOverride` computed (role === 'agency_admin' || role === 'admin'), and gating both the button and the form with `v-if="canRecordOverride"`.

Migration 0018 review: safe — only adds two nullable/default JSONFields, no column type changes, no data loss on existing rows, no indexes added (none needed for JSON flag storage), reversible (both fields can be dropped without data loss). No issues.

rha_check.py review: logic is correct. All 10 blocking code paths tested, ordinal helper is correct (11/12/13 edge case handled). The `_check_inspection_events` guard on `lease.pk` prevents a query on unsaved instances. No issues.

test_rha_gate.py review: 31 unit tests all pass. Coverage of rha_check module, Lease model methods, and the three new RNT-015 clause fields is adequate. Gap identified: no tests for the view endpoint response shape or RBAC enforcement on `rha-override`. Added `TestRhaCheckEndpoints` (7 integration tests) to close this gap — covers correct response keys, blocking flag surfacing, tenant/agent rejection (403), empty-reason rejection (400), and successful agency_admin override.

Caveats for reviewer: integration tests require a live PostgreSQL test DB; they cannot run in the current dev environment but are structurally correct and consistent with other integration tests in the codebase. The final acceptance criterion (git note tying eed71cb to this task ID) is deferred to post-testing sign-off per the task's own wording.

2026-04-23 — reviewer (RNT-SEC-024) — CHANGES REQUESTED. Sending back to implementer.

The two frontend bug fixes (BUG 1 key rename, BUG 2 canRecordOverride v-if guard) are correct and structurally sound. The migration and rha_check.py reviews are verified clean.

One blocking defect found: all 7 new `TestRhaCheckEndpoints` integration tests fail with HTTP 404.

**Root cause** (`backend/apps/leases/tests/test_rha_gate.py`, `TestRhaCheckEndpoints._make_db_lease`): `LeaseViewSet.get_queryset()` (`backend/apps/leases/views.py:43-60`) scopes leases to `get_accessible_property_ids(user)` for any non-tenant, non-admin role. The test helper creates a fresh `agency_admin` user with no property access assignments, so that user's queryset is empty and `get_object()` returns 404 — not 200. The lease was created but is invisible to the authenticating user.

**Required fix**: In `_make_db_lease`, assign the test admin user to the property that owns the created unit. Look at how other integration tests in `apps/test_hub/` or `test_regression_battery.py` grant property access (likely via `PropertyAccessGrant` or `create_property_access` on the tremly fixture). Pattern-match those and apply the same setup in `_make_db_lease`.

**Numbered fixes required:**

1. `backend/apps/leases/tests/test_rha_gate.py`, `TestRhaCheckEndpoints._make_db_lease` (approx line 495): Grant the calling user access to the unit's property so `get_accessible_property_ids` returns the right property ID. The simplest approach is to pass the `admin` user into `_make_db_lease` and call the appropriate access-grant helper on the tremly fixture before returning the lease. Alternatively, use `create_user(role="admin")` (superuser/ADMIN role bypasses the property filter at `views.py:55-56`) — but only if that matches what the tests are actually trying to assert; prefer the access-grant approach to keep the tests realistic.

2. After the fix, run `pytest apps/leases/tests/test_rha_gate.py -v --reuse-db` and confirm all 38 tests pass before re-submitting.

2026-04-23 — implementer (RNT-SEC-024) — test fix delivered.

**Issue:** All 7 integration tests in `TestRhaCheckEndpoints` were failing with HTTP 404 because `agency_admin` users had no property access. `get_accessible_property_ids()` requires `agency_admin` to be in the same agency as agents assigned to properties (either legacy `Property.agent` FK or `PropertyAgentAssignment`). The tests created fresh `agency_admin` users with no agency affiliation.

**Fix implemented:** Refactored `_make_db_lease()` helper to handle property access setup for three user types:

1. **agency_admin**: Created a shared Agency, assigned the lease's agent and the test admin to it. The agent is set on the property via legacy FK, making the property visible to all users in that agency.
2. **tenant**: Created a Person linked to the tenant and set as primary_tenant on the lease. Tenants access via `get_tenant_leases()` (primary/co/occupant link), independent of property scope.
3. **agent**: Created PropertyAgentAssignment to assign the test agent to the property. Agents access via assigned properties (legacy FK or assignment).

Updated all 7 integration tests to pass the relevant user (admin/tenant/agent_to_assign) to the helper before authenticating, ensuring each user type can access the lease and hit the correct permission/validation check (403 for RBAC, 400 for empty reason, 200 for success).

**Result:** All 38 tests now pass (`pytest apps/leases/tests/test_rha_gate.py -v --reuse-db`). Tests are now structurally correct and realistic: they exercise the full access control chain (property scope → lease visibility → RBAC) rather than bypassing it with superuser roles.
