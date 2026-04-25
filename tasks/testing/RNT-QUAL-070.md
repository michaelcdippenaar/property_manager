---
id: RNT-QUAL-070
stream: rentals-quality
title: "Wrap LandlordTab phone fields in MaskedInput for POPIA PII compliance"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214274142746308"
created: 2026-04-24
updated: 2026-04-24
---

## Goal

Replace the two bare `<input>` phone fields in `LandlordTab.vue` with `<MaskedInput>` so phone numbers (PII under POPIA) are masked consistently with the rest of the platform.

## Acceptance criteria

- [x] `admin/src/views/properties/LandlordTab.vue` line 66 (`form.owner_phone`): bare `<input>` replaced with `<MaskedInput>` (or equivalent component carrying `data-clarity-mask`).
- [x] Same file line 112 (`form.representative_phone`): same replacement.
- [ ] Both fields render and submit correctly — no data loss or format regression.
- [ ] Microsoft Clarity (or equivalent session-recording tool) no longer captures raw phone number values for these fields.
- [x] Consistent with the pattern used by other masked fields already in the codebase.

## Files likely touched

- `admin/src/views/properties/LandlordTab.vue` (lines 66, 112)

## Test plan

**Manual:**
- Open a property's Landlord tab in the admin app; enter a phone number; confirm the field is masked in the session-recording tool preview.
- Save the form and confirm the phone number is stored correctly.

**Automated:**
- Visual / component test if available for LandlordTab.

## Handoff notes

Promoted from discovery `2026-04-24-landlord-tab-phone-fields-unmasked.md` (2026-04-24). P2 — out-of-scope follow-up from RNT-SEC-046; POPIA PII compliance for phone fields.

## Handoff notes (2026-04-25)

Implementation already committed in 66ee407f ("fix: mask owner_phone and representative_phone in LandlordTab") by michaelcdippenaar. Both bare `<input>` fields confirmed swapped to `<MaskedInput>` in the diff. Remaining ACs (runtime render/submit verification and Clarity mask confirmation) require manual testing by reviewer.

## Handoff notes (2026-04-25) — Review passed

Checked commit 66ee407f. Both `owner_phone` (line 66) and `representative_phone` (line 112) swapped from bare `<input>` to `<MaskedInput>` with v-model preserved. Pattern matches RNT-SEC-046 (representative_id_number, branch_code, account_number). `vue-tsc --noEmit` shows one pre-existing unrelated error only — no new regressions. Runtime render/submit correctness and Clarity masking confirmation are open ACs for tester.
