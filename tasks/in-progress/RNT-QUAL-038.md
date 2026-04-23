---
id: RNT-QUAL-038
stream: rentals
title: "Fix broken municipal-bill-view integration tests (7 failing)"
feature: "municipal_bill_parsing"
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214229778497908"
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Realign `test_municipal_bill_view.py` with the current view behaviour so all 10 tests pass and regressions are caught.

## Acceptance criteria
- [ ] `test_unsupported_mime_returns_400` passes (view returns 400, not 502, for unsupported MIME)
- [ ] `test_claude_api_error_returns_502` passes (error message matches current "Claude API failed after 3 attempts: …" pattern)
- [ ] `test_claude_invalid_json_returns_502_with_raw_preview` passes (assertion matches current "no tool_use block" messaging)
- [ ] `test_happy_path_image_returns_extracted_json` and `test_happy_path_pdf_uses_document_block` pass with 200
- [ ] All 10 tests in `test_municipal_bill_view.py` green

## Files likely touched
- `apps/test_hub/properties/integration/test_municipal_bill_view.py` (update assertions to match view)
- `apps/properties/views.py` or equivalent municipal bill view (may need 400 vs 502 logic fix for unsupported MIME)

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/properties/integration/test_municipal_bill_view.py -v`

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-23 — rentals-pm: Promoted from discovery `2026-04-22-municipal-bill-view-tests-broken`. Found during RNT-SEC-026. 7 of 10 tests failing due to view behaviour drift (error messages, status codes).
