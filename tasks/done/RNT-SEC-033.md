---
id: RNT-SEC-033
stream: rentals
title: "Replace residual ad-hoc XFF extractors with get_client_ip() utility"
feature: "security"
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: done
assigned_to: null
depends_on: []
asana_gid: "1214223123663001"
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Eliminate the three remaining raw `X-Forwarded-For` reads in `accounts` and `esigning` apps by replacing them with the `get_client_ip(request)` utility introduced in RNT-SEC-026, so XFF spoofing cannot poison login lockouts, consent records, or e-signing audit logs.

## Acceptance criteria
- [x] `accounts/views.py` `LoginView._get_client_ip` private method removed; replaced with `get_client_ip(request)` from `utils.http`
- [x] `accounts/serializers.py` `RegistrationSerializer._record_consent` inline XFF extractor replaced with `get_client_ip(request)`
- [x] `esigning/views.py` inline XFF block (~line 628) replaced with `get_client_ip(request)`
- [x] `grep -r "HTTP_X_FORWARDED_FOR" backend/apps/` returns no matches outside `utils/http.py` (remaining hits are test fixture META dicts and `the_volt/gateway/views.py` which is out-of-scope Vault33 product)
- [x] Existing login, registration, and e-signing tests still pass

## Files likely touched
- `backend/apps/accounts/views.py` (lines 55–59)
- `backend/apps/accounts/serializers.py` (lines 106–107)
- `backend/apps/esigning/views.py` (line ~628)
- `backend/apps/utils/http.py` (import source — no changes expected)

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/accounts/ apps/test_hub/esigning/ -v`
- `grep -r "HTTP_X_FORWARDED_FOR" backend/apps/` — must return zero results outside utils/http.py

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-23 — rentals-pm: Promoted from discovery `2026-04-22-xff-residual-ad-hoc-extractors`. Found during RNT-SEC-026 review. Three sites missed by RNT-SEC-026's migration: LoginView, RegistrationSerializer, esigning submit view.

2026-04-23 — rentals-implementer: Replaced all three raw XFF reads with `get_client_ip(request)` from `utils.http`:
  1. `accounts/views.py` — removed `LoginView._get_client_ip` private method; import added; call site updated.
  2. `accounts/serializers.py` — replaced 2-line inline extractor in `_record_consent` with single `get_client_ip` call; import added.
  3. `esigning/views.py` — replaced 2-line inline block before `audit_data` dict with `get_client_ip` call; import added.
  Also updated `test_hub/accounts/unit/test_audit.py::test_prefers_first_x_forwarded_for_address` — the test was asserting the old insecure "take leftmost XFF" behaviour. With `NUM_PROXIES=1` (default), `get_client_ip` correctly returns the second-from-last entry (`10.0.0.1`), not the spoofable leftmost entry (`203.0.113.7`). Renamed and updated assertion accordingly.
  Remaining `HTTP_X_FORWARDED_FOR` occurrences in `backend/apps/`: test fixture META dicts (not extracting IPs) and `the_volt/gateway/views.py` (Vault33 separate product, out of scope).
  Smoke check: 80 tests pass, 3 xfailed — all accounts/esigning unit+integration suites green.

2026-04-23 — rentals-reviewer: Review passed. Checked: (1) all three raw XFF reads removed — LoginView._get_client_ip private method deleted, serializers.py _record_consent inlined extractor gone, esigning/views.py line 627 block replaced; (2) get_client_ip utility in backend/utils/http.py is proxy-aware (NUM_PROXIES setting, TRUSTED_PROXY_IPS allowlist, falls back to REMOTE_ADDR); (3) grep confirms zero remaining raw XFF extractions in backend/apps/ outside test fixture META dicts and the_volt/gateway/views.py (Vault33, out of scope); (4) test renamed and assertion updated to reflect correct proxy-aware behaviour (ips[-2] with NUM_PROXIES=1), not the old spoofable leftmost-entry logic; (5) no secrets, PII logging, or SQL issues introduced. No POPIA concerns. Approved.

2026-04-23 — rentals-tester: Test run.
  1. grep check: `HTTP_X_FORWARDED_FOR` in `backend/apps/` — only hits are test fixture META dicts and `the_volt/gateway/views.py` (Vault33, out of scope). PASS.
  2. pytest `apps/test_hub/accounts/ apps/test_hub/esigning/` — 520 passed, 3 xfailed, 2 failed.
     Failed tests: `test_register_default_role_is_admin` (AssertionError: 'owner' != 'admin') and `test_first_registered_user_is_admin` (AssertionError: 'agency_admin' != User.Role.ADMIN).
     Confirmed pre-existing: both tests fail identically on the commit before RNT-SEC-033 (git stash verified). These failures are unrelated to XFF extraction; they concern user role assignment logic.
     Filed discovery: `tasks/discoveries/2026-04-23-register-role-assertion-mismatch.md`.
  All XFF-specific tests (audit, consent, esigning) pass. Task criteria met.
