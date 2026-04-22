---
discovered_by: rentals-reviewer
discovered_during: RNT-SEC-031
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found
The `?search=` filter in `RentInvoiceViewSet.get_queryset` queries
`lease__primary_tenant__first_name` and `lease__primary_tenant__last_name`, but
`Person` does not have those fields — it uses `full_name` (a single field).
The filter silently returns no results for any name search and would raise a
`FieldError` in strict ORM mode.

## Why it matters
Agents and admins using the invoice list search bar get zero results when
searching by tenant name. Silent failure makes it hard to detect; affects
every caller of GET `/api/v1/payments/invoices/?search=<name>`.

## Where I saw it
- `backend/apps/payments/views.py:92-96`

## Suggested acceptance criteria (rough)
- [ ] Replace `primary_tenant__first_name` + `primary_tenant__last_name` lookups
  with `primary_tenant__full_name__icontains` in the search Q filter.
- [ ] Add a test that searches by a known tenant name and confirms at least one
  result is returned.

## Why I didn't fix it in the current task
Pre-existing bug, not introduced by RNT-SEC-031. Fixing it would expand the
diff beyond the IDOR-scoping scope of this task.
