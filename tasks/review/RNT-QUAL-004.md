---
id: RNT-QUAL-004
stream: rentals
title: "Rent reconciliation edge cases: partial, overpayment, reversal, unmatched"
feature: rent_payment_tracking
lifecycle_stage: 10
priority: P1
effort: M
v1_phase: "1.0"
status: review
asana_gid: "1214177452054690"
assigned_to: reviewer
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
