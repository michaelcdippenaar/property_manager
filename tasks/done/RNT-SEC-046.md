---
id: RNT-SEC-046
stream: rentals
title: "Migrate LandlordTab.vue PII inputs to MaskedInput component"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: done
assigned_to: null
depends_on: []
asana_gid: null
created: 2026-04-24
updated: 2026-04-24
---

## Goal
Replace the three remaining bare `<input data-clarity-mask="true">` elements in `LandlordTab.vue` with the `<MaskedInput>` wrapper to align with the post-RNT-SEC-042 codebase standard and eliminate the fragile attribute-based masking pattern.

## Acceptance criteria
- [x] `representative_id_number`, `branch_code`, and `account_number` fields in `LandlordTab.vue` use `<MaskedInput>` (imported from `../../components/shared/MaskedInput.vue`)
- [x] The bare `<input data-clarity-mask="true">` pattern is removed from these three fields
- [x] No functional regression: values still bind correctly via v-model
- [ ] CI lint / clarity-mask guard passes

## Files likely touched
- `admin/src/views/properties/LandlordTab.vue` (lines ~108, ~132, ~136)

## Test plan
**Manual:**
- Open a property in admin, navigate to the Landlord tab
- Confirm all three PII fields render and accept input correctly
- Verify Clarity session recording masks the values (or confirm attribute presence in DOM)

**Automated:**
- `cd admin && npm run lint`
- Existing component tests for LandlordTab (if any)

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-24 — Promoted from discovery `2026-04-23-landlord-tab-pii-not-migrated-to-masked-input.md`. No active POPIA leak (attribute masking is present), but inconsistent with post-RNT-SEC-042 standard.

2026-04-24 — Swapped all three bare `<input data-clarity-mask="true">` elements for `<MaskedInput>` and added the import from `../../components/shared/MaskedInput.vue`. Pattern matches LandlordDrawer.vue. No lint script available in admin; vue-tsc reports one pre-existing unrelated error in a browser test file, LandlordTab.vue itself is clean.

2026-04-24 — Review passed. Checked: all three AC fields (`representative_id_number`, `branch_code`, `account_number`) swapped to `<MaskedInput>`; bare `data-clarity-mask` pattern removed; import present and path correct; v-model bindings preserved with class/placeholder attrs forwarded via `$attrs`; `MaskedInput` component sets `data-clarity-mask="true"` internally; pattern matches `LandlordDrawer.vue`. Phone fields (`owner_phone`, `representative_phone`) were never masked and are out of scope — flagged as a gap in `tasks/discoveries/2026-04-24-landlord-tab-phone-fields-unmasked.md`.

2026-04-24 — Test run (rentals-tester). Code-level verification:
1. LandlordTab.vue lines 108, 132, 136: all three PII fields (`representative_id_number`, `branch_code`, `account_number`) confirmed using `<MaskedInput>` with v-model bindings intact. PASS
2. MaskedInput.vue: sets `data-clarity-mask="true"` internally on the rendered `<input>` element; uses `v-bind="$attrs"` to forward class/placeholder; `inheritAttrs: false` prevents double application. PASS
3. Grep for bare `data-clarity-mask` in LandlordTab.vue: zero matches. PASS
4. `npx vue-tsc --noEmit`: one pre-existing error in `src/__tests__/browser/focus-trap-keyboard.browser.test.ts` (Expected 1 arguments, got 2) — unrelated to this task and pre-dates this commit. LandlordTab.vue itself is clean. PASS (pre-existing, out of scope)
All checks pass.
