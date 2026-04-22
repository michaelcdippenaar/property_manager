---
id: RNT-SEC-031
stream: rentals
title: "Payments API: add role-scoped queryset filtering to prevent IDOR"
feature: ""
lifecycle_stage: null
priority: P0
effort: M
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214203923425520"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Scope all three payments viewsets (`RentInvoiceViewSet`, `RentPaymentViewSet`, `UnmatchedPaymentViewSet`) to the requesting user's role, preventing IDOR data exposure and eliminating tenant write access to unmatched deposit records.

## Acceptance criteria
- [ ] `RentInvoiceViewSet.get_queryset` filters to invoices on leases accessible to the requesting user (mirrors `leases/views.py` pattern)
- [ ] `RentPaymentViewSet.queryset` replaced with a scoped `get_queryset` using the same role-based logic
- [ ] `UnmatchedPaymentViewSet` restricted to `agency_admin` / admin roles only — tenants and owners receive 403
- [ ] Role-based permission tests added under `backend/apps/payments/tests/` covering tenant, owner, agent, and admin scenarios
- [ ] No regression on existing payments functionality for agents and admins

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
