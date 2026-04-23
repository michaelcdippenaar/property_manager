"""
SA Smart ID Card — extraction entry point.

This is the LOCAL AGENT for one document type. It does NOT call the LLM
in an open-ended loop — we use a deterministic Python flow that drives
the per-field crop+OCR + validators (the "agent" in this case is the
field-typed Haiku vision call inside `tools.crop_and_ocr_field`).

A future variant could swap this for an Anthropic tool-use loop with
the prompt at `prompt.md`, but the deterministic flow is cheaper,
easier to debug, and trivial to score against gold examples.

CLI usage:
  ANTHROPIC_API_KEY=... python3 -m apps.the_volt.classification.skills.sa_smart_id_card.run \\
      --image "/path/to/George ID_Front.jpg" \\
      [--back "/path/to/George ID_Back.jpg"] \\
      [--crop-dir /tmp/sa_smart_id_crops] \\
      [--model claude-haiku-4-5]

Programmatic:
  from apps.the_volt.classification.skills.sa_smart_id_card import extract
  result = extract(Path("..."))
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from apps.the_volt.classification.skills._shared.types import (
    ExtractionResult, FieldResult,
)
from apps.the_volt.classification.skills._shared.provenance import (
    Citation, Claim, make_citation_from_field,
)
from apps.the_volt.classification.skills._shared.sa_id import decode_sa_id
from .layout import LAYOUT_FRONT, LAYOUT_BACK
from . import tools as T

logger = logging.getLogger(__name__)

SKILL_VERSION = "skill:sa_smart_id_card@v1"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def extract(
    image_path: Path,
    *,
    back_image_path: Optional[Path] = None,
    crop_dir: Optional[Path] = None,
    model: str = "claude-haiku-4-5",
    document_sha256: str = "",
) -> ExtractionResult:
    """Run the full SA Smart ID Card extraction flow.

    Returns a populated `ExtractionResult` whose `metadata` includes:
      - "claims": list of provenance-bearing Claim dicts (id_number, surname, …)
      - "front_back_match": bool (only present if back_image_path supplied)
      - "sa_id_decoded": dict of {date_of_birth, sex, citizenship}
    """
    crop_dir = crop_dir or Path("/tmp/sa_smart_id_crops")
    crop_dir.mkdir(parents=True, exist_ok=True)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    import anthropic
    client = anthropic.Anthropic()

    # ── 1. layout detect ────────────────────────────────────────────────
    det = T.detect_layout(str(image_path))
    if not det["ok"]:
        return ExtractionResult(
            doc_type="SA_SMART_ID_CARD",
            layout_name=LAYOUT_FRONT.name,
            layout_score=0.0,
            errors=[f"layout_detect_fail:{det['reason']}"],
        )
    result = ExtractionResult(
        doc_type="SA_SMART_ID_CARD",
        layout_name=det["layout_name"],
        layout_score=det["layout_score"],
        metadata={"image_w": det["image_w"], "image_h": det["image_h"]},
    )

    # ── 2. id_number FIRST (root identifier) ────────────────────────────
    id_field = LAYOUT_FRONT.field_by_name("id_number")
    id_res = T.crop_and_ocr_field(
        image_path=str(image_path), field_name="id_number",
        side="front", crop_dir=str(crop_dir), client=client, model=model,
    )
    id_value = id_res.get("value")
    result.crops["id_number"] = id_res.get("crop_path", "")
    result.fields["id_number"] = FieldResult(
        name="id_number", value=id_value, confidence=id_res.get("confidence", 0.0),
        raw=id_res.get("raw"), field_type="digits",
    )

    if not id_value:
        result.errors.append("id_number_unreadable")
    else:
        v = T.validate_id_number_tool(id_value)
        if not v["ok"]:
            result.errors.append(v["note"])
            result.fields["id_number"].error = v["note"]
            result.fields["id_number"].confidence = min(result.fields["id_number"].confidence, 0.4)
        if v.get("decoded"):
            result.metadata["sa_id_decoded"] = v["decoded"]

    # ── 3. all other front fields ───────────────────────────────────────
    for fld in LAYOUT_FRONT.fields:
        if fld.name == "id_number":
            continue
        r = T.crop_and_ocr_field(
            image_path=str(image_path), field_name=fld.name,
            side="front", crop_dir=str(crop_dir), client=client, model=model,
        )
        result.crops[fld.name] = r.get("crop_path", "")
        result.fields[fld.name] = FieldResult(
            name=fld.name, value=r.get("value"), confidence=r.get("confidence", 0.0),
            raw=r.get("raw"), field_type=fld.field_type,
        )
        if fld.required and not r.get("value"):
            result.warnings.append(f"required_field_empty:{fld.name}")

    # ── 4. cross-checks (DOB + sex against ID) ──────────────────────────
    if id_value:
        dob_text = (result.fields.get("date_of_birth").value or "") if "date_of_birth" in result.fields else ""
        if dob_text:
            d = T.validate_dob_tool(id_value, dob_text)
            if not d["ok"]:
                result.errors.append(f"dob_id_{d['note']}")
        sex_text = (result.fields.get("sex").value or "") if "sex" in result.fields else ""
        if sex_text:
            s = T.validate_sex_tool(id_value, sex_text)
            if not s["ok"]:
                result.errors.append(f"sex_id_{s['note']}")

    # ── 5. (optional) back face — barcode + cross-match ─────────────────
    if back_image_path:
        det_b = T.detect_layout(str(back_image_path))
        if not det_b["ok"]:
            result.warnings.append(f"back_layout_detect_fail:{det_b['reason']}")
        else:
            barcode = T.read_pdf417_back(str(back_image_path))
            if barcode["ok"]:
                front_payload = {
                    k: (v.value or "") for k, v in result.fields.items()
                }
                cmp = T.compare_front_back(front_payload, barcode["fields"])
                result.metadata["front_back_match"] = cmp["ok"]
                result.metadata["barcode_payload"] = barcode["fields"]
                if not cmp["ok"]:
                    for m in cmp["mismatches"]:
                        result.errors.append(m)
            else:
                # Fall back to OCR'd MRZ lines (each line OCR'd as a typed string)
                mrz_payload = {}
                for mrz_field in ("mrz_line_1", "mrz_line_2", "mrz_line_3"):
                    r = T.crop_and_ocr_field(
                        image_path=str(back_image_path), field_name=mrz_field,
                        side="back", crop_dir=str(crop_dir), client=client, model=model,
                    )
                    mrz_payload[mrz_field] = r.get("value", "")
                result.metadata["barcode_unavailable_reason"] = barcode.get("reason")
                result.metadata["mrz_payload"] = mrz_payload

    # ── 6. confidence rollup ────────────────────────────────────────────
    field_confs = [f.confidence for f in result.fields.values()
                   if f.field_type != "image" and f.confidence is not None]
    avg = sum(field_confs) / len(field_confs) if field_confs else 0.0
    cap = 1.0
    if "luhn_fail" in result.errors or any("dob_id_" in e for e in result.errors) \
       or any("sex_id_" in e for e in result.errors):
        cap = 0.4
    if any("front_back_mismatch" in e for e in result.errors):
        cap = min(cap, 0.5)
    if "id_number_unreadable" in result.errors:
        cap = min(cap, 0.3)
    result.overall_confidence = round(min(avg, cap), 3)

    # ── 7. emit Claims (provenance-bearing) ─────────────────────────────
    claims_out: list[dict] = []
    if document_sha256:
        for fname, fr in result.fields.items():
            fld = LAYOUT_FRONT.field_by_name(fname)
            if not fld or not fr.value:
                continue
            attr_name = _field_to_attribute(fname)
            if not attr_name:
                continue
            cit = make_citation_from_field(
                document_path=str(image_path),
                document_sha256=document_sha256,
                layout_field_name=fname,
                bbox_norm=fld.bbox,
                extracted_value=str(fr.value),
                extracted_by=SKILL_VERSION,
                confidence=fr.confidence,
                page=1,
            )
            claim = Claim(
                entity_id="",     # router fills this once it knows the silo id
                attribute=attr_name,
                value=fr.value,
                citations=[cit],
                confidence=fr.confidence,
                status="PROPOSED",
            )
            claims_out.append({
                "attribute": claim.attribute,
                "value": claim.value,
                "confidence": claim.confidence,
                "citation": {
                    "document_path": cit.document_path,
                    "document_sha256": cit.document_sha256,
                    "page": cit.page,
                    "bbox": list(cit.bbox) if cit.bbox else None,
                    "field_name": cit.field_name,
                    "extracted_quote": cit.extracted_quote,
                    "extracted_by": cit.extracted_by,
                },
            })
    result.metadata["claims"] = claims_out

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Map layout field-names → entity attribute names (snake_case)
_FIELD_TO_ATTR = {
    "id_number": "id_number",
    "surname": "surname",
    "names": "given_names",
    "sex": "sex",
    "nationality": "nationality",
    "date_of_birth": "date_of_birth",
    "country_of_birth": "country_of_birth",
}

def _field_to_attribute(field_name: str) -> Optional[str]:
    return _FIELD_TO_ATTR.get(field_name)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="Path to front-face image (JPG/PNG/PDF)")
    ap.add_argument("--back", help="Path to back-face image (for cross-match)")
    ap.add_argument("--crop-dir", default="/tmp/sa_smart_id_crops")
    ap.add_argument("--model", default="claude-haiku-4-5")
    ap.add_argument("--sha256", default="", help="SHA-256 of the source file (for Citations)")
    ap.add_argument("--out", default=None, help="Write JSON result here")
    args = ap.parse_args()

    res = extract(
        Path(args.image),
        back_image_path=Path(args.back) if args.back else None,
        crop_dir=Path(args.crop_dir),
        model=args.model,
        document_sha256=args.sha256,
    )

    payload = {
        "doc_type": res.doc_type,
        "layout_name": res.layout_name,
        "layout_score": res.layout_score,
        "overall_confidence": res.overall_confidence,
        "errors": res.errors,
        "warnings": res.warnings,
        "fields": {k: {"value": v.value, "raw": v.raw, "confidence": v.confidence,
                       "field_type": v.field_type, "error": v.error}
                   for k, v in res.fields.items()},
        "crops": res.crops,
        "metadata": res.metadata,
    }
    out = json.dumps(payload, indent=2, default=str)
    print(out)
    if args.out:
        Path(args.out).write_text(out)


if __name__ == "__main__":
    main()
