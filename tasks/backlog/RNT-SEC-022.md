---
id: RNT-SEC-022
stream: rentals
title: "Centralise X-Forwarded-For IP extraction to prevent spoofed audit log IPs"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214195241914599"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Replace three ad-hoc XFF IP extraction implementations with a single shared `get_client_ip(request)` utility that respects proxy trust settings, so consent, e-signing, and login audit logs cannot be spoofed via crafted `X-Forwarded-For` headers.

## Acceptance criteria
- [ ] `backend/utils/http.py` introduces `get_client_ip(request)` that respects `NUM_PROXIES` (or a trusted-proxies list from settings) and does not blindly trust the first XFF hop
- [ ] `apps/legal/serializers.py` `_get_ip`, `apps/esigning/audit.py`, and `apps/accounts/audit.py` all replaced with calls to `get_client_ip(request)`
- [ ] Unit test: spoofed `X-Forwarded-For` header does not override socket `REMOTE_ADDR` when `NUM_PROXIES=0`
- [ ] Unit test: correct IP extracted when `NUM_PROXIES=1` (single trusted proxy)

## Files likely touched
- `backend/utils/http.py` (new utility)
- `backend/apps/legal/serializers.py` (~line 62)
- `backend/apps/esigning/audit.py` (~line 10)
- `backend/apps/accounts/audit.py` (~line 10)
- `backend/apps/test_hub/` (new tests)

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/ -k "get_client_ip" -v`
- Spoofed XFF with NUM_PROXIES=0: assert REMOTE_ADDR used, not XFF
- Single proxy with NUM_PROXIES=1: assert correct client IP extracted

## Handoff notes
2026-04-22: Promoted from discovery `2026-04-22-xff-trust-all-apps.md` (found during OPS-004 review). POPIA consent audit trails may record attacker-supplied IPs — forensic integrity concern.
