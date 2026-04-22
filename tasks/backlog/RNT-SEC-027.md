---
id: RNT-SEC-027
stream: rentals
title: "Harden @requires_feature decorator: fail loudly when request cannot be resolved"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214200629201021"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Prevent the `@requires_feature` decorator from silently passing tier gates when it cannot locate the DRF Request in a non-standard view signature, replacing the `else: request = None` branch with an explicit failure.

## Acceptance criteria
- [ ] When the decorator cannot identify the request, raise `ImproperlyConfigured` in DEBUG mode and return HTTP 500 in production (no silent pass-through)
- [ ] A test applies the decorator to a view with an unexpected signature and asserts it does not silently grant feature access
- [ ] All existing `@requires_feature` call sites continue to function correctly
- [ ] Alternatively: refactor the decorator to use a known request-resolver (fixed kwarg or `request.parser_context`) rather than isinstance duck-typing

## Files likely touched
- `backend/apps/accounts/decorators.py`
- `backend/apps/test_hub/accounts/` (new test)

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/accounts/ -k requires_feature`

## Handoff notes
Promoted from discovery `2026-04-22-requires-feature-request-detection.md` (found during OPS-007). Latent privilege-escalation vector as more features are tier-gated.
