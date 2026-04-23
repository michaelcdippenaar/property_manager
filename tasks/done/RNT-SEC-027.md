---
id: RNT-SEC-027
stream: rentals
title: "Harden @requires_feature decorator: fail loudly when request cannot be resolved"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: done
assigned_to: null
depends_on: []
asana_gid: "1214200629201021"
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Prevent the `@requires_feature` decorator from silently passing tier gates when it cannot locate the DRF Request in a non-standard view signature, replacing the `else: request = None` branch with an explicit failure.

## Acceptance criteria
- [x] When the decorator cannot identify the request, raise `ImproperlyConfigured` in DEBUG mode and return HTTP 500 in production (no silent pass-through)
- [x] A test applies the decorator to a view with an unexpected signature and asserts it does not silently grant feature access
- [x] All existing `@requires_feature` call sites continue to function correctly
- [x] Alternatively: refactor the decorator to use a known request-resolver (fixed kwarg or `request.parser_context`) rather than isinstance duck-typing

## Files likely touched
- `backend/apps/accounts/decorators.py`
- `backend/apps/test_hub/accounts/` (new test)

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/accounts/ -k requires_feature`

## Handoff notes
Promoted from discovery `2026-04-22-requires-feature-request-detection.md` (found during OPS-007). Latent privilege-escalation vector as more features are tier-gated.

**2026-04-23 — implementer**

The decorator in `backend/apps/accounts/decorators.py` already contained the hardened `else` branch (no silent pass-through); it raises `ImproperlyConfigured` when `DEBUG=True` and returns HTTP 500 otherwise. No changes to the decorator were required.

Added 9 unit tests in `backend/apps/test_hub/accounts/unit/test_requires_feature_decorator.py` covering:
- `TestUnresolvableRequest` (4 tests): DEBUG/production paths both raise/return-500 and do NOT call the view body.
- `TestFBVConvention` (2 tests): allowed feature calls through; blocked feature returns 402 with correct payload.
- `TestCBVConvention` (3 tests): allowed/blocked CBV method; CBV with unexpected args also does not silently grant.

All 9 tests pass (`pytest apps/test_hub/accounts/ -k requires_feature`). No DB fixtures required — pure unit tests using `unittest.mock`.

**2026-04-23 — reviewer (approved)**

Checked: decorator source (`backend/apps/accounts/decorators.py`) confirms the hardened `else` branch is live — raises `ImproperlyConfigured` in DEBUG, returns HTTP 500 in production, and does not call the view body in either path. All 9 tests in `test_requires_feature_decorator.py` directly exercise both paths. `_patched_decorator_env` patches `django.conf.settings.DEBUG` — valid target for how the decorator reads it. Call sites (`leases/builder_views.py`, `accounts/tests/test_tier_enforcement.py`) untouched; no regressions. POPIA/security pass: no PII logged, no raw SQL, no auth bypass. AC 1–3 satisfied; AC 4 is moot (approach already hardened, no duck-typing removed needed). Review passed.

**2026-04-23 — tester**

Test run: `pytest apps/test_hub/accounts/ -k requires_feature -v`

- test_debug_true_raises_improperly_configured: PASS
- test_debug_false_returns_http_500: PASS
- test_debug_false_does_not_silently_grant_access: PASS
- test_debug_true_does_not_silently_grant_access: PASS
- TestFBVConvention::test_feature_allowed_calls_view: PASS
- TestFBVConvention::test_feature_blocked_returns_402: PASS
- TestCBVConvention::test_feature_allowed_calls_view: PASS
- TestCBVConvention::test_feature_blocked_returns_402: PASS
- TestCBVConvention::test_cbv_unexpected_args_without_request_raises_or_500: PASS

9/9 passed. All acceptance criteria verified.
