---
discovered_by: rentals-reviewer
discovered_during: RNT-SEC-042
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-SEC
---

## What I found
`admin/src/views/properties/LandlordTab.vue` has three bare `<input data-clarity-mask="true">` bindings on PII fields (`representative_id_number`, `branch_code`, `account_number`) that were not migrated to `<MaskedInput>` in RNT-SEC-042.

## Why it matters
The inputs are functionally masked today (they carry `data-clarity-mask="true"`), so there is no active POPIA leak. However, the file is inconsistent with the rest of the codebase post-RNT-SEC-042: it uses the old bare-input pattern rather than the new `<MaskedInput>` wrapper. If anyone edits these inputs and removes the attribute (e.g. copy-paste refactor), the CI guard will not catch it because the guard only checks for bare `<input v-model=...>` without `data-clarity-mask`, and the old pattern satisfies that check. The wrapper is the forward-compatible approach.

## Where I saw it
- `admin/src/views/properties/LandlordTab.vue:108` — `representative_id_number`
- `admin/src/views/properties/LandlordTab.vue:132` — `branch_code`
- `admin/src/views/properties/LandlordTab.vue:136` — `account_number`

## Suggested acceptance criteria (rough)
- [ ] Replace the three bare `<input data-clarity-mask="true">` on PII fields in `LandlordTab.vue` with `<MaskedInput>`
- [ ] Import `MaskedInput` from `../../components/shared/MaskedInput.vue` in the file

## Why I didn't fix it in the current task
Out of scope for RNT-SEC-042 as noted by the implementer. The inputs are currently masked so there is no active leak — this is a consistency/hardening cleanup.
