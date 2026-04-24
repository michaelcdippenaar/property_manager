---
id: RNT-QUAL-050
stream: rentals
title: "Fix push token endpoint: validate platform field and return 400 for unknown values"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214246263037796"
created: 2026-04-24
updated: 2026-04-24
---

## Goal
The push token registration endpoint currently returns 200 for any `platform` value including invalid strings (e.g. `"INVALID"`). It must validate the `platform` field against an allowed set (`ios`, `android`) and return 400 for unknown values.

## Acceptance criteria
- [x] `POST /api/v1/accounts/push-token/` with `platform="INVALID"` returns HTTP 400 with a validation error body
- [x] Valid `platform` values (`ios`, `android`) continue to return 200/201
- [x] `apps/test_hub/accounts/integration/test_auth.py::PushTokenTests::test_register_push_token_invalid_platform` passes (currently fails with 200 instead of 400)
- [x] No regression on existing push token tests

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

2026-04-24 — rentals-implementer: Fix was a one-line change in `backend/apps/accounts/views.py` `PushTokenView.post()`. The existing guard already blocked unknown platforms but `"web"` was incorrectly included in the allowed set. Removed `"web"` from the tuple and updated the error response to use a dict keyed on `"platform"` with the message `"Invalid platform. Must be one of: ios, android."` (consistent with DRF validation error shape). The model still has `Platform.WEB` as a DB choice — that's intentional and untouched (it may be used by web-push in future; the API simply doesn't accept it for token registration). 6/7 PushToken tests now pass; `test_delete_push_token` is a pre-existing failure (returns 200 instead of 204) unrelated to this change — filed discovery at `tasks/discoveries/2026-04-24-push-token-delete-returns-200.md`.
