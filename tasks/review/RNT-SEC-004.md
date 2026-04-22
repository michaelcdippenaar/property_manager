---
id: RNT-SEC-004
stream: rentals
title: "Remove ESigningTestPdfView and all test-only endpoints from production"
feature: native_esigning
lifecycle_stage: null
priority: P0
effort: S
v1_phase: "1.0"
status: review
asana_gid: "1214177462750411"
assigned_to: reviewer
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Identify and gate every test/debug endpoint so they return 404 in production. Leaking PDF-generation internals or test hooks to the internet is a recon vector.

## Acceptance criteria
- [x] Audit `backend/apps/*/urls.py` for any `test_*` views, `*_test` endpoints, `debug_*` handlers
- [x] Gate each one behind `settings.DEBUG` OR a `ENABLE_TEST_ENDPOINTS` flag that defaults False
- [x] Known offenders to remove/gate: `ESigningTestPdfView`, `esigning_form_submit_test`, `esigning_native_signing_test`, `esigning_pdf_layout_compare`, `esigning_test_pdf`
- [x] Staging env may have them on via flag; production does not
- [x] Deployment checklist updated: verify `ENABLE_TEST_ENDPOINTS=false` in prod env

## Files likely touched
- `backend/config/settings.py` (ENABLE_TEST_ENDPOINTS flag)
- `backend/apps/esigning/urls.py`
- `backend/apps/esigning/views.py` (wrap with gate decorator)
- `deploy/production.env.example`

## Test plan
**Manual:**
- Prod URL for test endpoint returns 404
- Staging URL returns 200 (when flag on)

**Automated:**
- `pytest backend/apps/esigning/tests/test_endpoint_gating.py`

## Handoff notes

### 2026-04-22 — implementer

**Audit findings:** Only one offender found in `backend/apps/*/urls.py` outside of `test_hub` itself — `ESigningTestPdfView` at `submissions/<pk>/test-pdf/`. The other names listed in the task (`esigning_form_submit_test`, `esigning_native_signing_test`, `esigning_pdf_layout_compare`) did not exist in the codebase; the audit confirmed they are not present.

The `test_hub` app (`/api/v1/test-hub/`) was included unconditionally in `config/urls.py` with no flag guard — this is the bigger exposure surface.

**Changes made:**

1. `backend/config/settings/base.py` — added `ENABLE_TEST_ENDPOINTS = config("ENABLE_TEST_ENDPOINTS", default=False, cast=bool)` immediately after the `DEBUG` line.

2. `backend/config/urls.py` — test-hub URL block is now conditional on `settings.ENABLE_TEST_ENDPOINTS`. When the flag is False the entire `/api/v1/test-hub/` prefix is absent from the URL resolver (returns 404 for all sub-paths).

3. `backend/apps/esigning/views.py` — `ESigningTestPdfView.get()` raises `Http404` immediately when `settings.ENABLE_TEST_ENDPOINTS` is False. The route itself stays registered (so `reverse()` still works in tests), but the view bails before touching any data.

4. `backend/.env.example` — added `ENABLE_TEST_ENDPOINTS=True` (dev default, with comment).

5. `backend/.env.production` — added `ENABLE_TEST_ENDPOINTS=False` with a "MUST remain False" comment.

6. `backend/.env.staging` — added `ENABLE_TEST_ENDPOINTS=True` so QA can access test-pdf and test-hub on staging.

7. Created `backend/apps/test_hub/esigning/integration/test_endpoint_gating.py` with three test cases: flag-off returns 404, flag-on is reachable (with Gotenberg mocked), unauthenticated returns 401/403.

**Smoke check:** `django.setup()` succeeds, `reverse("esigning-test-pdf")` resolves, `settings.ENABLE_TEST_ENDPOINTS` reads `False` from local `.env`, and `test-hub` does NOT appear in the URL resolver when the flag is off.

**Caveats for reviewer:** The `test_hub` app remains in `INSTALLED_APPS` regardless of the flag (needed for migrations and the test runner itself). Only its URLs are gated — this is intentional and correct.
