---
discovered_by: rentals-reviewer
discovered_during: UX-009
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found
`admin/src/composables/useFeatureFlags.ts` maintains a static `PLANNED_FEATURES` Set hand-copied from `content/product/features.yaml`. There is no automated check that the two stay in sync — if a feature flips BUILT → PLANNED (or vice versa) in `features.yaml` and nobody updates the composable, UI gates silently drift.

## Why it matters
UX-009 was itself triggered by a drift incident (a PLANNED feature exposed as a live CTA). The convention now depends on implementer discipline at two write sites. A simple CI/unit guard removes the class of bug entirely.

## Where I saw it
- `admin/src/composables/useFeatureFlags.ts:41-66` (static Set)
- `content/product/features.yaml` (source of truth)
- UX-009 acceptance criteria originally hinted at a lint/test guard but shipped without one.

## Suggested acceptance criteria (rough)
- [ ] A Vitest/Node script parses `content/product/features.yaml`, collects every slug whose status is `PLANNED`, and asserts set-equality against `PLANNED_FEATURES` in `useFeatureFlags.ts`.
- [ ] Test runs in CI and fails loudly with a diff on drift.
- [ ] Alternative considered and rejected (or preferred): import/parse YAML at build time and generate the Set — eliminates the dual write site entirely.

## Why I didn't fix it in the current task
Out of scope for a P0 ship-blocker; belongs in a QUAL ticket so the fix can be discussed (static-guard test vs. build-time codegen) without delaying the gate.
