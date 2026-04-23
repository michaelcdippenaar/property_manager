---
id: RNT-SEC-032
stream: rentals
title: "Fix public-sign rate-limit test 404 — confirm throttle covers correct URL"
feature: "esigning"
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214227795305273"
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Confirm the public signing endpoint URL and ensure rate-limit tests cover the correct path, verifying the per-minute throttle is actually enforced.

## Acceptance criteria
- [ ] Identify the current URL pattern for the public signing endpoint (was `GET /api/v1/esigning/public-sign/<uuid>/sign/`, now 404)
- [ ] `TestPublicSignMinuteThrottle::test_different_ips_not_throttled_together` updated to hit the correct URL
- [ ] Test passes: endpoint returns 200/201/422 (not 404) on first call, 429 after exceeding the throttle limit
- [ ] Rate limiting confirmed active on the correct endpoint via grep of URLconf

## Files likely touched
- `backend/apps/esigning/urls.py` (find current public-sign URL pattern)
- `apps/test_hub/esigning/unit/test_rate_limits.py` (line 110 — update URL)

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/esigning/unit/test_rate_limits.py -v`

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-23 — rentals-pm: Promoted from discovery `2026-04-22-public-sign-rate-limit-404`. Found during RNT-SEC-026. Public-sign URL returns 404 — rate-limit security control may be covering a dead URL.
