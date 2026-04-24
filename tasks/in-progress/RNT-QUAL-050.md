---
id: RNT-QUAL-050
stream: rentals
title: "Fix push token endpoint: validate platform field and return 400 for unknown values"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214246263037796"
created: 2026-04-24
updated: 2026-04-24
---

## Goal
The push token registration endpoint currently returns 200 for any `platform` value including invalid strings (e.g. `"INVALID"`). It must validate the `platform` field against an allowed set (`ios`, `android`) and return 400 for unknown values.

## Acceptance criteria
- [ ] `POST /api/v1/accounts/push-token/` with `platform="INVALID"` returns HTTP 400 with a validation error body
- [ ] Valid `platform` values (`ios`, `android`) continue to return 200/201
- [ ] `apps/test_hub/accounts/integration/test_auth.py::PushTokenTests::test_register_push_token_invalid_platform` passes (currently fails with 200 instead of 400)
- [ ] No regression on existing push token tests

## Files likely touched
- `backend/apps/accounts/serializers.py` (add `platform` field validator)
- `backend/apps/accounts/views.py` (or wherever push token registration is handled)
- `backend/apps/test_hub/accounts/integration/test_auth.py`

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/accounts/integration/test_auth.py::PushTokenTests -v`

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-24 — rentals-pm: Promoted from discovery `2026-04-23-test-hub-remaining-regressions-post-infra-fix.md`. One of four regression tasks split from that discovery. Previously hidden by 347 infra failures surfaced in RNT-QUAL-045.
