---
id: RNT-SEC-047
stream: rentals
title: "Fix naive X-Forwarded-For parsing in contact.py (rate-limit bypass)"
feature: ""
lifecycle_stage: null
priority: P1
effort: S
v1_phase: "1.0"
status: done
assigned_to: null
depends_on: []
asana_gid: "1214275420009980"
created: 2026-04-24
updated: 2026-04-24
---

## Goal
Replace the spoofable `_client_ip()` helper in `config/contact.py` with the hardened `utils.http.get_client_ip(request)` utility, closing the rate-limit bypass on the public marketing contact endpoint.

## Acceptance criteria
- [x] `config/contact.py::_client_ip()` private helper is deleted; all call sites replaced with `utils.http.get_client_ip(request)`
- [x] Rate limit of 5/hour on `contact_view` cannot be bypassed by forging `X-Forwarded-For` when `NUM_PROXIES=0`
- [x] Regression test: a forged XFF header does not change the keyed IP used for rate limiting
- [x] `grep -rn "HTTP_X_FORWARDED_FOR" backend/` returns zero production hits outside `utils/http.py`
- [x] Note: `apps/the_volt/gateway/views.py:142` also uses raw XFF — fix is out of Rentals v1 scope (Vault33) but noted here for awareness

## Files likely touched
- `backend/config/contact.py` (lines 46–51)
- `backend/utils/http.py` (no change expected; already hardened)
- `backend/config/tests/test_contact.py` (new or existing test)

## Test plan
**Manual:**
- POST to `/contact/` with `X-Forwarded-For: 1.2.3.4` spoofed; confirm rate limit keys on actual proxy IP, not the forged value

**Automated:**
- `cd backend && pytest config/tests/test_contact.py -v`

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-24 — Promoted from discovery `2026-04-23-naive-xff-parsing-in-contact-and-volt.md`. The_volt gateway XFF issue is out of Rentals v1 scope per PM; scoping this ticket to contact.py only.

2026-04-24 — implementer: Deleted `_client_ip()` from `config/contact.py`; replaced all 2 call sites (honeypot log + rate-limit keying) with `utils.http.get_client_ip(request)`. Added `config/tests/test_contact.py` with 4 tests (XFF bypass blocked, keyed-IP is REMOTE_ADDR, origin reject, happy-path smoke). All 4 pass. The `apps/the_volt/gateway/views.py:142` raw XFF hit remains; it is Vault33 scope and is not touched.

2026-04-24 — reviewer: Approved. Verified _client_ip() deleted, both call sites use utils.http.get_client_ip, grep confirms no raw XFF in Rentals production code (the_volt out of scope, utils/http.py + tests expected). 4 tests cover bypass vector: 6th request with forged XFF returns 429, stored ip_address equals REMOTE_ADDR not forged value, origin reject, happy-path. → testing.

2026-04-24 — tester: All 4 automated tests pass (test_forged_xff_does_not_bypass_rate_limit, test_keyed_ip_is_remote_addr_not_xff, test_unknown_origin_rejected, test_happy_path_creates_enquiry). No failures. → done.
