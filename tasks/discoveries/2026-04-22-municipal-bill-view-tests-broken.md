---
discovered_by: rentals-tester
discovered_during: RNT-SEC-026
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found
7 tests in `apps/test_hub/properties/integration/test_municipal_bill_view.py` are failing. The view appears to have changed its error message format and response logic (returning 502 for unsupported MIME instead of 400; error messages changed from "Claude API error" to "Claude API failed after 3 attempts: ..."; tool_use block responses changed).

## Why it matters
The municipal bill parsing feature has no passing integration tests — regressions won't be caught.

## Where I saw it
- `apps/test_hub/properties/integration/test_municipal_bill_view.py`
- `test_unsupported_mime_returns_400` — 502 != 400
- `test_claude_api_error_returns_502` — error message mismatch ("Claude API failed after 3 attempts: ..." vs "Claude API error")
- `test_claude_invalid_json_returns_502_with_raw_preview` — "invalid JSON" not found in "Claude response contained no tool_use block."
- `test_happy_path_image_returns_extracted_json` / `test_happy_path_pdf_uses_document_block` — 502 != 200

## Suggested acceptance criteria (rough)
- [ ] All 10 `test_municipal_bill_view.py` tests pass

## Why I didn't fix it in the current task
Out of scope. This task covers IP extraction utility only.
