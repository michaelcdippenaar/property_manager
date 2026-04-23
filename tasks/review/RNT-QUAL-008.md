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
updated: 2026-04-24
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

### 2026-04-23 — reviewer: changes requested

Two mandatory fixes before this can go to testing.

**Fix 1 — File upload: no size or MIME-type validation (security)**

`SupplierInvoiceSubmitSerializer` (`backend/apps/maintenance/supplier_serializers.py`, class `SupplierInvoiceSubmitSerializer`, field `invoice_file`) has no `validate_invoice_file` method and no `validators` on the model's `FileField`. Same gap for the `photo` field in `SupplierJobStatusUpdateView` (`backend/apps/maintenance/supplier_views.py`, line where `photo = request.FILES.get("photo")` is accepted). An authenticated supplier can upload files of arbitrary type or size through both endpoints.

Required: add a `validate_invoice_file` method to `SupplierInvoiceSubmitSerializer` that (a) rejects MIME types outside `application/pdf` and `image/*` and (b) rejects files larger than a reasonable cap (suggest 10 MB). Add the same checks (inline in the view or via a shared validator) for the status-update `photo` field (images only, same size cap). A custom DRF `FileField` subclass or a standalone validator function is fine — just needs to be called before `save()`.

**Fix 2 — State machine: `reject` action has no status guard**

`AgentInvoiceApprovalView.post()` (`backend/apps/maintenance/views.py`, `elif action_name == "reject":` branch) writes `status=REJECTED` with no check on the current invoice status. An agent can call `action=reject` on an invoice that is already `approved` or `paid`, which corrupts the status trail and overwrites `reviewed_by`.

Required: add the same style of guard that `approve` and `paid` already have:
```python
if invoice.status != SupplierInvoice.Status.PENDING:
    return Response({"detail": "Only pending invoices can be rejected"}, status=status.HTTP_400_BAD_REQUEST)
```

No other blocking issues found. The following checked out:
- Migration 0016: `CreateModel` only, fully reversible.
- IDOR on invoice submission: `_get_qr` filters `.get(id=pk, supplier=supplier)` — correct.
- `AgentInvoiceApprovalView` permission: `IsAgentOrAdmin` confirmed.
- `approve` and `paid` transitions: guards are correct.
- Frontend job and invoice scoping: both hit supplier-scoped backend endpoints.
- POPIA/PII: activity log messages contain only job amounts and `display_name`, not raw personal data.
- ORM usage: no raw SQL.

Note: `pytest apps/maintenance/ -xvs` could not be executed (test DB locked by another session). Please ensure the suite is green before resubmitting. No new tests were added for `SupplierInvoice`, `SupplierInvoiceView`, or `AgentInvoiceApprovalView`. Consider adding at least a smoke test for each once the two fixes above are in.

### 2026-04-24 — implementer (reviewer fixes pass 2)

**Fix 1 — File upload validation:**

- `backend/apps/maintenance/supplier_serializers.py` — added `_validate_file()` helper (shared, module-level) that checks MIME type against `application/pdf` and `image/*` prefixes, and rejects files larger than 10 MB. Added `validate_invoice_file` method to `SupplierInvoiceSubmitSerializer` that delegates to this helper (PDF + images allowed).
- `backend/apps/maintenance/supplier_views.py` — imported `_validate_file`; in `SupplierJobStatusUpdateView.post()`, after `photo = request.FILES.get("photo")`, added an inline guard that calls `_validate_file(photo, allow_pdf=False, allow_images=True)` and returns a 400 with the validation message if it raises.

**Fix 2 — Reject action status guard:**

- `backend/apps/maintenance/views.py` — in `AgentInvoiceApprovalView.post()`, `elif action_name == "reject":` branch, added guard before state mutation: returns 400 `"Only pending invoices can be rejected"` if `invoice.status != SupplierInvoice.Status.PENDING`.

**Tests:**

- `backend/apps/maintenance/tests/test_supplier_invoice.py` — new file with 15 integration tests covering:
  - approve: pending succeeds, non-pending returns 400
  - reject: pending succeeds, approved/paid returns 400 (Fix 2 guard), missing reason returns 400
  - paid: approved succeeds, non-approved returns 400
  - invoice_file: PDF accepted, image accepted, wrong MIME rejected, oversized rejected
  - status-update photo: non-image MIME rejected, image accepted

`pytest apps/maintenance/ -xvs` — **35 passed** (all maintenance tests, including 15 new). Coverage warnings are pre-existing (stale `.coverage` file, unrelated to this task).
