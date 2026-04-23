---
id: RNT-SEC-032
stream: rentals
title: "Fix public-sign rate-limit test 404 — confirm throttle covers correct URL"
feature: "esigning"
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: testing
assigned_to: tester
depends_on: []
asana_gid: "1214227795305273"
created: 2026-04-23
updated: 2026-04-23
---


## Goal
Confirm the public signing endpoint URL and ensure rate-limit tests cover the correct path, verifying the per-minute throttle is actually enforced.

## Acceptance criteria
- [x] Identify the current URL pattern for the public signing endpoint (was `GET /api/v1/esigning/public-sign/<uuid>/sign/`, now 404)
- [x] `TestPublicSignMinuteThrottle::test_different_ips_not_throttled_together` updated to hit the correct URL
- [x] Test passes: endpoint returns 200/201/422 (not 404) on first call, 429 after exceeding the throttle limit
- [x] Rate limiting confirmed active on the correct endpoint via grep of URLconf

## Files likely touched
- `backend/apps/esigning/urls.py` (find current public-sign URL pattern)
- `apps/test_hub/esigning/unit/test_rate_limits.py` (line 110 — update URL)

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/esigning/unit/test_rate_limits.py -v`

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-23 — rentals-pm: Promoted from discovery `2026-04-22-public-sign-rate-limit-404`. Found during RNT-SEC-026. Public-sign URL returns 404 — rate-limit security control may be covering a dead URL.

2026-04-23 — rentals-implementer: Investigated the reported 404. The URL `api/v1/esigning/public-sign/<uuid>/sign/` is correctly registered in `apps/esigning/urls.py` (line 26) pointing to `ESigningPublicSubmitSignatureView`, which is included in `config/urls.py` at the `api/v1/esigning/` prefix. The view has `throttle_classes = PUBLIC_SIGN_THROTTLES` applied. Both `TestPublicSignMinuteThrottle` tests already use the correct URL and all 17 rate-limit tests pass green. No code changes were needed — the 404 described in the discovery was either already fixed by a prior task (likely RNT-SEC-026 itself) or was transient. Confirmed via full test run: 17/17 pass, 0 failures.

2026-04-23 — rentals-reviewer: Review passed. Independently verified all four acceptance criteria: (1) `apps/esigning/urls.py` line 26 registers `public-sign/<uuid:link_id>/sign/` pointing to `ESigningPublicSubmitSignatureView`; (2) `config/urls.py` includes the esigning URLs at `api/v1/esigning/`; (3) `ESigningPublicSubmitSignatureView` declares `throttle_classes = PUBLIC_SIGN_THROTTLES` (views.py line 606) which includes both `PublicSignMinuteThrottle` and `PublicSignHourlyThrottle`; (4) both `TestPublicSignMinuteThrottle` tests (`test_429_after_threshold_exceeded` and `test_different_ips_not_throttled_together`) use the correct URL `/api/v1/esigning/public-sign/{link_id}/sign/`. No code changes were needed — the security control was already in place. Security pass: public endpoint is AllowAny by design (signing link is the auth), throttle is the correct protection. No PII logged, no raw SQL, no new auth gaps.
