---
id: RNT-QUAL-047
stream: rentals
title: "Feature-flag drift guard — CI test asserting PLANNED_FEATURES Set matches features.yaml"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214235807685706"
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Add an automated CI guard that detects drift between the static `PLANNED_FEATURES` Set in `useFeatureFlags.ts` and the canonical `content/product/features.yaml`, eliminating the class of bug where UI gates silently show planned features as live.

## Acceptance criteria
- [ ] A Vitest or Node script parses `content/product/features.yaml`, collects every slug with `status: PLANNED`, and asserts set-equality against `PLANNED_FEATURES` in `admin/src/composables/useFeatureFlags.ts`
- [ ] Test fails loudly with a human-readable diff (which slugs are missing or extra) on any drift
- [ ] Test runs in CI (added to the admin test step)
- [ ] Alternative considered: if the team decides to generate the Set from YAML at build time instead of a test guard, that implementation satisfies this ticket; document the decision in Handoff notes
- [ ] No regression on existing feature-flag behaviour

## Files likely touched
- `admin/src/composables/useFeatureFlags.ts` — lines 41-66 (static `PLANNED_FEATURES` Set)
- `content/product/features.yaml` — source of truth
- `admin/src/composables/__tests__/useFeatureFlags.drift.test.ts` — new test file (or equivalent)
- `.github/workflows/` or CI config — ensure test step runs

## Test plan
**Manual:**
- Temporarily add a fake PLANNED slug to `features.yaml` without updating `useFeatureFlags.ts`; run test; confirm failure with diff
- Restore `features.yaml`; confirm test passes

**Automated:**
- `cd admin && npx vitest run src/composables/__tests__/useFeatureFlags.drift.test.ts`

## Handoff notes
2026-04-23 rentals-pm: Promoted from discovery `2026-04-23-feature-flag-drift-guard.md` (found during UX-009 review). P2 — removes a class of silent bug. Implementer should evaluate build-time codegen vs. test guard and document choice.
