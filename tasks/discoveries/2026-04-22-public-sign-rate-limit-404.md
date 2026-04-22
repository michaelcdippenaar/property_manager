---
discovered_by: rentals-tester
discovered_during: RNT-SEC-026
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT-SEC
---

## What I found
`TestPublicSignMinuteThrottle::test_different_ips_not_throttled_together` in `apps/test_hub/esigning/unit/test_rate_limits.py` is failing because `GET /api/v1/esigning/public-sign/<uuid>/sign/` returns 404 instead of being throttled (expected 429). The public signing URL appears to no longer exist at that path.

## Why it matters
Rate limiting on the public signing endpoint is a security control. If the URL changed, the rate limit tests are not covering the correct endpoint and the control may be untested or misconfigured.

## Where I saw it
- `apps/test_hub/esigning/unit/test_rate_limits.py:110`
- `GET /api/v1/esigning/public-sign/<uuid>/sign/` returning 404

## Suggested acceptance criteria (rough)
- [ ] Rate limit test updated to match current public signing URL pattern
- [ ] Rate limiting on the public signing endpoint confirmed to work

## Why I didn't fix it in the current task
Out of scope. This task covers IP extraction utility only.
