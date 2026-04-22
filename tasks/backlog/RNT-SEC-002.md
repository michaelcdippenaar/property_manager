---
id: RNT-SEC-002
stream: rentals
title: "Rate-limit public e-signing and invite endpoints"
feature: native_esigning
lifecycle_stage: 7
priority: P0
effort: S
v1_phase: "1.0"
status: backlog
asana_gid: "1214177462221163"
assigned_to: null
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Apply per-IP and per-token rate limits to all public (unauthenticated) e-signing, public document, and tenant-invite endpoints so they cannot be brute-forced or DoS'd.

## Acceptance criteria
- [ ] Install + configure `django-ratelimit` (or DRF throttling) globally
- [ ] Public signing endpoints: `/api/v1/esigning/public/<token>/...` → 10 req/min/IP, 60 req/hr/IP
- [ ] Mandate/lease public link endpoints → same tier
- [ ] Tenant-invite acceptance endpoint → 5 req/min/IP
- [ ] Login endpoint → 5 failed attempts/min/IP + 20/hr/user
- [ ] OTP verification endpoints (Vault gateway, 2FA) → 5/min/token
- [ ] Rate-limit breaches return 429 + logged
- [ ] Document the limits in `docs/ops/rate-limits.md`

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
