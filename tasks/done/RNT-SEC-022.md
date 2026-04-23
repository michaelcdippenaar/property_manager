---
id: RNT-SEC-022
stream: rentals
title: "Centralise X-Forwarded-For IP extraction to prevent spoofed audit log IPs"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: done
assigned_to: null
depends_on: []
asana_gid: "1214195241914599"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Replace three ad-hoc XFF IP extraction implementations with a single shared `get_client_ip(request)` utility that respects proxy trust settings, so consent, e-signing, and login audit logs cannot be spoofed via crafted `X-Forwarded-For` headers.

## Acceptance criteria
- [x] `backend/utils/http.py` introduces `get_client_ip(request)` that respects `NUM_PROXIES` (or a trusted-proxies list from settings) and does not blindly trust the first XFF hop
- [x] `apps/legal/serializers.py` `_get_ip`, `apps/esigning/audit.py`, and `apps/accounts/audit.py` all replaced with calls to `get_client_ip(request)`
- [x] Unit test: spoofed `X-Forwarded-For` header does not override socket `REMOTE_ADDR` when `NUM_PROXIES=0`
- [x] Unit test: correct IP extracted when `NUM_PROXIES=1` (single trusted proxy)

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

## Reconciliation note (2026-04-23)
Closed during backlog reconciliation pass. All ACs confirmed satisfied in HEAD:
- `backend/utils/http.py` contains `get_client_ip()` with `NUM_PROXIES` setting support (lines 45+).
- `backend/apps/legal/serializers.py`, `backend/apps/esigning/audit.py`, and `backend/apps/accounts/audit.py` all import and call `get_client_ip` (confirmed via grep).
- `backend/utils/tests/test_http.py` contains explicit tests for `NUM_PROXIES=0` spoofed XFF ignored, `NUM_PROXIES=1` correct hop extracted, and other edge cases (9+ test functions).
