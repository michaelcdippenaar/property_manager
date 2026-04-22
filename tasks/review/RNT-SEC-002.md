---
id: RNT-SEC-002
stream: rentals
title: "Rate-limit public e-signing and invite endpoints"
feature: native_esigning
lifecycle_stage: 7
priority: P0
effort: S
v1_phase: "1.0"
status: review
asana_gid: "1214177462221163"
assigned_to: reviewer
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Apply per-IP and per-token rate limits to all public (unauthenticated) e-signing, public document, and tenant-invite endpoints so they cannot be brute-forced or DoS'd.

## Acceptance criteria
- [x] Install + configure `django-ratelimit` (or DRF throttling) globally
- [x] Public signing endpoints: `/api/v1/esigning/public/<token>/...` → 10 req/min/IP, 60 req/hr/IP
- [x] Mandate/lease public link endpoints → same tier
- [x] Tenant-invite acceptance endpoint → 5 req/min/IP
- [x] Login endpoint → 5 failed attempts/min/IP + 20/hr/user
- [x] OTP verification endpoints (Vault gateway, 2FA) → 5/min/token
- [x] Rate-limit breaches return 429 + logged
- [x] Document the limits in `docs/ops/rate-limits.md`

## Files likely touched
- `backend/config/settings.py` (install + defaults)
- `backend/apps/esigning/views.py` (public endpoints)
- `backend/apps/leases/views.py` (public link views)
- `backend/apps/users/views.py` (login, invite)
- `docs/ops/rate-limits.md` (new)

## Test plan
**Automated:**
- `pytest backend/apps/esigning/tests/test_rate_limits.py` — hitting public sign endpoint 11× in a minute returns 429 on the 11th

**Manual:**
- curl in a loop → confirm 429 at threshold

## Handoff notes

### 2026-04-22 — implementer

Used DRF's built-in throttle system rather than `django-ratelimit` (no new
dependency needed; DRF throttles already in the project).

**New files:**
- `backend/apps/esigning/throttles.py` — `PublicSignMinuteThrottle` (10/min) and `PublicSignHourlyThrottle` (60/hr)
- `backend/apps/test_hub/esigning/unit/test_rate_limits.py` — 15 unit tests; all pass
- `docs/ops/rate-limits.md` — full documentation of all rate-limit tiers

**Modified files:**
- `backend/config/settings/base.py` — added `DEFAULT_THROTTLE_CLASSES` (global) and 4 new scopes to `DEFAULT_THROTTLE_RATES`
- `backend/apps/esigning/views.py` — `throttle_classes = PUBLIC_SIGN_THROTTLES` on all 6 `AllowAny` public-signing views
- `backend/apps/accounts/throttles.py` — added `InviteAcceptThrottle` (5/min) and `LoginHourlyThrottle` (20/hr per email)
- `backend/apps/accounts/views.py` — `LoginView` now uses `[AuthAnonThrottle, LoginHourlyThrottle]`; `AcceptInviteView` now uses `[InviteAcceptThrottle]`

**OTP endpoints:** Already had `OTPSendThrottle` (3/min) and `OTPVerifyThrottle` (5/min) applied since before this task. No Vault gateway OTP endpoint was found in the codebase (`the_volt` app has no `AllowAny` views), so the existing `otp_verify` scope covers the current surface area.

**429 logging:** DRF logs throttle breaches at WARNING via `rest_framework.throttling` logger; the global `console` handler catches these.

**Discovery:** Pre-existing conflicting migrations in `properties` app block DB tests. Logged at `tasks/discoveries/2026-04-22-properties-migration-conflict.md`. The 2 DB-integration rate-limit tests (`test_429_after_threshold_exceeded`, `test_different_ips_not_throttled_together`) cannot run until that migration conflict is resolved.

**Caveat for production:** DRF throttles use locmem cache by default. Redis must be configured as the `default` cache backend for limits to hold across multiple Gunicorn workers. See `docs/ops/rate-limits.md` for the config snippet.
