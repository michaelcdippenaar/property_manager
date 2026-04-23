---
id: RNT-SEC-018
stream: rentals
title: "Centralise X-Forwarded-For IP extraction to prevent spoofed IPs in audit logs"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214230994874349"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Replace three independent ad-hoc XFF IP extraction implementations with a single trusted-proxy-aware utility so audit logs (POPIA consent, e-signing, login) cannot be poisoned by spoofed `X-Forwarded-For` headers.

## Acceptance criteria
- [ ] `backend/utils/http.py` (or `backend/utils/network.py`) contains a shared `get_client_ip(request)` utility that respects `SECURE_PROXY_SSL_HEADER` and a configurable `NUM_PROXIES` / trusted-proxies list from settings
- [ ] `backend/apps/legal/serializers.py` `_get_ip` static method replaced with the shared utility
- [ ] `backend/apps/esigning/audit.py` XFF extraction replaced with the shared utility
- [ ] `backend/apps/accounts/audit.py` XFF extraction replaced with the shared utility
- [ ] Unit test: when `NUM_PROXIES=0`, a crafted `X-Forwarded-For` header does not override the socket `REMOTE_ADDR`
- [ ] Unit test: when `NUM_PROXIES=1`, the correct hop is extracted from a multi-hop XFF header
- [ ] No regressions in POPIA consent audit, e-signing audit, or login audit logging

## Files likely touched
- `backend/utils/http.py` (new utility)
- `backend/apps/legal/serializers.py`
- `backend/apps/esigning/audit.py`
- `backend/apps/accounts/audit.py`
- `backend/apps/test_hub/utils/test_http.py` (new tests)
- `backend/config/settings/base.py` (add `NUM_PROXIES` setting)

## Test plan
**Manual:**
- Send a request with `X-Forwarded-For: 1.2.3.4` to a POPIA consent endpoint; check audit log — should record real socket IP, not `1.2.3.4` when `NUM_PROXIES=0`

**Automated:**
- `cd backend && pytest apps/test_hub/utils/ -v`

## Handoff notes
Promoted from discovery: `2026-04-22-xff-trust-all-apps.md` (OPS-004). Spoofable IPs weaken POPIA s11 forensic audit trails and may allow rate-limit bypass.
