---
id: RNT-SEC-004
stream: rentals
title: "Remove ESigningTestPdfView and all test-only endpoints from production"
feature: native_esigning
lifecycle_stage: null
priority: P0
effort: S
v1_phase: "1.0"
status: backlog
asana_gid: "1214177462750411"
assigned_to: null
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Identify and gate every test/debug endpoint so they return 404 in production. Leaking PDF-generation internals or test hooks to the internet is a recon vector.

## Acceptance criteria
- [ ] Audit `backend/apps/*/urls.py` for any `test_*` views, `*_test` endpoints, `debug_*` handlers
- [ ] Gate each one behind `settings.DEBUG` OR a `ENABLE_TEST_ENDPOINTS` flag that defaults False
- [ ] Known offenders to remove/gate: `ESigningTestPdfView`, `esigning_form_submit_test`, `esigning_native_signing_test`, `esigning_pdf_layout_compare`, `esigning_test_pdf`
- [ ] Staging env may have them on via flag; production does not
- [ ] Deployment checklist updated: verify `ENABLE_TEST_ENDPOINTS=false` in prod env

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
