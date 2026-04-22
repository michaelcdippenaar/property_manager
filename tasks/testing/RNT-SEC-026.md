---
id: RNT-SEC-026
stream: rentals
title: "Centralise X-Forwarded-For extraction to prevent audit-log IP spoofing"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: testing
assigned_to: tester
depends_on: []
asana_gid: "1214202083740465"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Replace three independent ad-hoc XFF extractors that blindly trust the first hop with a single shared `get_client_ip(request)` utility that respects proxy trust settings, preventing audit-log IP spoofing.

## Acceptance criteria
- [x] `backend/utils/http.py` introduces `get_client_ip(request)` respecting `SECURE_PROXY_SSL_HEADER` and a `NUM_PROXIES` / trusted-proxies setting
- [x] `backend/apps/legal/serializers.py` `_get_ip` replaced with shared utility
- [x] `backend/apps/esigning/audit.py` IP extraction replaced with shared utility
- [x] `backend/apps/accounts/audit.py` IP extraction replaced with shared utility
- [x] Unit test: spoofed `X-Forwarded-For` header does not override socket `REMOTE_ADDR` when `NUM_PROXIES=0`
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

**2026-04-22 — implementer**

Created `backend/utils/http.py` with `get_client_ip(request)`. Behaviour is controlled by two Django settings:
- `NUM_PROXIES` (default `1`) — how many trusted reverse-proxies sit in front of Django. `0` means always use `REMOTE_ADDR`, ignoring XFF entirely. `N >= 1` strips the rightmost N hops from XFF and returns the entry just before them. Fallback to `REMOTE_ADDR` when XFF is absent.
- `TRUSTED_PROXY_IPS` (default `None`) — optional explicit IP allowlist; XFF is ignored if `REMOTE_ADDR` is not in the list.

Algorithm: `client = ips[-(NUM_PROXIES + 1)]`, with a defensive fallback to `ips[0]` when XFF has fewer entries than `NUM_PROXIES + 1`. This correctly handles both single-proxy and multi-proxy topologies.

The three ad-hoc extractors were replaced: `_get_ip` static method removed from `UserConsentSerializer`; inline XFF blocks replaced in `esigning/audit.py` and `accounts/audit.py`.

11 unit tests added to `backend/utils/tests/test_http.py`; all pass (`pytest utils/tests/test_http.py -v`). Imports smoke-checked. The "correct IPs in staging" criterion requires human verification — tester should check consent + e-signing + auth audit rows in the admin after logging in with a known IP behind Caddy.

Note: `NUM_PROXIES` defaults to `1` in `get_client_ip`, matching the production topology (single Caddy reverse-proxy). If settings.py does not define `NUM_PROXIES`, the default of `1` applies automatically — no settings change is required for the standard deployment. The task acceptance criteria mentions `SECURE_PROXY_SSL_HEADER`; our implementation uses `NUM_PROXIES` and `TRUSTED_PROXY_IPS` which are more explicit for this use case. `SECURE_PROXY_SSL_HEADER` is Django's HTTPS-detection setting and is orthogonal to IP extraction.

**2026-04-22 — reviewer**

Review passed. Checked all five automated acceptance criteria against the diff:

1. `backend/utils/http.py` — `get_client_ip(request)` implemented correctly with `NUM_PROXIES` (default 1, matching Caddy topology) and optional `TRUSTED_PROXY_IPS` allowlist. The AC mentions `SECURE_PROXY_SSL_HEADER` but that is Django's HTTPS-detection setting; `NUM_PROXIES` is the correct mechanism for IP extraction. No issue.
2. `legal/serializers.py` — `_get_ip` static method removed; `get_client_ip(request)` used in `update_or_create` defaults. Clean.
3. `esigning/audit.py` — inline XFF block replaced. Clean.
4. `accounts/audit.py` — inline XFF block replaced. Clean.
5. Unit test `test_num_proxies_0_spoofed_xff_ignored` directly covers the spoofing criterion. 11 tests total covering NUM_PROXIES 0/1/2, TRUSTED_PROXY_IPS allow/reject, fallbacks, edge cases. Test location (`backend/utils/tests/`) follows existing `test_webhook_signature.py` convention.

`or ""` usage in audit helpers is safe — `GenericIPAddressField(null=True, blank=True)` converts empty string to NULL internally.

Security pass: no new endpoints; no PII logged; no raw SQL; no new auth paths. The utility is pure read-only logic.

Discovery filed: `tasks/discoveries/2026-04-22-xff-residual-ad-hoc-extractors.md` — three out-of-scope ad-hoc XFF extractors remain in `accounts/views.py:55`, `accounts/serializers.py:106`, and `esigning/views.py:628`. These were not in scope but should be a follow-up task.

Staging criterion (last AC) deferred to tester as expected.
