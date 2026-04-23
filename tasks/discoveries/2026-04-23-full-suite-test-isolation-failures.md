---
discovered_by: rentals-implementer
discovered_during: RNT-QUAL-023
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found

When running the full `pytest apps/test_hub/` suite (1538 tests), 343 tests fail due to shared state pollution between test modules. All affected tests pass individually in isolation — the failures are purely order-dependent. Running any subset of the affected files alone yields zero failures.

## Why it matters

CI will be unreliable: a green run depends on which subset of tests is executed. Developers cannot trust the full suite result, and regressions may be hidden behind the noise. This makes the suite effectively unusable as a gate until fixed.

## Where I saw it

- Observed during RNT-QUAL-023 smoke-check (`pytest apps/test_hub/ --no-cov -q`)
- Affected modules include: `test_maintenance.py` (44), `test_agent_assist_helpers.py` (31), `test_mandate_services.py` (29), `test_conversations.py` (20), and ~15 other modules — 343 failures total
- All modules pass cleanly when run in isolation

## Suggested acceptance criteria (rough)

- [ ] Identify the test(s) that leak shared state (likely a cache, mock patch, or DB fixture left dirty)
- [ ] Add `tearDown` / fixture cleanup or use `@override_settings` / `cache.clear()` in the offending test class
- [ ] `pytest apps/test_hub/ --no-cov -q` completes with 0 failures

## Why I didn't fix it in the current task

RNT-QUAL-023 was scoped to 15 named failures; this is a separate, much larger isolation problem that would require identifying the pollution source across many modules. Fixing it here would more than double the diff and scope.
