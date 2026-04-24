---
id: RNT-SEC-046
stream: rentals
title: "Migrate LandlordTab.vue PII inputs to MaskedInput component"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: null
created: 2026-04-24
updated: 2026-04-24
---

## Goal
Replace the three remaining bare `<input data-clarity-mask="true">` elements in `LandlordTab.vue` with the `<MaskedInput>` wrapper to align with the post-RNT-SEC-042 codebase standard and eliminate the fragile attribute-based masking pattern.

## Acceptance criteria
- [ ] `representative_id_number`, `branch_code`, and `account_number` fields in `LandlordTab.vue` use `<MaskedInput>` (imported from `../../components/shared/MaskedInput.vue`)
- [ ] The bare `<input data-clarity-mask="true">` pattern is removed from these three fields
- [ ] No functional regression: values still bind correctly via v-model
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
