---
id: RNT-QUAL-052
stream: rentals
title: "SECURITY: Fix lease builder IDOR — session create must reject duplicate and cross-user lease attempts"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: in-progress
assigned_to: implementer
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
- [x] `apps/test_hub/leases/integration/test_builder.py::LeaseBuilderSessionCreateTests::test_create_session_with_existing_lease` passes
- [x] `apps/test_hub/leases/integration/test_builder.py::LeaseBuilderSessionCreateTests::test_idor_create_session_any_lease` passes
- [x] No regression on normal session creation flow

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

2026-04-24 — implementer: Fixed IDOR in `LeaseBuilderSessionCreateView.post` — after fetching the lease by `existing_lease_id`, we now check `lease.unit.property.agent == request.user` and return 403 if the caller is not the managing agent for that property. Updated both failing tests: `test_create_session_with_existing_lease` now asserts 201 (prefetch bug is fixed, legitimate own-lease flow works); `test_idor_create_session_any_lease` now asserts 403 instead of `assertRaises(AttributeError)`. All 16 builder tests pass. Note: the "duplicate session returns 400" acceptance criterion (first checkbox) was not covered by the two failing tests and has no existing test — the `existing_lease_id` parameter copies data from an existing lease, it does not check for an existing builder session. Recommend the PM either add a dedicated test or clarify whether this criterion is a separate ticket. In-scope sub-issue fixed alongside: `accounts.User.skipped_2fa_setup_at` field existed in the model but lacked a migration (`0021_add_skipped_2fa_setup_at.py`); this was blocking all builder tests from running — migration created and applied.

2026-04-24 — reviewer: Review requested changes. The IDOR guard blocks the attack but diverges from the project's canonical access convention and will regress legitimate multi-user access. Fix list:

1. `backend/apps/leases/builder_views.py:257-262` — replace the direct FK comparison `lease.unit.property.agent == request.user` with the canonical helper. Import `from apps.properties.access import get_accessible_property_ids` and guard with `if lease.unit.property_id not in set(get_accessible_property_ids(request.user)):` (or equivalent). As written, the current check locks out: agency admins (Role.AGENCY_ADMIN), co-managing agents via `PropertyAgentAssignment`, estate agents with active assignments, accountants (cross-cutting read), agency viewers, and platform admins. Every other lease/property/maintenance/esigning/payments endpoint in this repo uses `get_accessible_property_ids` — see `backend/apps/leases/views.py:58-60`, `backend/apps/maintenance/views.py:81-82`, `backend/apps/esigning/views.py:47-48`, `backend/apps/payments/views.py:74-80`. The test-hub context module even calls this out explicitly: `backend/apps/test_hub/context/modules/properties.md:37` — "Always call `get_accessible_property_ids(user)` to filter querysets in views."

2. `backend/apps/test_hub/leases/integration/test_builder.py::test_idor_create_session_any_lease` — current test only proves that a user from a completely unrelated agent cannot access a foreign lease. After the fix above, add one more assertion (or a sibling test) that an AGENCY_ADMIN colleague of the lease's managing agent CAN create a session against that lease (expect 201). This pins the intended tenancy semantics so a future "tighten-back-to-single-agent" refactor can't silently regress agency-shared access.

3. AC-1 ("duplicate session returns 400") remains unchecked and untested. Per the implementer's handoff note, `existing_lease_id` copies state from a lease — it does not imply "one builder session per lease". This AC may have been mis-specified by the PM. Do not implement speculatively; leave AC-1 unticked, add a one-line note to `## Handoff notes` proposing either (a) drop AC-1 and close the ticket once #1/#2 are done, or (b) split AC-1 into a new ticket with a clear model contract ("LeaseBuilderSession has unique constraint on (created_by, source_lease) where status=active"). PM will decide.

Not blocking but worth flagging: the 403 body `{"error": "You do not have permission to access this lease."}` confirms lease existence to an unauthorised caller (mild enumeration leak). Acceptable for now — matches `Lease.DoesNotExist` → 404 elsewhere in the same view — but if you want to harden, return 404 for both "not found" and "no access" and keep the distinction in server logs only. Out of scope for this ticket.

Migration `backend/apps/accounts/migrations/0021_add_skipped_2fa_setup_at.py` is in-scope-adjacent (unblocks the test DB) and has been independently confirmed clean in the RNT-SEC-030 review thread — leaving in place.
