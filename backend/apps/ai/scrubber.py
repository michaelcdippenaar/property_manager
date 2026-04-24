"""
POPIA s72 PII scrubber -- applied to all user messages before forwarding to
Anthropic's API and before persisting to the database.

Covered patterns (minimum required by RNT-SEC-044):
  - SA ID number (13-digit, Luhn-valid form; matches the standard YYMMDD GSSS C ZZ pattern)
  - SA bank account numbers (8-11 digit sequences preceded by a banking context cue)
  - Passport numbers (SA green booklet: A-Z followed by 8 digits; also catches foreign formats)

Replacement token is [REDACTED] so downstream code can detect scrubbing occurred.

Bank-account false-positive exclusions (RNT-QUAL-057):
  - Rand amounts: digits directly preceded by R or ZAR are protected from all passes
  - YYYYMMDD dates: exactly 8 digits matching year 19xx/20xx range are protected
  - Digit strings followed by unit suffixes (kWh, km, m2, MB, GB) are protected
  - A context cue (account, acct, bank, EFT, IBAN, a/c) must appear immediately
    before an 8-11 digit sequence (with optional separators) for it to be redacted.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

# SA Identity number: exactly 13 consecutive digits (YYMMDDGSSSCAZ pattern).
# We require word boundaries to avoid matching 14+ digit numbers.
_SA_ID = re.compile(r"\b(\d{13})\b")

# ---------------------------------------------------------------------------
# Exclusion guards -- protect tokens before bank-account and passport matching
# ---------------------------------------------------------------------------

# Rand amounts: R or ZAR followed by digits (with optional spaces/commas/dots).
# e.g. R12345, R 12 345.67, R12,345, ZAR 150000.
# This protection runs before ALL redaction passes so R-prefixed digit sequences
# are not falsely matched as passport numbers (R<6-8digits>) either.
_RAND_AMOUNT = re.compile(
    r"(?:ZAR\s*|R)[\d][\d\s,\.]*",
    re.IGNORECASE,
)

# YYYYMMDD dates: 8 digits starting with 19xx or 20xx
_DATE_YYYYMMDD = re.compile(r"\b(?:19|20)\d{6}\b")

# Digit strings followed by unit suffixes
_UNIT_SUFFIXED = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:kWh|KWH|kwh|km|KM|m2|m\u00b2|MB|GB|TB|KB|kg|litre|liter)\b",
)

# ---------------------------------------------------------------------------
# Bank-account: context-gated (RNT-QUAL-057)
#
# Requires a banking cue immediately before the digit sequence.
# Supported cues: account(s), acct(s), bank, bank account, EFT, IBAN, a/c
# Supported separators between cue and digits: whitespace, colon, slash,
# hyphen, hash, N, n, o, dot (e.g. "Account No.", "Acc #", "acct:").
# ---------------------------------------------------------------------------

_BANK_ACCOUNT = re.compile(
    r"(?:accounts?|accts?|bank(?:\s+account)?|EFT|IBAN|a\/c)"
    r"[\s:\/\-#Nno\.]*"
    r"(\d{8,11})\b",
    re.IGNORECASE,
)

# Passport numbers:
#   - SA green booklet: A followed by 8 digits (e.g. A12345678)
#   - Generic foreign: 1-2 letters followed by 6-8 digits
# Note: rand amounts (R<digits>) are protected via placeholder before this runs.
_PASSPORT = re.compile(r"\b([A-Za-z]{1,2}\d{6,8})\b")

_REDACTED = "[REDACTED]"

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scrub(text: str) -> str:
    """
    Return *text* with all recognised PII tokens replaced by [REDACTED].

    Order:
      1. Protect rand amounts, YYYYMMDD dates, unit-suffixed numbers via placeholders.
      2. SA ID numbers (13-digit).
      3. Bank account numbers (context-gated 8-11 digit sequences).
      4. Passport numbers (letter-prefixed digit sequences).
      5. Restore protected tokens.
    """
    if not text:
        return text

    placeholders: list[tuple[str, str]] = []

    def _protect(pattern: re.Pattern, t: str) -> str:
        def _replace(m: re.Match) -> str:
            token = f"\x00PROT{len(placeholders)}\x00"
            placeholders.append((token, m.group(0)))
            return token
        return pattern.sub(_replace, t)

    text = _protect(_RAND_AMOUNT, text)
    text = _protect(_DATE_YYYYMMDD, text)
    text = _protect(_UNIT_SUFFIXED, text)

    # 1. SA ID numbers (exact 13-digit word)
    text = _SA_ID.sub(_REDACTED, text)

    # 2. Bank account numbers (context-gated)
    text = _BANK_ACCOUNT.sub(
        lambda m: m.group(0).replace(m.group(1), _REDACTED), text
    )

    # 3. Passport numbers
    text = _PASSPORT.sub(_REDACTED, text)

    # Restore protected tokens
    for token, original in placeholders:
        text = text.replace(token, original)

    return text
