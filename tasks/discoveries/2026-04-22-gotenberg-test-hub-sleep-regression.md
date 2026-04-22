---
discovered_by: rentals-reviewer
discovered_during: RNT-QUAL-002
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found
`backend/apps/test_hub/esigning/unit/test_gotenberg.py` — `TestHtmlToPdf.test_raises_on_http_error` (line 60) does not patch `time.sleep`. The new retry loop in `gotenberg.html_to_pdf` introduced by RNT-QUAL-002 makes 4 attempts with 1s+2s+4s backoff sleeps, so this previously-instant unit test now sleeps 7 real seconds on every CI run.

## Why it matters
Every CI run of the test_hub esigning suite will be 7 seconds slower. As the suite grows and more callers exercise this path, the drag compounds. The test was fast by design (unit, mocked HTTP) — the regression undermines that contract.

## Where I saw it
- `backend/apps/test_hub/esigning/unit/test_gotenberg.py:60-73`
- Fix applied to the task-local test file (`backend/apps/leases/tests/test_pdf_resilience.py`) but not backported to the test_hub counterpart.

## Suggested acceptance criteria (rough)
- [ ] `test_raises_on_http_error` decorated with `@patch("time.sleep")` (or `@patch("apps.esigning.gotenberg.time.sleep")`)
- [ ] All other `TestHtmlToPdf` tests in test_gotenberg.py audited for missing sleep patch and fixed where needed
- [ ] Test suite runtime for `test_hub/esigning/unit/` remains under 2 seconds total

## Why I didn't fix it in the current task
Out of scope — fixing test_hub tests not listed in RNT-QUAL-002 acceptance criteria would broaden the diff. Requires a targeted quality pass on the test_hub esigning suite.
