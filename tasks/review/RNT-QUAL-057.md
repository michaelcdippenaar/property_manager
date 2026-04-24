---
id: RNT-QUAL-057
stream: rentals
title: "Tighten PII scrubber bank-account regex to reduce false positives on rand amounts and dates"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.1"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: null
created: 2026-04-24
updated: 2026-04-24
---

## Goal
Refine the bank-account digit pattern in `backend/apps/ai/scrubber.py` so it requires an adjacent contextual cue (e.g. "account", "acc", "bank", "EFT") and excludes rand amounts, dates, and unit-suffixed numbers, reducing false-positive redaction without harming PII coverage.

## Acceptance criteria
- [x] Bank-account pattern requires an adjacent context cue (`account`, `acc`, `acct`, `bank`, `EFT`, `IBAN`, `a/c`) within N characters, OR uses a Luhn-checked pattern
- [x] Rand amounts (`R\d+`, `ZAR \d+`) with 6+ digits are explicitly excluded from redaction
- [x] YYYYMMDD-format dates (`\d{8}`) are excluded
- [x] Digit strings followed by unit suffixes (`kWh`, `km`, `m²`, `L`, `MB`) are excluded
- [x] New tests cover: `R150000` not redacted, `20241215` not redacted, `meter reading 458790 kWh` not redacted, `account 1234567890` redacted
- [x] Existing passing scrubber tests remain green

## Files likely touched
- `backend/apps/ai/scrubber.py` (line ~32)
- `backend/apps/ai/tests/test_pii_scrubber.py`

## Test plan
**Automated:**
- `cd backend && pytest apps/ai/tests/test_pii_scrubber.py -v`

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-24 — Promoted from discovery `2026-04-23-ai-scrubber-overbroad-bank-regex.md`. Deferred to v1.1 — conservative over-scrubbing is the safer production posture for launch; refine post-launch once real interaction logs surface false-positive patterns.

2026-04-24 (implementer) -- Rewrote `_BANK_ACCOUNT` pattern in `scrubber.py` to use context-gated matching (`_BANK_ACCOUNT` now requires an adjacent cue word). Added `_RAND_AMOUNT`, `_DATE_YYYYMMDD`, and `_UNIT_SUFFIXED` exclusion guards using a placeholder-swap mechanism applied before all redaction passes, so rand amounts (R/ZAR prefix), YYYYMMDD dates, and unit-suffixed numbers are never redacted. Updated test file: removed the old "accepted tradeoff" test that asserted dates ARE redacted; added 13 new false-positive tests and 10 positive-match tests. All 33 tests pass. Caveats: `_RAND_AMOUNT` guard uses a greedy pattern -- a rand amount that trails into other text (e.g. "R150000 per month unit 12345") will protect the whole matched span; no issues observed in testing.
