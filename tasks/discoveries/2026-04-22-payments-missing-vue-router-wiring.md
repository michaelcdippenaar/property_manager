---
discovered_by: rentals-reviewer
discovered_during: RNT-QUAL-004
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found
`ReconciliationQueue.vue` and `InvoiceDetail.vue` exist but are not wired into `admin/src/router/index.ts`. The implementer flagged this in handoff notes as a known caveat.

## Why it matters
The payments views are unreachable in the admin SPA. Agents cannot use the reconciliation UI until routes `/payments/` and `/payments/invoices/:id` are added to the router.

## Where I saw it
- `admin/src/views/payments/ReconciliationQueue.vue`
- `admin/src/views/payments/InvoiceDetail.vue`
- `admin/src/router/index.ts` (missing routes)

## Suggested acceptance criteria (rough)
- [ ] `/payments/` route added, renders `ReconciliationQueue.vue`, requires `IsAgentOrAdmin`-equivalent nav guard
- [ ] `/payments/invoices/:id` route added, renders `InvoiceDetail.vue`
- [ ] Routes appear in the admin sidebar nav under Financials or Payments

## Why I didn't fix it in the current task
Out of scope; the implementer explicitly noted it as a follow-on. Backend API is functional.
