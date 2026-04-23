---
discovered_by: rentals-reviewer
discovered_during: RNT-SEC-044
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found

The PII scrubber's bank-account pattern `\b(\d{6,11})\b` (in `backend/apps/ai/scrubber.py`) matches any isolated 6–11 digit sequence. This is documented as a conservative tradeoff, but will silently mangle legitimate user input:

- `R150000` → `R[REDACTED]` (rand amounts with 6+ digits)
- `20241215` → `[REDACTED]` (YYYYMMDD dates)
- `meter reading 458790 kWh` → `meter reading [REDACTED] kWh`
- `invoice 7782311` → `invoice [REDACTED]`
- Any 10-digit SA phone number is collapsed to `[REDACTED]` too, even when sharing that is the user's explicit intent.

## Why it matters

Over-scrubbing degrades the quality of AI responses (the model loses meaningful numeric context it could otherwise act on) and produces confusing stored interaction logs for support. The current tests only verify the pattern fires, not that it preserves useful context. A tighter heuristic (require context words like "account"/"acc"/"bank"/"EFT" nearby, or exclude digit strings immediately preceded by currency `R`/`ZAR` or followed by unit words like `kWh`/`km`/`m²`) would preserve utility without harming PII coverage.

## Where I saw it

- `backend/apps/ai/scrubber.py:32`
- `backend/apps/ai/tests/test_pii_scrubber.py:114-124` — tests explicitly assert the redaction of `20241215` and (separately) allow `R1500` to pass (only because 4 digits is below the 6-digit threshold — `R150000` would not)

## Suggested acceptance criteria (rough)

- [ ] Bank-account pattern requires an adjacent context cue (e.g., `account`, `acc`, `acct`, `bank`, `EFT`, `IBAN`, `a/c`) within N characters, OR switches to a Luhn-checked narrower pattern
- [ ] Rand amounts (`R\d+`, `ZAR \d+`) are explicitly excluded
- [ ] Digits followed by unit suffixes (`kWh`, `km`, `m²`, `L`, `MB`) are excluded
- [ ] New tests cover the above false-positive cases

## Why I didn't fix it in the current task

It's a design decision the implementer made consciously and documented in the scrubber docstring. Changing the heuristic is a re-architecture, not a verification fix, so it belongs in a follow-up ticket for PM to prioritise.
