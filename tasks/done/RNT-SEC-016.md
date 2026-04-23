---
id: RNT-SEC-016
stream: rentals
title: "Harden @requires_feature decorator: fail-safe when request cannot be identified"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: done
assigned_to: null
depends_on: []
asana_gid: "1214229863091491"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Replace the silent pass-through (`else: request = None`) in `@requires_feature` with a fail-safe so views with non-standard signatures do not silently bypass the tier gate.

## Acceptance criteria
- [ ] When `@requires_feature` cannot identify the request object, it raises `ImproperlyConfigured` in DEBUG mode and returns HTTP 500 in production rather than silently passing through
- [ ] A test applies the decorator to a view with an unexpected signature and asserts it does not silently pass (returns 500 or raises `ImproperlyConfigured`)
- [ ] All existing `@requires_feature` call sites continue to work correctly (no regressions)
- [ ] Alternatively: refactor the decorator to rely on a known request-resolver (fixed kwarg position or `request.parser_context`) rather than isinstance duck-typing — document the chosen approach

## Files likely touched
- `backend/apps/accounts/decorators.py` (lines 65–67)
- `backend/apps/test_hub/accounts/unit/test_decorators.py` (new or updated tests)

## Test plan
**Manual:**
- Apply `@requires_feature("some_feature")` to a view with an extra positional arg; call it; expect 500 (not silent pass)

**Automated:**
- `cd backend && pytest apps/test_hub/accounts/ -k requires_feature -v`

## Handoff notes
Promoted from discovery: `2026-04-22-requires-feature-request-detection.md` (OPS-007). Latent privilege-escalation — any future view with a non-standard signature will bypass tier gating silently.

### 2026-04-23 — rentals-pm

Duplicate of RNT-SEC-027, already shipped. Decorator raises `ImproperlyConfigured` in DEBUG / returns HTTP 500 in production; 9/9 unit tests pass. Closing as duplicate.
