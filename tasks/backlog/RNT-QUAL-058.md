---
id: RNT-QUAL-058
stream: rentals
title: "Unify drift-guard YAML parser boundary-reset logic between script and test"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.1"
status: backlog
assigned_to: null
depends_on: []
asana_gid: null
created: 2026-04-24
updated: 2026-04-24
---

## Goal
Align `check-feature-flag-drift.mjs` and `useFeatureFlags.drift.test.ts` so both parsers share the same feature-block boundary-reset logic, preventing a future edge case where a slug-less block causes the test parser to carry a stale slug forward and produce a false-clean CI result.

## Acceptance criteria
- [ ] Both parsers reset `lastSlug` on encountering a two-space-indented non-comment line (feature block boundary), OR the simpler test-file version has an explicit comment explaining why it is safe without that reset
- [ ] Either extract to a shared helper, or document the intentional difference
- [ ] Existing drift CI check continues to pass

## Files likely touched
- `admin/src/composables/__tests__/useFeatureFlags.drift.test.ts` (lines ~40–53)
- `admin/scripts/check-feature-flag-drift.mjs` (lines ~58–65)

## Test plan
**Automated:**
- `cd admin && npm run test -- useFeatureFlags.drift`
- Add a `features.yaml` fixture entry without a `status:` field and confirm the test parser handles it correctly

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-24 — Promoted from discovery `2026-04-23-drift-guard-parser-divergence.md`. Current YAML is safe (every slug paired with status). Deferred to v1.1 — edge case only materialises if a future feature block omits `status:`.
