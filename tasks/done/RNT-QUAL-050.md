---
id: RNT-QUAL-050
stream: rentals
title: "Fix push token endpoint: validate platform field and return 400 for unknown values"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: testing
assigned_to: tester
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

2026-04-24 — rentals-reviewer: Review passed. Verified the test at `backend/apps/test_hub/accounts/integration/test_auth.py:218-221` literally POSTs `platform="web"` and expects 400, so removing "web" from the allowed set is the correct fix (the discovery file's wording was misleading; implementer read the actual test correctly). No existing consumer sends "web" to this endpoint: `agent-app/src/services/push.ts:61` only sends `'ios' | 'android'` and explicitly defers web push to "tenant app (handled separately)"; no push-token code found in `admin/src` or `web_app/`. Error shape change from `{"detail": "..."}` to `{"platform": [...]}` does not break the one caller (`agent-app/src/stores/auth.ts:145` does not read the error body). Model's `Platform.WEB` DB choice retained via migration `0020_add_web_push_platform` — fine for future web-push. Security: endpoint still `IsAuthenticated`, no PII/secret leakage, no SQL concerns. AC 1-4 all satisfied; 6/7 PushTokenTests pass; `test_delete_push_token` is a separate pre-existing issue properly filed as discovery `2026-04-24-push-token-delete-returns-200.md`. Tester: please confirm before closing that no prod/staging PushToken rows have `platform="web"` (a quick `PushToken.objects.filter(platform="web").count()` on staging); if any exist, a data-migration follow-up may be warranted. Also worth a forward-looking note: when web-push is built for the tenant `web_app/`, a distinct endpoint (or a re-admission of "web" with a VAPID-subscription payload shape) will be needed.
