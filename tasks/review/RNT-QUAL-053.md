---
id: RNT-QUAL-053
stream: rentals
title: "Vault33 test_hub tests: skip cleanly when vault33_client module is absent"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214246262761811"
created: 2026-04-24
updated: 2026-04-24
---

## Goal
Three tests in `apps/test_hub/integrations/unit/test_vault33.py` fail with `ModuleNotFoundError: No module named 'vault33_client'` because vault33 is a separate product not installed in the Rentals dev environment. These tests should skip cleanly (`pytest.importorskip` or a `skipIf` decorator) rather than erroring — to preserve the "0 failures" test baseline for Rentals v1 launch.

## Acceptance criteria
- [x] `apps/test_hub/integrations/unit/test_vault33.py` tests skip with reason "vault33_client not installed" when the module is absent
- [x] No import-time error when running the full test suite without vault33_client installed
- [x] If vault33_client IS installed, tests still run normally
- [x] `cd backend && pytest apps/test_hub/ -v` — 0 errors (skips are acceptable)

## Files likely touched
- `backend/apps/test_hub/integrations/unit/test_vault33.py`

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/integrations/unit/test_vault33.py -v` — should show 3 SKIPPED, 0 ERRORS when vault33_client is absent

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-24 — rentals-pm: Promoted from discovery `2026-04-23-test-hub-remaining-regressions-post-infra-fix.md`. Vault33 is a separate product (out of Rentals v1 scope). Skip pattern is the correct fix — do not install vault33_client as a dev dependency of the Rentals backend.

2026-04-24 — implementer: Added `pytest.importorskip("vault33_client", reason="...")` at the top of `test_vault33.py`, after the `import pytest` line. The module-level `importorskip` causes pytest to skip the entire file's collection when `vault33_client` is absent — `collected 0 items / 1 skipped`, no errors. Confirmed with `pytest apps/test_hub/integrations/unit/test_vault33.py -v`. Note: the code fix was included in the `152a44d0` (GTM-008) commit due to stash/restore interplay during that session — the fix is live in HEAD. This task file commit is the formal task board handoff.
