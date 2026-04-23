---
id: RNT-SEC-042
stream: rentals
title: "Admin SPA: systematic PII masking wrapper + CI lint rule for Clarity session recording"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214229920415908"
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Introduce a `MaskedInput.vue` wrapper (or `v-mask-pii` directive) that enforces `data-clarity-mask="true"` + `autocomplete="off"` on all PII fields, migrate all ~15 unmasked PII inputs across admin views, and add a CI lint rule so future PII fields cannot be added without masking — preventing POPIA-grade session-recording leaks.

## Acceptance criteria
- [x] `admin/src/composables/useClarity.ts` (or a new `admin/src/composables/piiFields.ts`) documents the canonical list of PII field names: `id_number`, `account_number`, `branch_code`, `trust_account_number`, `representative_id_number`, `passport`
- [x] `MaskedInput.vue` wrapper component (or `v-mask-pii` directive) sets `data-clarity-mask="true"` and `autocomplete="off"` automatically
- [x] All existing PII inputs in the following views are migrated to the wrapper:
  - `admin/src/views/auth/ProfileView.vue` — no canonical PII v-models; password fields already had data-clarity-mask
  - `admin/src/views/properties/LandlordDrawer.vue` — migrated (representative_id_number, account_number, branch_code)
  - `admin/src/views/properties/LandlordDetailView.vue` — migrated (representative_id_number, account_number, branch_code)
  - `admin/src/views/properties/PropertyDetailView.vue` — migrated (id_number)
  - `admin/src/views/admin/AgencySettingsView.vue` — migrated (trust_account_number, trust_branch_code)
  - `admin/src/views/maintenance/SuppliersView.vue` — migrated (account_number, branch_code)
  - `admin/src/views/suppliers/DirectoryView.vue` — migrated (account_number, branch_code)
  - `admin/src/views/supplier/SupplierProfileView.vue` — migrated (account_number, branch_code)
  - `admin/src/views/leases/EditLeaseDrawer.vue` — migrated (id_number × 3)
  - `admin/src/views/leases/LeaseBuilderView.vue` — already uses h() render fn with data-clarity-mask; no v-model on PII
  - `admin/src/views/leases/ImportLeaseWizard.vue` — already uses h() render fn with data-clarity-mask; no v-model on PII
- [x] Grep-based CI check script `admin/scripts/check-pii-masking.sh` wired into `.github/workflows/ci.yml` admin job
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

2026-04-23 (implementer) — Implemented all acceptance criteria:

1. **`admin/src/composables/piiFields.ts`** (new) — canonical list of 6 PII field names with POPIA commentary.
2. **`admin/src/components/shared/MaskedInput.vue`** (new) — drop-in `<input>` wrapper; auto-sets `data-clarity-mask="true"` and `autocomplete="off"` via `$attrs` pass-through and `defineOptions({ inheritAttrs: false })`.
3. **Migrated 8 views** from bare `<input data-clarity-mask="true">` to `<MaskedInput>`: LandlordDrawer, LandlordDetailView, PropertyDetailView, AgencySettingsView, SuppliersView (maintenance), DirectoryView (suppliers), SupplierProfileView, EditLeaseDrawer. LeaseBuilderView and ImportLeaseWizard already used `h()` render functions with `data-clarity-mask` directly — left as-is (CI script allows both patterns). ProfileView has no canonical PII v-models (only password fields, which had masking already).
4. **`admin/scripts/check-pii-masking.sh`** (new, executable) — grep-based CI check; exits 1 if any bare `<input v-model="..<pii_field>..">` is found without `MaskedInput` or `data-clarity-mask`. Smoke-checked locally: `PASS`.
5. **`.github/workflows/ci.yml`** — added "PII masking guard (RNT-SEC-042)" step in the admin job, after drift guard.
6. **`admin/src/composables/useClarity.ts`** — added cross-reference comment to MaskedInput and piiFields.ts.

Pre-existing TS error in browser tests (`focus-trap-keyboard.browser.test.ts`) is unrelated to this task and pre-dates this change.
