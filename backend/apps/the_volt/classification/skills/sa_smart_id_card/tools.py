"""
Tools the SA-Smart-ID-Card local agent calls.

These wrap the per-field crop-then-OCR loop, the Luhn/DOB/sex
cross-checks, the optional PDF417 barcode read, and the final
emit_result envelope. Every tool returns a small JSON-friendly dict
so the agent loop can chain them.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from apps.the_volt.classification.skills._shared.image_io import load_image, aspect_ratio
from apps.the_volt.classification.skills._shared.types import (
    ExtractionResult, FieldResult,
)
from apps.the_volt.classification.skills._shared.vision_ocr import (
    crop_to_png_bytes, normalised_to_pixels, ocr_field, save_crop,
)
from apps.the_volt.classification.skills._shared.sa_id import (
    decode_sa_id, normalise_id_digits,
)
from .layout import LAYOUT_FRONT, LAYOUT_BACK
from .validators import (
    validate_id_number, validate_dob_against_id,
    validate_sex_against_id, validate_nationality,
    front_back_consistency,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Layout detection
# ---------------------------------------------------------------------------

def detect_layout(image_path: str) -> dict:
    """Return {ok, layout_name, layout_score, reason}."""
    img, info = load_image(Path(image_path))
    ar = aspect_ratio(img)
    delta = abs(ar - LAYOUT_FRONT.aspect_ratio)
    if delta > LAYOUT_FRONT.aspect_tolerance:
        return {
            "ok": False, "layout_name": LAYOUT_FRONT.name,
            "layout_score": 0.0,
            "reason": f"aspect_off:{ar:.3f}_target_{LAYOUT_FRONT.aspect_ratio}_tol_{LAYOUT_FRONT.aspect_tolerance}",
            "image_w": img.width, "image_h": img.height,
        }
    score = 1.0 - (delta / LAYOUT_FRONT.aspect_tolerance)
    return {
        "ok": True, "layout_name": LAYOUT_FRONT.name,
        "layout_score": round(0.55 + 0.45 * score, 3),
        "reason": f"aspect_ok:{ar:.3f}",
        "image_w": img.width, "image_h": img.height,
    }


# ---------------------------------------------------------------------------
# Field crop + OCR
# ---------------------------------------------------------------------------

def crop_and_ocr_field(
    *,
    image_path: str,
    field_name: str,
    side: str = "front",
    crop_dir: Optional[str] = None,
    client=None,
    model: str = "claude-haiku-4-5",
) -> dict:
    """Crop the named field, OCR it, save the crop, return {value, raw, confidence, crop_path}."""
    layout = LAYOUT_FRONT if side == "front" else LAYOUT_BACK
    fld = layout.field_by_name(field_name)
    if not fld:
        return {"ok": False, "error": f"unknown_field:{field_name}"}

    img, info = load_image(Path(image_path))
    pixels = normalised_to_pixels(fld.bbox, img.width, img.height)
    crop_png = crop_to_png_bytes(img, pixels)

    crop_path = None
    if crop_dir:
        crop_path = str(save_crop(crop_png, Path(crop_dir), field_name))

    if fld.field_type == "image":
        return {
            "ok": True, "field": field_name, "field_type": "image",
            "raw": None, "value": None, "confidence": 1.0,
            "crop_path": crop_path, "bbox_pixels": pixels,
        }

    res = ocr_field(
        crop_png_bytes=crop_png,
        field_type=fld.field_type,
        extra_hint=fld.hint,
        model=model,
        client=client,
    )

    raw = res.raw
    if raw.upper() == "UNREADABLE":
        value = None
        conf = 0.0
    elif fld.field_type == "digits":
        value = normalise_id_digits(raw) if field_name == "id_number" else "".join(c for c in raw if c.isdigit())
        conf = res.confidence
    elif fld.field_type == "gender":
        value = raw.strip().upper()[:1] if raw.strip() else None
        conf = res.confidence
    else:
        value = raw.strip()
        conf = res.confidence

    return {
        "ok": True, "field": field_name, "field_type": fld.field_type,
        "raw": raw, "value": value, "confidence": conf,
        "crop_path": crop_path, "bbox_pixels": pixels,
        "in_tokens": res.in_tokens, "out_tokens": res.out_tokens,
        "seconds": round(res.seconds, 2),
    }


# ---------------------------------------------------------------------------
# Barcode (PDF417) on the back face
# ---------------------------------------------------------------------------

def read_pdf417_back(image_path: str) -> dict:
    """Decode the PDF417 barcode on the back of an SA Smart ID Card.

    Tries `pyzbar` first (single-pass), falls back to `zxing` if installed.
    Returns {ok, fields: {id_number, surname, names, date_of_birth, sex}, raw}
    or {ok: False, reason} if no decoder is available.
    """
    try:
        from pyzbar.pyzbar import decode as zbar_decode  # type: ignore
        from PIL import Image
        img = Image.open(image_path)
        results = zbar_decode(img)
        if not results:
            return {"ok": False, "reason": "no_pdf417_found"}
        raw = results[0].data.decode("utf-8", errors="replace")
        return {"ok": True, "raw": raw, "fields": _parse_dha_pdf417(raw)}
    except ImportError:
        return {
            "ok": False,
            "reason": "no_decoder_installed",
            "hint": "pip install pyzbar (and `brew install zbar` on macOS)",
        }
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": f"decode_error:{e}"}


def _parse_dha_pdf417(raw: str) -> dict:
    """The DHA PDF417 payload is pipe-delimited (per public reverse-engineering
    write-ups). We extract the fields we need and ignore the signature blob.
    Schema example: 'IDZAF|0|<surname>|<names>|<id_no>|<dob YYYYMMDD>|M|RSA|...'
    """
    parts = raw.split("|")
    out = {}
    if not parts or parts[0] != "IDZAF":
        return out
    try:
        out["surname"] = parts[2].strip()
        out["names"] = parts[3].strip()
        out["id_number"] = parts[4].strip()
        dob = parts[5].strip()
        if len(dob) == 8 and dob.isdigit():
            out["date_of_birth"] = f"{dob[6:8]} {_mon_short(int(dob[4:6]))} {dob[0:4]}"
        out["sex"] = parts[6].strip()
        out["nationality"] = parts[7].strip()
    except IndexError:
        pass
    return out


_MONS = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"]
def _mon_short(m: int) -> str:
    return _MONS[m - 1] if 1 <= m <= 12 else str(m)


# ---------------------------------------------------------------------------
# Compare front + back
# ---------------------------------------------------------------------------

def compare_front_back(front_fields: dict, back_payload: dict) -> dict:
    mismatches = front_back_consistency(front_fields, back_payload)
    return {"ok": not mismatches, "mismatches": mismatches}


# ---------------------------------------------------------------------------
# Validators (expose as tools)
# ---------------------------------------------------------------------------

def validate_id_number_tool(id_number: str) -> dict:
    ok, note = validate_id_number(id_number)
    decoded = decode_sa_id(id_number)
    return {
        "ok": ok, "note": note,
        "decoded": {
            "date_of_birth": decoded.date_of_birth.isoformat() if decoded else None,
            "sex": decoded.sex if decoded else None,
            "citizenship": decoded.citizenship if decoded else None,
        } if decoded else None,
    }


def validate_dob_tool(id_number: str, dob_text: str) -> dict:
    ok, note = validate_dob_against_id(id_number, dob_text)
    return {"ok": ok, "note": note}


def validate_sex_tool(id_number: str, sex_text: str) -> dict:
    ok, note = validate_sex_against_id(id_number, sex_text)
    return {"ok": ok, "note": note}
