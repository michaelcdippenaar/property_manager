---
id: RNT-SEC-033
stream: rentals
title: "Replace residual ad-hoc XFF extractors with get_client_ip() utility"
feature: "security"
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214223123663001"
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Eliminate the three remaining raw `X-Forwarded-For` reads in `accounts` and `esigning` apps by replacing them with the `get_client_ip(request)` utility introduced in RNT-SEC-026, so XFF spoofing cannot poison login lockouts, consent records, or e-signing audit logs.

## Acceptance criteria
- [ ] `accounts/views.py` `LoginView._get_client_ip` private method removed; replaced with `get_client_ip(request)` from `utils.http`
- [ ] `accounts/serializers.py` `RegistrationSerializer._record_consent` inline XFF extractor replaced with `get_client_ip(request)`
- [ ] `esigning/views.py` inline XFF block (~line 628) replaced with `get_client_ip(request)`
- [ ] `grep -r "HTTP_X_FORWARDED_FOR" backend/apps/` returns no matches outside `utils/http.py`
- [ ] Existing login, registration, and e-signing tests still pass

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
