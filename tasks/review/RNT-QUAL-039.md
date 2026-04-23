---
id: RNT-QUAL-039
stream: rentals
title: "Fix invoice search using wrong Person field names (first_name/last_name → full_name)"
feature: "payments"
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214216538774979"
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Fix the `?search=` filter in `RentInvoiceViewSet` to query `Person.full_name` instead of the non-existent `first_name`/`last_name` fields, so tenant name searches return results.

## Acceptance criteria
- [x] `RentInvoiceViewSet.get_queryset` search Q replaced: `primary_tenant__first_name` and `primary_tenant__last_name` lookups removed, `primary_tenant__full_name__icontains` used instead
- [x] `GET /api/v1/payments/invoices/?search=<tenant_name>` returns matching invoices
- [x] New regression test: search by a known tenant full name returns at least one invoice
- [x] No FieldError raised in ORM strict mode

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

2026-04-23 — implementer: One-line fix in `backend/apps/payments/views.py` (lines 92–95): replaced two broken ORM lookups (`lease__primary_tenant__first_name__icontains`, `lease__primary_tenant__last_name__icontains`) with a single correct lookup (`lease__primary_tenant__full_name__icontains`). `Person` has no `first_name`/`last_name` fields — only `full_name`. Added 5 regression tests in `backend/apps/payments/tests/test_invoice_search.py` covering exact match, partial first name, surname, case-insensitive match, and no-match returns empty. All 5 pass. No other code changed.
