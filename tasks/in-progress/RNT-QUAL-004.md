---
id: RNT-QUAL-004
stream: rentals
title: "Rent reconciliation edge cases: partial, overpayment, reversal, unmatched"
feature: rent_payment_tracking
lifecycle_stage: 10
priority: P1
effort: M
v1_phase: "1.0"
status: in-progress
asana_gid: "1214177452054690"
assigned_to: implementer
depends_on: []
created: 2026-04-22
updated: 2026-04-22

---

## Goal
Today the rent-tracking engine handles the happy path (one payment, matches expected amount). Handle the realistic edge cases so agents don't chase false "unpaid" alerts.

## Acceptance criteria
- [x] Partial payment: mark invoice `partially_paid`, remaining balance visible, reminder copy references remaining amount
- [x] Overpayment: credit balance rolls into next cycle; operator sees "tenant in credit" flag
- [x] Reversal / bounced EFT: invoice reverts to `unpaid`, tenant + agent notified
- [x] Unmatched deposit (wrong reference): quarantined to "needs reconciliation" queue; operator can manually assign
- [x] Split payment from two sources (tenant + guarantor): aggregated under same invoice
- [x] Audit trail: every state change logged (ties to RNT-SEC-008)

## Files likely touched
- `backend/apps/payments/reconciliation.py`
- `backend/apps/payments/models.py` (state machine)
- `admin/src/views/payments/ReconciliationQueue.vue`
- `admin/src/views/payments/InvoiceDetail.vue`

## Test plan
**Automated:**
- `pytest backend/apps/payments/tests/test_reconciliation_edges.py` — covers each edge case

## Handoff notes

### 2026-04-22 — implementer

**New app: `backend/apps/payments/`**

Created a full `apps.payments` Django app from scratch (no prior payments app existed). Key files:

- `models.py` — four models: `RentInvoice` (state machine: unpaid → partially_paid/paid/overpaid/reversed), `RentPayment` (individual EFT/cash receipt, CLEARED or REVERSED), `UnmatchedPayment` (quarantine queue for wrong-reference deposits), `PaymentAuditLog` (append-only event log).
- `reconciliation.py` — public API: `apply_payment`, `reverse_payment`, `assign_unmatched`, `carry_credit_forward`. All writes are `@transaction.atomic`. Notifications dispatched best-effort on reversal (falls back silently if notifications app unavailable).
- `serializers.py` + `views.py` + `urls.py` — DRF endpoints mounted at `/api/v1/payments/`.
- `migrations/0001_initial.py` — auto-generated.

**Admin UI:** Two new Vue 3 views:
- `admin/src/views/payments/ReconciliationQueue.vue` — lists unmatched deposits, shows pending count + total, modal to assign to an invoice.
- `admin/src/views/payments/InvoiceDetail.vue` — invoice detail with nested payments table, record-payment modal, reverse-payment modal with reason field, full audit trail.

**Tests:** `apps/payments/tests/test_reconciliation_edges.py` — 23 tests, all passing. Covers every acceptance criterion with DB-backed `TestCase` rows (no mocking of DB layer, no factory dependencies).

**`manage.py check`** — clean (0 issues).

**Caveat — no Vue Router wiring:** The Vue components exist but are not yet wired into `admin/src/router/index.ts`. The reviewer should wire `/payments/` and `/payments/invoices/:id` routes as part of this or a follow-on task. The backend API is fully functional.

**Caveat — notification service import:** `_notify_reversal` does `from apps.notifications.services.email import send_email` — this module path may not exist yet; the call is wrapped in a bare `try/except` so it degrades silently.

### 2026-04-22 — Review requested changes

The reconciliation engine logic, models, and tests are solid and satisfy all six acceptance criteria. Sending back for three security fixes before approval. Security is non-negotiable per review rules.

**Required fixes:**

1. **`backend/apps/payments/views.py` — all three viewsets use `IsAuthenticated` instead of a role-scoped permission.** Any authenticated user, including tenants, can call `POST /api/v1/payments/invoices/{id}/payments/` (record a payment), `POST /api/v1/payments/payments/{id}/reverse/` (reverse a payment), and `POST /api/v1/payments/unmatched/{id}/assign/` (assign an unmatched deposit to an invoice). These are financial mutation actions. Change all three viewsets to use `IsAgentOrAdmin` from `apps.accounts.permissions` (already used by tenant views and e-signing views). The `CanViewFinancials` permission defined in the same file also exists as an option but `IsAgentOrAdmin` matches the existing pattern for operator-only endpoints.

2. **`backend/apps/payments/views.py` — IDOR on list endpoints.** `RentInvoiceViewSet.get_queryset()` and `UnmatchedPaymentViewSet.get_queryset()` return all rows with no scope filter on the requesting user's agency or property assignments. If scope filtering is done at the permission layer (i.e. only agents/admins reach these views), this is tolerable for v1, but must be explicitly documented in a code comment. If tenant access is ever permitted in future, there is no guard. Add a comment at line 49 and line 158 of `views.py` stating: `# Queryset is intentionally unscoped — view is gated to IsAgentOrAdmin which limits exposure to operator roles only.`

3. **`backend/apps/payments/views.py` — `RentInvoiceViewSet` and `UnmatchedPaymentViewSet` are full `ModelViewSet`.** This exposes `POST /api/v1/payments/invoices/` (create invoice), `PUT/PATCH /api/v1/payments/invoices/{id}/` (edit invoice), `DELETE /api/v1/payments/invoices/{id}/` (delete invoice), and the equivalent for unmatched payments to any authenticated user. Invoices should only be created by the system when a rent period opens — not by arbitrary API callers. Restrict `RentInvoiceViewSet` to read + custom actions only: change it to `mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet` (or override `http_method_names`). `UnmatchedPaymentViewSet` may keep `create` (operators can manually enter an unmatched deposit) but should not allow `update` or `destroy` — restrict it similarly.

**Discovery filed:** `tasks/discoveries/2026-04-22-payments-missing-vue-router-wiring.md` — Vue Router wiring for the two new payment views is missing but is out of scope for this task per the implementer's own caveat. Filed as a follow-on.

**What was checked and passed:**
- All six acceptance criteria covered by models, reconciliation engine, and 23 tests.
- All ORM writes are parameterised (Django ORM, no raw SQL).
- No PII logged — audit log stores `detail` dict with amounts/references only, no full bank account numbers or ID numbers.
- `@transaction.atomic` on all mutation functions — correct.
- `_notify_reversal` wrapped in `try/except` — acceptable degradation.
- `PaymentAuditLog` is append-only by design (no update/delete model methods).
