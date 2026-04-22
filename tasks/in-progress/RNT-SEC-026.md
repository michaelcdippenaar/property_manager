---
id: RNT-SEC-026
stream: rentals
title: "Centralise X-Forwarded-For extraction to prevent audit-log IP spoofing"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214202083740465"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Replace three independent ad-hoc XFF extractors that blindly trust the first hop with a single shared `get_client_ip(request)` utility that respects proxy trust settings, preventing audit-log IP spoofing.

## Acceptance criteria
- [ ] `backend/utils/http.py` introduces `get_client_ip(request)` respecting `SECURE_PROXY_SSL_HEADER` and a `NUM_PROXIES` / trusted-proxies setting
- [ ] `backend/apps/legal/serializers.py` `_get_ip` replaced with shared utility
- [ ] `backend/apps/esigning/audit.py` IP extraction replaced with shared utility
- [ ] `backend/apps/accounts/audit.py` IP extraction replaced with shared utility
- [ ] Unit test: spoofed `X-Forwarded-For` header does not override socket `REMOTE_ADDR` when `NUM_PROXIES=0`
- [ ] POPIA consent and e-signing audit logs record correct IPs in staging

## Files likely touched
- `backend/utils/http.py` (new)
- `backend/apps/legal/serializers.py`
- `backend/apps/esigning/audit.py`
- `backend/apps/accounts/audit.py`

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/ -k ip` (new tests for utility)

## Handoff notes
Promoted from discovery `2026-04-22-xff-trust-all-apps.md` (found during OPS-004). Affects POPIA consent audit trail, e-signing logs, and login audit logs.
