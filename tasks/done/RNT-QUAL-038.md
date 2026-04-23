---
id: RNT-QUAL-038
stream: rentals
title: "Fix broken municipal-bill-view integration tests (7 failing)"
feature: "municipal_bill_parsing"
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: done
assigned_to: null
depends_on: []
asana_gid: "1214229778497908"
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Realign `test_municipal_bill_view.py` with the current view behaviour so all 10 tests pass and regressions are caught.

## Acceptance criteria
- [x] `test_unsupported_mime_returns_400` passes (view returns 400, not 502, for unsupported MIME)
- [x] `test_claude_api_error_returns_502` passes (error message matches current "Claude API failed after 3 attempts: …" pattern)
- [x] `test_claude_invalid_json_returns_502_with_raw_preview` passes (assertion matches current "no tool_use block" messaging)
- [x] `test_happy_path_image_returns_extracted_json` and `test_happy_path_pdf_uses_document_block` pass with 200
- [x] All 10 tests in `test_municipal_bill_view.py` green (11 pass after rename + 2 new tests)

## Files likely touched
- `apps/test_hub/properties/integration/test_municipal_bill_view.py` (update assertions to match view)
- `apps/properties/views.py` or equivalent municipal bill view (may need 400 vs 502 logic fix for unsupported MIME)

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/properties/integration/test_municipal_bill_view.py -v`

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-23 — rentals-pm: Promoted from discovery `2026-04-22-municipal-bill-view-tests-broken`. Found during RNT-SEC-026. 7 of 10 tests failing due to view behaviour drift (error messages, status codes).

2026-04-23 — rentals-implementer: The view had migrated from plain-text JSON parsing to `tool_use` (via `call_claude_with_tools` in `extraction_utils.py`), but the tests were still mocking a plain-text response. Root cause of each failure:

1. `test_unsupported_mime_returns_400` (502→400): `encode_file` falls through to a text block for unsupported MIMEs rather than returning `None`, so the old `file_block is None` guard never fired. Fixed in `municipal_bill_view.py` with an explicit allowlist check (`image/*` or `application/pdf`) before calling `encode_file`.

2. `test_claude_api_error_returns_502`: Assertion checked for `"Claude API error"` but the retry wrapper in `call_claude_with_tools` returns `"Claude API failed after N attempts: API error: ..."`. Updated assertion to `assertIn("Claude API failed after", ...)`.

3. `test_claude_invalid_json_returns_502_with_raw_preview`: Concept is obsolete — the view no longer parses JSON text; it reads `block.input` from a `tool_use` block. Renamed to `test_claude_no_tool_use_block_returns_502` and updated to mock a text-only response, asserting `"no tool_use block"` in the error detail.

4. Happy path tests (image, pdf, fenced JSON x2): `_fake_claude_response` returned a mock with `content[0].text`, but `call_claude_with_tools` iterates looking for `block.type == "tool_use"` and found none → 502. Replaced `_fake_claude_response` with `_fake_tool_use_response(payload: dict)` that sets `block.type = "tool_use"` and `block.input = payload`. The two fenced-JSON tests were obsolete (view never parses text) — replaced with `test_extracted_payload_includes_confidence_scores` and `test_tool_choice_is_forced_in_api_call`.

All 11 tests now pass. No regressions — the 4 already-passing auth/config tests unchanged.

2026-04-23 — rentals-reviewer: Review passed. Checked all 5 acceptance criteria:
1. Allowlist guard in `municipal_bill_view.py` lines 136-140 correctly returns 400 for non-image/non-PDF before `encode_file` is called — fixes the 502→400 regression.
2. Assertion update to `assertIn("Claude API failed after", ...)` matches `call_claude_with_tools` retry wrapper pattern confirmed in `extraction_utils.py` line 401.
3. `test_claude_no_tool_use_block_returns_502` correctly mocks a text-only response via `_fake_no_tool_use_response()` and asserts `"no tool_use block"` in detail.
4. Happy path image + PDF tests updated to use `_fake_tool_use_response()` — consistent with `tool_use`-based flow.
5. All 11 tests pass locally (confirmed by running the suite — `11 passed, 12 warnings in 22.39s`).
Security pass: endpoint retains `IsAuthenticated` + `IsAgentOrAdmin` permissions, no PII logged, no raw SQL, file input validated before use. The dead `file_block is None` guard is left in place as a defensive fallback — acceptable. No scope creep, no regressions detected.

2026-04-23 — rentals-tester: All 11 tests pass. pytest apps/test_hub/properties/integration/test_municipal_bill_view.py -v — 11 passed, 0 failed.
