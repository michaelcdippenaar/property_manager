---
id: RNT-QUAL-056
stream: rentals
title: "Add agent invoice approval UI panel to maintenance request detail view"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: null
created: 2026-04-24
updated: 2026-04-24
---

## Goal
Surface the `AgentInvoiceApprovalView` backend endpoint in the admin maintenance request detail view so agents can approve, reject, and mark invoices as paid without calling the API directly.

## Acceptance criteria
- [ ] Maintenance request detail view shows an invoice panel when a supplier invoice is present (status chip, total amount, PDF download link)
- [ ] Agent can approve the invoice from the panel
- [ ] Agent can reject the invoice with a required reason field
- [ ] Agent can mark invoice as paid with an EFT reference field
- [ ] Invoice status change triggers a toast notification and refreshes the activity log
- [ ] Panel is hidden / empty state shown when no invoice has been submitted

## Files likely touched
- `admin/src/views/maintenance/` (detail view component — add invoice panel)
- `admin/src/components/maintenance/InvoiceApprovalPanel.vue` (new component)
- `backend/apps/maintenance/views.py` — `AgentInvoiceApprovalView` (no backend changes expected)

## Test plan
**Manual:**
- Create a maintenance request, have supplier submit invoice, open detail view as agent
- Verify invoice panel renders with correct status/amount/PDF
- Test approve, reject (with reason), and mark paid flows
- Confirm toast fires and activity log updates on each action

**Automated:**
- `cd backend && pytest apps/maintenance/tests/ -v -k invoice`

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-24 — Promoted from discovery `2026-04-23-agent-invoice-approval-ui.md`. Backend `AgentInvoiceApprovalView` is complete; only the agent UI panel is missing.
