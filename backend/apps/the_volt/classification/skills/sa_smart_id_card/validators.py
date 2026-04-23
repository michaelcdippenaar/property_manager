"""
Validators specific to SA Smart ID Card extractions.

Each validator returns (ok: bool, note: str). The skill collects every
note and uses them to cap the overall confidence.
"""
from __future__ import annotations

from typing import Optional

from apps.the_volt.classification.skills._shared.sa_id import (
    decode_sa_id, cross_check_id_vs_dob, cross_check_id_vs_sex,
)


def validate_id_number(id_number: str) -> tuple[bool, str]:
    d = decode_sa_id(id_number)
    if not d:
        return False, "id_undecodable"
    if not d.luhn_ok:
        return False, "luhn_fail"
    return True, "ok"


def validate_dob_against_id(id_number: str, dob_text: str) -> tuple[bool, str]:
    return cross_check_id_vs_dob(id_number, dob_text)


def validate_sex_against_id(id_number: str, sex_text: str) -> tuple[bool, str]:
    return cross_check_id_vs_sex(id_number, sex_text)


def validate_nationality(value: Optional[str]) -> tuple[bool, str]:
    """SA Smart ID Cards typically print 'RSA' for SA citizens."""
    if not value:
        return False, "nationality_missing"
    if value.strip().upper() in ("RSA", "ZAF"):
        return True, "ok"
    # Permanent residents / foreigners may legitimately have other codes
    return True, f"nationality_non_rsa:{value!r}"


def front_back_consistency(
    front_fields: dict,
    back_payload: dict,
) -> list[str]:
    """Compare critical fields across front (OCR) and back (PDF417 decode).

    `back_payload` is the decoded barcode dict (or, fallback, an OCR'd
    MRZ that we parsed into a dict).

    Returns list of mismatch notes — empty list = perfect match.
    """
    mismatches = []
    for field in ("id_number", "surname", "names", "date_of_birth", "sex"):
        f = (front_fields.get(field) or "").strip().upper()
        b = (back_payload.get(field) or "").strip().upper()
        if f and b and f != b:
            mismatches.append(f"front_back_mismatch:{field}:front={f!r}!=back={b!r}")
    return mismatches
