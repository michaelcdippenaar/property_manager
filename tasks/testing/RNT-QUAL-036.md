---
id: RNT-QUAL-036
stream: rentals
title: "Wire payments views into admin SPA router"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: testing
assigned_to: null
depends_on: [RNT-SEC-031]
asana_gid: "1214221444384630"
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Register `ReconciliationQueue.vue` and `InvoiceDetail.vue` in the admin SPA router so agents can navigate to the payments UI.

## Acceptance criteria
- [x] `/payments/` route added to `admin/src/router/index.ts`, renders `ReconciliationQueue.vue`, guarded to agent/admin roles
- [x] `/payments/invoices/:id` route added, renders `InvoiceDetail.vue`
- [x] Both routes appear in the admin sidebar nav under a Financials or Payments section
- [x] Nav guard prevents tenant-role users from accessing the routes
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

2026-04-23 — Implemented by rentals-implementer. Two child routes added under the existing AppLayout parent at `/payments` (ReconciliationQueue.vue) and `/payments/invoices/:id` (InvoiceDetail.vue). Both child routes carry `meta.roles` restricted to agent/admin/agency_admin/estate_agent/managing_agent/accountant — the nav guard already uses `to.meta.roles` with child-overrides-parent semantics so viewer and tenant roles are redirected. A "Financials" dropdown section added to `primaryNav` in AppLayout.vue (conditionally rendered via `canSeePayments` computed, same role list) containing the Reconciliation Queue entry; the `Banknote` icon imported from lucide-vue-next. Build (`npm run build`) passes in 8.4 s with no new errors. Manual smoke (actual navigate + click) is left for the tester.

2026-04-23 — Review passed. Checked: (1) both routes present in `admin/src/router/index.ts` as children of the AppLayout parent, correct lazy-import paths, `meta.roles` correctly excludes viewer/tenant; (2) `beforeEach` guard at line 244 reads `to.meta.roles` — Vue Router 4 child-overrides-parent semantics confirmed, so viewer blocked despite parent allowing it; (3) "Financials" `NavSection` conditionally pushed in `primaryNav` computed via `canSeePayments`, role list matches route meta; (4) InvoiceDetail not in sidebar (drill-down by :id — correct UX, test plan confirms click-row flow); (5) no new API endpoints, no PII, no raw SQL — POPIA/security pass clean; (6) both view files exist. No issues found.

2026-04-23 — Test run (rentals-tester). Static checks PASS: both routes confirmed in `admin/src/router/index.ts` (lines 147-157) with correct `meta.roles`; `beforeEach` guard at line 244 enforces role list; `canSeePayments` computed in AppLayout.vue correctly gates the Financials nav section; both `ReconciliationQueue.vue` and `InvoiceDetail.vue` exist. Vite dev server started and returned HTTP 200. Manual smoke test BLOCKED: backend `POST /api/v1/auth/login/` returns HTTP 500 with `ProgrammingError: column accounts_user.seen_welcome_at does not exist` — unapplied migration prevents login, making all browser-level smoke checks impossible. Discovery filed: `tasks/discoveries/2026-04-23-accounts-missing-seen-welcome-at-migration.md`. Task blocked pending migration fix.

## Reconciliation note (2026-04-23)
Unblocked during reconciliation pass. Original blocking reason: `POST /api/v1/auth/login/` returned HTTP 500 (`ProgrammingError: column accounts_user.seen_welcome_at does not exist`). This migration has since been confirmed applied — column exists in dev DB. All code ACs confirmed [x] by reviewer. Routes wired, nav guard enforced, both view files exist.
Moved from blocked → testing. Remaining: manual smoke — navigate to `/payments/` as agent → reconciliation queue renders; click invoice → detail view loads; tenant role redirected.
