---
id: RNT-QUAL-004
stream: rentals
title: "Rent reconciliation edge cases: partial, overpayment, reversal, unmatched"
feature: rent_payment_tracking
lifecycle_stage: 10
priority: P1
effort: M
v1_phase: "1.0"
status: backlog
asana_gid: "1214177452054690"
assigned_to: null
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Today the rent-tracking engine handles the happy path (one payment, matches expected amount). Handle the realistic edge cases so agents don't chase false "unpaid" alerts.

## Acceptance criteria
- [ ] Partial payment: mark invoice `partially_paid`, remaining balance visible, reminder copy references remaining amount
- [ ] Overpayment: credit balance rolls into next cycle; operator sees "tenant in credit" flag
- [ ] Reversal / bounced EFT: invoice reverts to `unpaid`, tenant + agent notified
- [ ] Unmatched deposit (wrong reference): quarantined to "needs reconciliation" queue; operator can manually assign
- [ ] Split payment from two sources (tenant + guarantor): aggregated under same invoice
- [ ] Audit trail: every state change logged (ties to RNT-SEC-008)

## Files likely touched
- `backend/apps/payments/reconciliation.py`
- `backend/apps/payments/models.py` (state machine)
- `admin/src/views/payments/ReconciliationQueue.vue`
- `admin/src/views/payments/InvoiceDetail.vue`

## Test plan
**Automated:**
- `pytest backend/apps/payments/tests/test_reconciliation_edges.py` — covers each edge case

## Handoff notes
