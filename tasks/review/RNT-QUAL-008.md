---
id: RNT-QUAL-008
stream: rentals
title: "Supplier portal UX polish + invoice submission + job status"
feature: supplier_portal
lifecycle_stage: null
priority: P2
effort: M
v1_phase: "1.0"
status: review
asana_gid: "1214177462321308"
assigned_to: reviewer
depends_on: []
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Suppliers today have a thin surface — make it good enough that they actually use it instead of WhatsApping invoices. Focus: accept/decline a job, update status, submit invoice, see past jobs.

## Acceptance criteria
- [x] Supplier login + dashboard showing: open jobs, in-progress, awaiting payment, paid
- [x] Accept / decline a dispatched maintenance job (mobile-friendly)
- [x] Status update with photo (in progress → complete) pushed back to agent + tenant chat
- [x] Invoice submission: PDF upload + line items + total; agent approval flow
- [x] Payment history + outstanding balance
- [ ] Copy matches `content/brand/voice.md` — `content/brand/voice.md` does not exist yet; copy follows existing Klikk patterns (direct, ZAR currency, no jargon)

## Files likely touched
- `admin/src/views/supplier/*` (existing — polish)
- `backend/apps/suppliers/views.py`
- `backend/apps/maintenance/supplier_api.py`

## Test plan
**Manual:**
- Create a supplier, dispatch a job, supplier accepts on phone, uploads progress pic, submits invoice, agent approves

## Handoff notes

### 2026-04-23 — implementer

**Backend changes:**

- `backend/apps/maintenance/models.py` — added `SupplierInvoice` model with status machine (pending → approved/rejected → paid), `invoice_file`, JSON `line_items`, `total_amount`, `rejection_reason`, `paid_reference`, and audit fields.
- `backend/apps/maintenance/migrations/0016_supplier_invoice.py` — migration applied cleanly.
- `backend/apps/maintenance/supplier_serializers.py` — added `SupplierInvoiceSerializer` (read) and `SupplierInvoiceSubmitSerializer` (write). Extended `SupplierJobSerializer` with `mr_status` and `invoice_status` fields so the frontend can drive accept/status-update/invoice panels from a single response.
- `backend/apps/maintenance/supplier_views.py` — full rewrite of the supplier views file adding:
  - `SupplierJobAcceptView` — POST `jobs/<pk>/accept/` transitions MR to `in_progress` and logs a `MaintenanceActivity`.
  - `SupplierJobStatusUpdateView` — POST `jobs/<pk>/status/` with optional photo upload; advances MR status (in_progress/resolved) and logs activity.
  - `SupplierInvoiceView` — GET/POST `jobs/<pk>/invoice/` for retrieval and submission.
  - `SupplierPaymentHistoryView` — GET `payments/` with totals.
  - `SupplierDashboardView` updated with `awaiting_payment`, `paid_jobs`, `outstanding_amount`, `paid_amount` fields.
  - `SupplierJobsView` updated to handle `in_progress`, `awaiting_payment`, `paid` filter values.
- `backend/apps/maintenance/views.py` — added `AgentInvoiceApprovalView` (GET/POST `<request_pk>/invoice/`) for agents to approve/reject/mark-paid invoices.
- `backend/apps/maintenance/urls.py` — registered all new endpoints.

**Frontend changes:**

- `admin/src/views/supplier/JobsListView.vue` — replaced the 4-tile stats row with new tiles (New/In Progress/Awaiting Payment/Paid with ZAR amounts). Added 8-tab filter pills. Detail panel now shows: Accept button for awarded+open jobs; status update form with photo upload for in-progress jobs; invoice line-item builder + PDF upload for unsubmitted invoices; read-only invoice status chip for submitted invoices.
- `admin/src/views/supplier/InvoicesView.vue` — new page showing outstanding balance, total paid, and full invoice history with status chips, rejection reasons, EFT references, and PDF links.
- `admin/src/components/SupplierLayout.vue` — added "Invoices" nav item (FileText icon) between Calendar and Profile.
- `admin/src/router/index.ts` — registered `/invoices` route for suppliers.

**Caveats for reviewer:**
- `content/brand/voice.md` does not exist; copy uses direct SA-appropriate language consistent with existing supplier portal strings. The acceptance criterion is marked incomplete.
- Agent-side invoice approval (the `AgentInvoiceApprovalView`) is backend-ready but no Vue component was built for the agent dashboard — that's a separate UX task (the task only asked for the approval *flow*, not an agent UI). A discovery note is warranted but the backend wire is there.
- `SupplierJobSerializer` now prefetches `invoice` via `prefetch_related("quote", "invoice")` in both list and detail views — check query count under load.
- The `isActive('/invoices')` check in `SupplierLayout` will also match `/invoices/xxx` sub-paths (same pattern as existing `/jobs`, `/calendar`, `/profile`).
