---
id: RNT-QUAL-039
stream: rentals
title: "Fix invoice search using wrong Person field names (first_name/last_name → full_name)"
feature: "payments"
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214216538774979"
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Fix the `?search=` filter in `RentInvoiceViewSet` to query `Person.full_name` instead of the non-existent `first_name`/`last_name` fields, so tenant name searches return results.

## Acceptance criteria
- [ ] `RentInvoiceViewSet.get_queryset` search Q replaced: `primary_tenant__first_name` and `primary_tenant__last_name` lookups removed, `primary_tenant__full_name__icontains` used instead
- [ ] `GET /api/v1/payments/invoices/?search=<tenant_name>` returns matching invoices
- [ ] New regression test: search by a known tenant full name returns at least one invoice
- [ ] No FieldError raised in ORM strict mode

## Files likely touched
- `backend/apps/payments/views.py` (lines 92–96)
- `backend/apps/payments/tests/` or `apps/test_hub/payments/` (new regression test)

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/payments/ -v -k invoice`
- Verify `?search=` returns correct results with a known tenant name fixture

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-23 — rentals-pm: Promoted from discovery `2026-04-22-payments-invoice-search-wrong-field-names`. Found during RNT-SEC-031 review. Silent failure — search returns zero results for any name query. Pre-existing bug unrelated to RNT-SEC-031.
