---
id: RNT-SEC-047
stream: rentals
title: "Fix naive X-Forwarded-For parsing in contact.py (rate-limit bypass)"
feature: ""
lifecycle_stage: null
priority: P1
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: null
created: 2026-04-24
updated: 2026-04-24
---

## Goal
Replace the spoofable `_client_ip()` helper in `config/contact.py` with the hardened `utils.http.get_client_ip(request)` utility, closing the rate-limit bypass on the public marketing contact endpoint.

## Acceptance criteria
- [ ] `config/contact.py::_client_ip()` private helper is deleted; all call sites replaced with `utils.http.get_client_ip(request)`
- [ ] Rate limit of 5/hour on `contact_view` cannot be bypassed by forging `X-Forwarded-For` when `NUM_PROXIES=0`
- [ ] Regression test: a forged XFF header does not change the keyed IP used for rate limiting
- [ ] `grep -rn "HTTP_X_FORWARDED_FOR" backend/` returns zero production hits outside `utils/http.py`
- [ ] Note: `apps/the_volt/gateway/views.py:142` also uses raw XFF — fix is out of Rentals v1 scope (Vault33) but noted here for awareness

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
