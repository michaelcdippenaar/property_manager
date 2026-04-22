---
discovered_by: rentals-reviewer
discovered_during: RNT-QUAL-027
discovered_at: 2026-04-22
priority_hint: P0
suggested_prefix: RNT-SEC
---

## What I found
All three viewsets in `backend/apps/payments/views.py` use only `permission_classes = [IsAuthenticated]` with no role-based filtering in `get_queryset`. Any authenticated user — including tenants — can list, retrieve, and act on every invoice, payment, and unmatched deposit in the system.

## Why it matters
IDOR: a tenant can enumerate all other tenants' invoices and payment histories. `UnmatchedPaymentViewSet` is a full `ModelViewSet` (create/update/delete included), so a tenant could also create or delete unmatched deposit records. This is a POPIA data exposure and a financial integrity risk.

## Where I saw it
- `backend/apps/payments/views.py` — `RentInvoiceViewSet.get_queryset` (no user-scope filter)
- `backend/apps/payments/views.py` — `RentPaymentViewSet.queryset` (class-level, no user filter)
- `backend/apps/payments/views.py` — `UnmatchedPaymentViewSet.get_queryset` (no user-scope filter)
- Compare: `backend/apps/leases/views.py` scopes by `user.role` in every `get_queryset`.

## Suggested acceptance criteria (rough)
- [ ] `RentInvoiceViewSet.get_queryset` scopes to leases accessible by the requesting user (mirrors leases app pattern)
- [ ] `RentPaymentViewSet.queryset` replaced with a scoped `get_queryset`
- [ ] `UnmatchedPaymentViewSet` restricted to admin/agency_admin roles only (tenants have no business seeing unmatched deposits)
- [ ] Role-based permission tests added to `backend/apps/payments/tests/`

## Why I didn't fix it in the current task
Out of scope — RNT-QUAL-027 is a build/TS fix task. The payments app was bundled into this commit from RNT-QUAL-004 work and needs its own security review pass.
