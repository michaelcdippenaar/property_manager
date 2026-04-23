---
discovered_by: rentals-reviewer
discovered_during: RNT-QUAL-047
discovered_at: 2026-04-23
priority_hint: P3
suggested_prefix: RNT-QUAL
---

## What I found
The two YAML parsers delivered by RNT-QUAL-047 have divergent feature-block boundary logic. `check-feature-flag-drift.mjs` resets `lastSlug = null` when it encounters a two-space-indented non-comment line (feature block boundary). `useFeatureFlags.drift.test.ts` omits that boundary reset — `lastSlug` only clears when a `status:` line is consumed.

## Why it matters
If any future feature block in `features.yaml` is added without a `status:` field, the test parser will carry the previous block's slug forward and incorrectly classify the next block's `status:` as belonging to that stale slug. The standalone script would handle this correctly. The two implementations are meant to be equivalent guards but will diverge in that edge case, giving a false-clean CI result. Current YAML is safe — every slug is paired with a status before the next slug.

## Where I saw it
- `admin/src/composables/__tests__/useFeatureFlags.drift.test.ts:40-53` — no boundary reset
- `admin/scripts/check-feature-flag-drift.mjs:58-65` — has boundary reset logic

## Suggested acceptance criteria (rough)
- [ ] Both parsers share the same boundary-reset logic (either extract to a shared helper or confirm the simpler test-file version is intentionally less defensive with a comment explaining why it is safe)

## Why I didn't fix it in the current task
Out of scope for review; requires implementer decision on whether to unify parsers or document the intentional difference.
