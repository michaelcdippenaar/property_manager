---
discovered_by: rentals-implementer
discovered_during: RNT-QUAL-008
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found

The `AgentInvoiceApprovalView` backend endpoint (`POST /maintenance/<request_pk>/invoice/`) for agents to approve, reject, and mark invoices as paid is fully implemented, but there is no Vue component in the agent maintenance detail view to surface it. Agents currently have no UI to act on supplier invoices.

## Why it matters

Without the agent UI, the invoice approval flow is incomplete from end to end — suppliers can submit invoices but agents cannot approve/reject/mark paid without calling the API directly. This blocks the "awaiting payment" and "paid" states from ever being reached in production.

## Where I saw it

- `backend/apps/maintenance/views.py` — `AgentInvoiceApprovalView` (added in RNT-QUAL-008)
- `admin/src/views/maintenance/` — no invoice panel in any existing maintenance request detail view

## Suggested acceptance criteria (rough)
- [ ] Maintenance request detail view shows invoice panel when a supplier invoice is present (status chip + total + PDF link)
- [ ] Agent can approve / reject (with reason) from the panel
- [ ] Agent can mark as paid with an EFT reference field
- [ ] Invoice status change triggers a toast / activity log refresh

## Why I didn't fix it in the current task

The current task scope was the supplier-facing portal. Adding an agent UI panel to the maintenance detail view would have significantly expanded the diff into a different portal and feature area.
