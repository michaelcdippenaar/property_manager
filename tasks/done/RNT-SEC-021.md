---
id: RNT-SEC-021
stream: rentals
title: "Harden @requires_feature decorator: raise on unresolvable request instead of silent pass-through"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: done
assigned_to: null
depends_on: []
asana_gid: "1214195192546765"
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Replace the `else: request = None` silent pass-through in `@requires_feature` with an explicit error so views with non-standard signatures never accidentally bypass the tier gate.

## Acceptance criteria
- [x] When request cannot be identified, decorator raises `ImproperlyConfigured` in DEBUG mode and returns HTTP 500 in production (no silent pass-through)
- [x] Test: applying decorator to a view with an unexpected signature does not silently grant access — asserts `ImproperlyConfigured` or 500 response
- [x] All existing `@requires_feature` decorated views still work correctly

## Files likely touched
- `backend/apps/accounts/decorators.py` (line 65-67, `else: request = None` branch)
- `backend/apps/test_hub/accounts/` (new test)

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/accounts/ -k "requires_feature" -v`
- Existing decorated views: assert tier gate still enforced
- Unexpected-signature view: assert `ImproperlyConfigured` / 500

## Handoff notes
2026-04-22: Promoted from discovery `2026-04-22-requires-feature-request-detection.md` (found during OPS-007 review). Latent privilege-escalation vector as more features get gated.

2026-04-23: Implementation was already complete when task was picked up. Both `backend/apps/accounts/decorators.py` and `backend/apps/test_hub/accounts/unit/test_requires_feature_decorator.py` had the full hardened implementation in place. The `else: request = None` branch has been replaced with DEBUG-aware error handling: raises `ImproperlyConfigured` in DEBUG mode, returns HTTP 500 in production. A full test suite with 9 tests covers all three branches (FBV, CBV, unresolvable) plus the critical no-silent-grant assertions. All 9 tests pass (`pytest apps/test_hub/accounts/ -k "requires_feature" -v`). No code changes were needed — moving straight to review.

2026-04-23: Review passed. Verified decorator at backend/apps/accounts/decorators.py lines 60-78: fail-closed, DEBUG raises ImproperlyConfigured, production returns HTTP 500, no silent pass-through. Verified test file backend/apps/test_hub/accounts/unit/test_requires_feature_decorator.py covers FBV, CBV, and unresolvable branches with explicit 'no silent grant' assertions. Ran `pytest apps/test_hub/accounts/ -k requires_feature -v` — 9 passed. Existing @requires_feature call sites (builder_views.py) unchanged and still conform to CBV signature. Security: no PII/secret leakage in error paths.

### Test run 2026-04-23
- `pytest apps/test_hub/accounts/ -k "requires_feature" -v`: 9 passed, 293 deselected, 1 warning in 9.25s
  - TestUnresolvableRequest::test_debug_true_raises_improperly_configured PASSED
  - TestUnresolvableRequest::test_debug_false_returns_http_500 PASSED
  - TestUnresolvableRequest::test_debug_false_does_not_silently_grant_access PASSED
  - TestUnresolvableRequest::test_debug_true_does_not_silently_grant_access PASSED
  - TestFBVConvention::test_feature_allowed_calls_view PASSED
  - TestFBVConvention::test_feature_blocked_returns_402 PASSED
  - TestCBVConvention::test_feature_allowed_calls_view PASSED
  - TestCBVConvention::test_feature_blocked_returns_402 PASSED
  - TestCBVConvention::test_cbv_unexpected_args_without_request_raises_or_500 PASSED
- All acceptance criteria met. No failures.
