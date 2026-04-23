---
discovered_by: rentals-reviewer
discovered_during: UX-006
discovered_at: 2026-04-23
priority_hint: P1
suggested_prefix: RNT-SEC
---

## What I found
The admin SPA has no systematic guard to prevent PII inputs from being added without `data-clarity-mask`. UX-006 masked ~10 inputs by hand; at least 15 other SA ID, passport, bank-account, branch-code, trust-account, and password inputs across tenant/landlord/lease/supplier/agency-settings flows remain unmasked. Every new view with a PII field is a future POPIA leak into session recording.

## Why it matters
Once Clarity is live on staging (and eventually production), a single forgotten `data-clarity-mask` attribute on a new view will surface real SA IDs, passports, or bank account numbers in session replays — POPIA breach + reputational risk. Per-view manual edits do not scale.

## Where I saw it
- UX-006 review: ~15 unmasked PII inputs across `admin/src/views/auth/ProfileView.vue`, `admin/src/views/properties/LandlordDrawer.vue`, `admin/src/views/properties/LandlordDetailView.vue`, `admin/src/views/properties/PropertyDetailView.vue`, `admin/src/views/admin/AgencySettingsView.vue`, `admin/src/views/maintenance/SuppliersView.vue`, `admin/src/views/suppliers/DirectoryView.vue`, `admin/src/views/supplier/SupplierProfileView.vue`, `admin/src/views/leases/EditLeaseDrawer.vue`, `admin/src/views/leases/LeaseBuilderView.vue`, `admin/src/views/leases/ImportLeaseWizard.vue`

## Suggested acceptance criteria (rough)
- [ ] A `MaskedInput.vue` wrapper (or `v-mask-pii` directive) that sets `data-clarity-mask="true"` + `autocomplete="off"` once at the source
- [ ] Migrate all existing PII inputs (SA ID, passport, bank account, branch code, trust account, password) to the wrapper
- [ ] ESLint rule (or grep-based CI check) that fails the build if `v-model` references a known-PII field name (`id_number`, `account_number`, `branch_code`, `trust_account_number`, `representative_id_number`, `passport`) without either `data-clarity-mask` or using the `MaskedInput` wrapper
- [ ] Documented list of PII field names in `admin/src/composables/useClarity.ts` comment block

## Why I didn't fix it in the current task
Out of scope — UX-006 ships the Clarity harness itself. A system-level masking contract is its own task (wrapper component + codebase-wide migration + CI lint rule) that would triple the UX-006 diff and delay the UAT session.
