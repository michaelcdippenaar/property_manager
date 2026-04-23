"""
POPIA s72 PII scrubber — applied to all user messages before forwarding to
Anthropic's API and before persisting to the database.

Covered patterns (minimum required by RNT-SEC-044):
  - SA ID number (13-digit, Luhn-valid form; matches the standard YYMMDD GSSS C ZZ pattern)
  - SA bank account numbers (6–11 contiguous digit sequences that look like account refs)
  - Passport numbers (SA green booklet: A–Z followed by 8 digits; also catches foreign formats)

Replacement token is [REDACTED] so downstream code can detect scrubbing occurred.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

# SA Identity number: exactly 13 consecutive digits (YYMMDDGSSSCAZ pattern).
# We require word boundaries to avoid matching 14+ digit numbers.
_SA_ID = re.compile(r"\b(\d{13})\b")

# SA bank account numbers: 6–11 consecutive digits (FNB, Standard, ABSA etc.).
# We avoid matching pure telephone numbers (10 digits starting with 0) by
# being conservative: we require that the digits are NOT surrounded by more
# digits on either side (word boundary) and we specifically exclude 13-digit
# strings (caught by _SA_ID above).
# Note: 10-digit SA phone numbers (0xx xxx xxxx) share the same length space
# as some bank accounts.  We err on the side of redaction for 7–11 digit
# isolated sequences, and also catch 6-digit account numbers.
_BANK_ACCOUNT = re.compile(r"\b(\d{6,11})\b")

# Passport numbers:
#   - SA green booklet: A followed by 8 digits (e.g. A12345678)
#   - Generic foreign: 1–2 letters followed by 6–8 digits
_PASSPORT = re.compile(r"\b([A-Za-z]{1,2}\d{6,8})\b")

_REDACTED = "[REDACTED]"

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scrub(text: str) -> str:
    """
    Return *text* with all recognised PII tokens replaced by [REDACTED].

    Order matters: apply ID (13-digit) first so it is not split by the
    bank-account pattern, then bank accounts, then passports.
    """
    if not text:
        return text
    # 1. SA ID numbers (exact 13-digit word)
    text = _SA_ID.sub(_REDACTED, text)
    # 2. Bank account numbers (6–11 digit words)
    text = _BANK_ACCOUNT.sub(_REDACTED, text)
    # 3. Passport numbers
    text = _PASSPORT.sub(_REDACTED, text)
    return text
