---
id: RNT-QUAL-036
stream: rentals
title: "Wire payments views into admin SPA router"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: [RNT-SEC-031]
asana_gid: "1214221444384630"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Register `ReconciliationQueue.vue` and `InvoiceDetail.vue` in the admin SPA router so agents can navigate to the payments UI.

## Acceptance criteria
- [ ] `/payments/` route added to `admin/src/router/index.ts`, renders `ReconciliationQueue.vue`, guarded to agent/admin roles
- [ ] `/payments/invoices/:id` route added, renders `InvoiceDetail.vue`
- [ ] Both routes appear in the admin sidebar nav under a Financials or Payments section
- [ ] Nav guard prevents tenant-role users from accessing the routes
- [ ] Manual smoke: navigate to `/payments/` → reconciliation queue renders; click an invoice → detail view loads

## Files likely touched
- `admin/src/router/index.ts`
- `admin/src/components/AppLayout.vue` (or equivalent sidebar nav component)
- `admin/src/views/payments/ReconciliationQueue.vue`
- `admin/src/views/payments/InvoiceDetail.vue`

## Test plan
**Manual:**
- Log in as agent → sidebar shows Payments link → `/payments/` loads queue
- Click invoice row → `/payments/invoices/<id>` loads detail
- Log in as tenant → `/payments/` redirected or 403

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-22 — Promoted from discovery `2026-04-22-payments-missing-vue-router-wiring.md` found during RNT-QUAL-004 review. Depends on RNT-SEC-031 (role-scoped API) being merged first so the wired UI only exposes appropriately scoped data.
