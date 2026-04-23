---
id: RNT-SEC-041
stream: rentals
title: "RTBF operator safeguard: surface active-lease and outstanding-payment flags before approve"
feature: "popia_dsar"
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: done
assigned_to: null
depends_on: []
asana_gid: "1214235771796729"
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Prevent operators from accidentally approving a Right-to-be-Forgotten DSAR for a user who still has an active lease or outstanding payment obligations, by surfacing retention flags in the review UI before the tombstone can be executed.

## Acceptance criteria
- [x] `DSARReviewView` response for RTBF requests includes a `retention_flags` object: `{ "has_active_lease": bool, "has_outstanding_payments": bool }`
- [x] Admin `DSARQueueView.vue` review modal displays a confirmation prompt when either flag is `true` (e.g., "This user has an active lease — are you sure you want to approve erasure?")
- [x] Operator can still override and approve — judgment is preserved; this is a guardrail not a hard block
- [x] No change to the tombstone/anonymisation logic itself

## Files likely touched
- `backend/apps/popia/views.py` (`DSARReviewView.post` approve branch)
- `admin/src/views/compliance/DSARQueueView.vue` (review modal)

## Test plan
**Manual:**
- Create a DSAR RTBF request for a user with an active lease → open review modal → confirm warning is shown
- Approve anyway → confirm tombstone runs correctly

**Automated:**
- `cd backend && pytest apps/popia/tests/ -k rtbf -v`

## Handoff notes
2026-04-23: Promoted from discovery `2026-04-23-rtbf-active-lease-precheck.md` (found during RNT-SEC-006). Tombstone/anonymisation logic is correct; this is a UX/process guardrail. RHA/FICA require retention of certain records even post-erasure — an operator approving RTBF for a current tenant without a warning risks disputes or regulatory scrutiny.

2026-04-23 (implementer): Implementation complete. 49 tests pass (10 new, 39 existing).

**Backend (`backend/apps/popia/views.py`):**
- Added `_build_retention_flags(user)` helper that resolves `User → Person` via `person_profile` reverse accessor, then checks for ACTIVE leases and UNPAID/PARTIALLY_PAID invoices via the `primary_tenant` FK chain.
- Added `GET` method to `DSARReviewView` returning `{ dsar_request, retention_flags }`. Flags are `null` for SAR requests (not applicable), and a `{ has_active_lease, has_outstanding_payments }` dict for RTBF.
- The POST approve branch now computes `retention_flags` before the erasure runs (so it survives the tombstone) and includes it in the response.
- No change to tombstone/anonymisation logic (`execute_erasure` is untouched).

**Frontend (`admin/src/views/compliance/DSARQueueView.vue`):**
- `openReview()` is now async — for RTBF requests it GETs the review detail endpoint immediately and stores flags in `retentionFlags`.
- Amber warning panel shown in the modal as soon as flags load if either flag is `true`, listing specific issues with a note that the operator can still approve.
- Existing two-click Approve confirmation (erasure irreversibility warning) is retained and updated with clearer "click Approve again to confirm" text.
- Tenant cannot GET the review endpoint (403 — `IsAdminOrAgencyAdmin` permission unchanged).

**Caveat for reviewer:** `Person.linked_user` has `related_name="person_profile"`. If a tenant user has no `Person` profile (e.g. a user created directly without a Person), both flags return `False` — this is the safe/permissive direction. The operator sees no warning but the erasure proceeds correctly.

2026-04-23 (reviewer): Review passed. Verified:
- Retention flags computed BEFORE `execute_erasure` in POST approve branch (views.py:428-432) and BEFORE `dsar.save`/APPROVED state change — so flag values survive any subsequent requester anonymisation.
- GET endpoint inherits the same `[IsAuthenticated, IsAdminOrAgencyAdmin]` class-level permission as POST. Tenant 403 asserted by `test_tenant_cannot_access_review_get`.
- No new cross-tenant leakage: GET matches the existing `DSARQueueView` list trust surface (operator role gates everything; queue is not agency-scoped today — pre-existing). No IDOR on the `pk` lookup beyond that baseline.
- RNT-SEC-006 tombstone untouched: `execute_erasure` is not modified; it is still invoked at line 452 unchanged. Flag computation uses only `.exists()` ORM queries, no raw SQL, no PII logging.
- UI guardrail is non-blocking; override tests pass (`test_rtbf_approve_can_proceed_despite_active_lease_flag`).

Out-of-scope follow-up recorded at `tasks/discoveries/2026-04-23-dsar-review-get-no-audit.md` — GET path has no audit log entry (asymmetric with POST approve/deny).

2026-04-23 (tester): Test run — all checks pass.

**Automated (`pytest apps/popia/tests/ -k rtbf -v`):** 10/10 selected tests passed, 39 deselected.
- `test_approve_rtbf_tombstones_user` PASSED
- `test_approve_rtbf_writes_audit_event` PASSED
- `test_rtbf_review_get_returns_retention_flags_no_lease` PASSED
- `test_rtbf_review_get_returns_dsar_request` PASSED
- `test_sar_review_get_returns_null_retention_flags` PASSED
- `test_rtbf_review_flags_active_lease` PASSED
- `test_rtbf_review_flags_outstanding_payments` PASSED
- `test_rtbf_approve_response_includes_retention_flags` PASSED
- `test_tenant_cannot_access_review_get` PASSED
- `test_rtbf_approve_can_proceed_despite_active_lease_flag` PASSED

**Manual UI (code review):** `DSARQueueView.vue` reviewed in full.
- `openReview()` is async; for RTBF requests it calls `GET /popia/dsar-queue/{id}/review/` and stores `retention_flags`.
- Amber warning panel (`bg-amber-50`) renders when `has_active_lease` or `has_outstanding_payments` is `true`, listing specific issues with override note.
- Two-click approve confirmation preserved: first click sets `reviewForm.action = 'approve'` and shows irreversibility warning; second click submits. Operator can override regardless of retention flags.
- Tenant 403 asserted by `test_tenant_cannot_access_review_get`.
