"""
SA ID-number primitives shared across every identity skill.

A South African ID number is 13 digits: YYMMDD SSSS C A Z
  YYMMDD  date of birth
  SSSS    sex code: 0000-4999 = female, 5000-9999 = male
  C       citizenship: 0 = SA citizen, 1 = permanent resident
  A       race indicator (legacy, always 8 or 9 since 1986)
  Z       Luhn check digit over the preceding 12 digits

We share this here so the Smart-ID-Card, Green-ID-Book, Passport,
Birth-Certificate and Driver's-Licence skills all decode/validate the
same way.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Optional


SA_ID_RE = re.compile(r"^\d{13}$")


@dataclass(frozen=True)
class SAIDDecoded:
    id_number: str
    date_of_birth: date
    sex: str                 # "M" or "F"
    citizenship: str         # "SA_CITIZEN" or "PERMANENT_RESIDENT"
    luhn_ok: bool


def luhn_check(digits: str) -> bool:
    """Standard Luhn over a digit string (final digit is the check digit)."""
    total = 0
    parity = len(digits) % 2
    for i, ch in enumerate(digits):
        d = int(ch)
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def decode_sa_id(raw: str, *, century_pivot: int = 25) -> Optional[SAIDDecoded]:
    """Decode a 13-digit SA ID. Returns None if structurally invalid.

    century_pivot: YY <= pivot → 20YY else 19YY.  Default 25 (today is 2026).
    """
    s = re.sub(r"\D", "", raw or "")
    if not SA_ID_RE.match(s):
        return None

    yy, mm, dd = int(s[0:2]), int(s[2:4]), int(s[4:6])
    century = 2000 if yy <= century_pivot else 1900
    try:
        dob = date(century + yy, mm, dd)
    except ValueError:
        return None

    sex_code = int(s[6:10])
    sex = "M" if sex_code >= 5000 else "F"

    cit = "SA_CITIZEN" if s[10] == "0" else "PERMANENT_RESIDENT"

    return SAIDDecoded(
        id_number=s,
        date_of_birth=dob,
        sex=sex,
        citizenship=cit,
        luhn_ok=luhn_check(s),
    )


def normalise_id_digits(raw: str) -> str:
    """Strip everything that isn't a digit. Useful for dirty OCR output."""
    return re.sub(r"\D", "", raw or "")


def cross_check_id_vs_dob(id_number: str, dob_text: str) -> tuple[bool, str]:
    """Return (ok, note). dob_text may be in any common SA format."""
    decoded = decode_sa_id(id_number)
    if not decoded:
        return False, "id_undecodable"
    parsed_dob = _parse_dob(dob_text)
    if not parsed_dob:
        return False, "dob_unparseable"
    if parsed_dob != decoded.date_of_birth:
        return False, f"dob_mismatch:{parsed_dob.isoformat()}!={decoded.date_of_birth.isoformat()}"
    return True, "ok"


def cross_check_id_vs_sex(id_number: str, sex_text: str) -> tuple[bool, str]:
    decoded = decode_sa_id(id_number)
    if not decoded:
        return False, "id_undecodable"
    s = (sex_text or "").strip().upper()[:1]
    if s not in ("M", "F"):
        return False, f"sex_unparseable:{sex_text!r}"
    if s != decoded.sex:
        return False, f"sex_mismatch:doc={s}!=id={decoded.sex}"
    return True, "ok"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
    # Afrikaans
    "JANUARIE": 1, "FEBRUARIE": 2, "MAART": 3, "APRIL": 4, "MEI": 5,
    "JUNIE": 6, "JULIE": 7, "AUGUSTUS": 8, "SEPTEMBER": 9,
    "OKTOBER": 10, "NOVEMBER": 11, "DESEMBER": 12,
}


def _parse_dob(text: str) -> Optional[date]:
    """Try the SA-common date formats: 'DD MMM YYYY', 'YYYY-MM-DD',
    'DD/MM/YYYY', 'YYYY/MM/DD', 'DD MMMM YYYY'."""
    if not text:
        return None
    t = text.strip().upper().replace(",", "")
    # DD MMM YYYY  or  DD MMMM YYYY
    m = re.match(r"^(\d{1,2})\s+([A-Z]+)\s+(\d{4})$", t)
    if m:
        d, mon_s, y = m.groups()
        mon = _MONTHS.get(mon_s) or _MONTHS.get(mon_s[:3])
        if mon:
            try: return date(int(y), mon, int(d))
            except ValueError: return None
    # YYYY-MM-DD or YYYY/MM/DD
    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", t)
    if m:
        y, mo, d = m.groups()
        try: return date(int(y), int(mo), int(d))
        except ValueError: return None
    # DD-MM-YYYY or DD/MM/YYYY
    m = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", t)
    if m:
        d, mo, y = m.groups()
        try: return date(int(y), int(mo), int(d))
        except ValueError: return None
    return None
