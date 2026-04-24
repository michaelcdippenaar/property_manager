---
id: discovery
discovered_by: reviewer
discovered_in: RNT-SEC-046
date: 2026-04-24
severity: low
---

## Summary
`LandlordTab.vue` has two phone fields — `form.owner_phone` (line 66) and `form.representative_phone` (line 112) — rendered as bare `<input>` elements with no `data-clarity-mask` attribute and no `<MaskedInput>` wrapper. Phone numbers are PII under POPIA. They were out of scope for RNT-SEC-046 (which targeted only fields that already carried the attribute), but should be migrated to `<MaskedInput>` for consistency and compliance.

## Suggested action
Create a follow-up task to replace these two fields with `<MaskedInput>` in `admin/src/views/properties/LandlordTab.vue`.
