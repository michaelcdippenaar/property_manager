---
id: RNT-QUAL-047
stream: rentals
title: "Feature-flag drift guard — CI test asserting PLANNED_FEATURES Set matches features.yaml"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214235807685706"
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Add an automated CI guard that detects drift between the static `PLANNED_FEATURES` Set in `useFeatureFlags.ts` and the canonical `content/product/features.yaml`, eliminating the class of bug where UI gates silently show planned features as live.

## Acceptance criteria
- [x] A Vitest or Node script parses `content/product/features.yaml`, collects every slug with `status: PLANNED`, and asserts set-equality against `PLANNED_FEATURES` in `admin/src/composables/useFeatureFlags.ts`
- [x] Test fails loudly with a human-readable diff (which slugs are missing or extra) on any drift
- [x] Test runs in CI (added to the admin test step)
- [x] Alternative considered: if the team decides to generate the Set from YAML at build time instead of a test guard, that implementation satisfies this ticket; document the decision in Handoff notes
- [x] No regression on existing feature-flag behaviour

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

2026-04-23 implementer: Chose test-guard approach over build-time codegen. Rationale: codegen would import YAML into the bundle at build time, adding a runtime dependency and potentially leaking internal status metadata to the browser. The static Set in useFeatureFlags.ts is intentional (see comments in that file) — the test guard adds the discipline without changing the runtime model.

Delivered two complementary artefacts:
1. `admin/src/composables/__tests__/useFeatureFlags.drift.test.ts` — Vitest node-environment test (3 assertions: no missing slugs, no extra slugs, set sizes match). Runs via `npm run test:drift`.
2. `admin/scripts/check-feature-flag-drift.mjs` — zero-dependency Node.js script for local dev use (`node admin/scripts/check-feature-flag-drift.mjs` from repo root).

Both use a line-scan parser against features.yaml (no external YAML lib needed). Both produce human-readable diffs identifying missing (+) and extra (-) slugs on failure — smoke-tested both cases against the live repo.

CI wired in `.github/workflows/ci.yml` admin job: added `Feature-flag drift guard (RNT-QUAL-047)` step running `npm run test:drift` after the existing Vitest browser tests. Also added `admin/vitest.node.config.ts` for node-environment test config (separate from the browser Playwright config).

Current state: 21 slugs in sync between features.yaml and PLANNED_FEATURES. `useFeatureFlags.ts` itself was not modified — no regression risk to existing feature-flag behaviour.
