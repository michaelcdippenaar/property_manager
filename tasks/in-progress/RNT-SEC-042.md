---
id: RNT-SEC-042
stream: rentals
title: "Admin SPA: systematic PII masking wrapper + CI lint rule for Clarity session recording"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214229920415908"
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Introduce a `MaskedInput.vue` wrapper (or `v-mask-pii` directive) that enforces `data-clarity-mask="true"` + `autocomplete="off"` on all PII fields, migrate all ~15 unmasked PII inputs across admin views, and add a CI lint rule so future PII fields cannot be added without masking — preventing POPIA-grade session-recording leaks.

## Acceptance criteria
- [ ] `admin/src/composables/useClarity.ts` (or a new `admin/src/composables/piiFields.ts`) documents the canonical list of PII field names: `id_number`, `account_number`, `branch_code`, `trust_account_number`, `representative_id_number`, `passport`
- [ ] `MaskedInput.vue` wrapper component (or `v-mask-pii` directive) sets `data-clarity-mask="true"` and `autocomplete="off"` automatically
- [ ] All existing PII inputs in the following views are migrated to the wrapper:
  - `admin/src/views/auth/ProfileView.vue`
  - `admin/src/views/properties/LandlordDrawer.vue`
  - `admin/src/views/properties/LandlordDetailView.vue`
  - `admin/src/views/properties/PropertyDetailView.vue`
  - `admin/src/views/admin/AgencySettingsView.vue`
  - `admin/src/views/maintenance/SuppliersView.vue`
  - `admin/src/views/suppliers/DirectoryView.vue`
  - `admin/src/views/supplier/SupplierProfileView.vue`
  - `admin/src/views/leases/EditLeaseDrawer.vue`
  - `admin/src/views/leases/LeaseBuilderView.vue`
  - `admin/src/views/leases/ImportLeaseWizard.vue`
- [ ] ESLint rule (or grep-based CI check script) fails the build/CI step if `v-model` references a known-PII field name without `data-clarity-mask` or the `MaskedInput` wrapper
- [ ] No regression: all affected views render correctly in dev mode; no new console errors

## Files likely touched
- `admin/src/components/shared/MaskedInput.vue` (new)
- `admin/src/composables/useClarity.ts`
- `admin/src/views/auth/ProfileView.vue`
- `admin/src/views/properties/LandlordDrawer.vue`
- `admin/src/views/properties/LandlordDetailView.vue`
- `admin/src/views/properties/PropertyDetailView.vue`
- `admin/src/views/admin/AgencySettingsView.vue`
- `admin/src/views/maintenance/SuppliersView.vue`
- `admin/src/views/suppliers/DirectoryView.vue`
- `admin/src/views/supplier/SupplierProfileView.vue`
- `admin/src/views/leases/EditLeaseDrawer.vue`
- `admin/src/views/leases/LeaseBuilderView.vue`
- `admin/src/views/leases/ImportLeaseWizard.vue`
- `.eslintrc.js` or `scripts/check-pii-masking.sh` (CI check)

## Test plan
**Manual:**
- Open each affected view in staging with Clarity loaded; confirm PII inputs do not appear in session recordings
- Add a new PII field without the wrapper and confirm the CI check fails

**Automated:**
- `cd admin && npm run lint` — ESLint/CI check must flag any bare `v-model="id_number"` (etc.) without masking
- Visual regression: each affected view loads without JS errors in dev

## Handoff notes
2026-04-23 — Promoted from discovery `2026-04-23-admin-pii-mask-audit.md` (found by rentals-reviewer during UX-006). UX-006 ships the Clarity harness; this task owns the system-level masking contract across the full admin SPA.
