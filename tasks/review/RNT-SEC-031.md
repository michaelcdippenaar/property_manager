---
id: RNT-SEC-031
stream: rentals
title: "Payments API: add role-scoped queryset filtering to prevent IDOR"
feature: ""
lifecycle_stage: null
priority: P0
effort: M
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214203923425520"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Scope all three payments viewsets (`RentInvoiceViewSet`, `RentPaymentViewSet`, `UnmatchedPaymentViewSet`) to the requesting user's role, preventing IDOR data exposure and eliminating tenant write access to unmatched deposit records.

## Acceptance criteria
- [x] `RentInvoiceViewSet.get_queryset` filters to invoices on leases accessible to the requesting user (mirrors `leases/views.py` pattern)
- [x] `RentPaymentViewSet.queryset` replaced with a scoped `get_queryset` using the same role-based logic
- [x] `UnmatchedPaymentViewSet` restricted to `agency_admin` / admin roles only — tenants and owners receive 403
- [x] Role-based permission tests added under `backend/apps/payments/tests/` covering tenant, owner, agent, and admin scenarios
- [x] No regression on existing payments functionality for agents and admins

## Files likely touched
- `backend/apps/payments/views.py`
- `backend/apps/payments/tests/` (new test file or additions to existing)

## Test plan
**Automated:**
- `cd backend && pytest apps/payments/tests/`

**Manual:**
- Log in as tenant → GET `/api/v1/payments/invoices/` → must return only own invoices (not other tenants')
- Log in as tenant → GET `/api/v1/payments/unmatched/` → must return 403
- Log in as agent → full access confirmed

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-22 — Promoted from discovery `2026-04-22-payments-api-missing-role-scoping.md` (P0 IDOR + POPIA exposure, found during RNT-QUAL-027 review). Ship-blocker — do not go live with open read access to all invoices.

2026-04-22 — Implemented by rentals-implementer. Changes made to `backend/apps/payments/views.py`:
- `RentInvoiceViewSet`: changed permission to `IsAuthenticated` (was `IsAgentOrAdmin`) and added role-scoped `get_queryset` — admin/superuser unrestricted; tenant filtered to their leases via `get_tenant_leases`; owner and all agent roles filtered to accessible properties via `get_accessible_property_ids`. The `record_payment` action retains `IsAgentOrAdmin` permission to block tenant write access.
- `RentPaymentViewSet`: removed static `queryset`, added `get_queryset` with same role-based logic (tenant → own leases; others → property-scoped). Permission changed to `IsAuthenticated`; the `reverse` action retains `IsAgentOrAdmin`.
- `UnmatchedPaymentViewSet`: permission changed from `IsAgentOrAdmin` to `IsAdminOrAgencyAdmin` — regular agents, owners, and tenants now receive 403. Removed stale "intentionally unscoped" comment.
- New test file: `backend/apps/payments/tests/test_rbac.py` — 20 tests, all passing. Covers tenant IDOR (list + detail), agent property scoping, admin full access, and unmatched 403 for tenant/owner/agent roles.
- All 43 payments tests pass (no regressions on reconciliation tests).
- Note for reviewer: the search filter in `get_queryset` uses `primary_tenant__first_name` and `primary_tenant__last_name` which don't exist on `Person` (which uses `full_name`). This is a pre-existing bug — not introduced here. Flagged as a discovery if PM wants to track it.
