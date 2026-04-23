# Skill — SA Smart ID Card extractor

**Document:** South African Smart ID Card (DHA, polycarbonate CR80, 2013+)
**Side:** Front + Back
**Entry point:** `skills.sa_smart_id_card.run.extract(image_path) -> ExtractionResult`

## What this skill does

Given an image of one face of a SA Smart ID Card, this skill:

1. **Verifies layout** — aspect ratio is in [1.516, 1.656] (CR80 ± tolerance) and at least one of the anchor strings ("REPUBLIC OF SOUTH AFRICA", "Identity Number", "Surname") is visible.
2. **Crops every field** by the normalised bbox map in `layout.py`.
3. **OCRs each crop** with a field-typed prompt (digits-only for ID number, name-typed for surname, etc.) using Claude Haiku vision.
4. **Validates** — Luhn check on the 13-digit ID, DOB cross-check (first 6 digits of ID == structured DOB field), sex cross-check (digits 7-10 vs the M/F field), nationality default = RSA.
5. **(Back face)** — OCRs the PDF417 barcode if present (or the printed MRZ-style lines) and **cross-matches every field against the front**. Mismatch → `errors.append("front_back_mismatch:<field>")`.
6. **Returns** an `ExtractionResult` with per-field confidence, the saved bbox crops, and the canonical 13-digit ID number ready to seed a `NaturalPersonSilo`.

## What this skill DOES NOT do

- Does not vectorise the raw image (Identity-First doctrine).
- Does not call any 3rd-party verifier (DHA HANIS / ContactAble) — that's the job of `id_verifier/`.
- Does not create the `NaturalPersonSilo` — that's the job of the `entities/silo_engine`.
- Does not try to handle the Green ID Book — see `sa_green_id_book/`.

## Inputs

| arg | type | required | notes |
|---|---|---|---|
| `image_path` | `Path` | ✓ | JPG/PNG of the front face. PDF accepted (page 1 rendered at 300 DPI). |
| `back_image_path` | `Path` | ✗ | If supplied, runs front-back cross-match. |
| `crop_dir` | `Path` | ✗ | Where to save bbox crops for audit. Default: `/tmp/sa_smart_id_crops/`. |
| `model` | `str` | ✗ | Claude vision model. Default: `claude-haiku-4-5`. |

## Output schema

```python
ExtractionResult(
    doc_type="SA_SMART_ID_CARD",
    layout_name="SA Smart ID Card 2013+ (front)",
    layout_score=0.92,
    fields={
        "id_number":       FieldResult(value="8001015009087", confidence=0.97, ...),
        "surname":         FieldResult(value="DU PREEZ", ...),
        "names":           FieldResult(value="GEORGE FREDERICK", ...),
        "sex":             FieldResult(value="M", ...),
        "nationality":     FieldResult(value="RSA", ...),
        "country_of_birth":FieldResult(value="RSA", ...),
        "date_of_birth":   FieldResult(value="01 JAN 1980", ...),
        ...
    },
    crops={"photo": "/tmp/.../photo.png", ...},
    overall_confidence=0.93,
    metadata={"sa_id_decoded": {...}, "front_back_match": True},
)
```

## Failure modes (and what we do)

| Failure | Behaviour |
|---|---|
| Wrong aspect ratio | Skill refuses to run, layout_score=0.0, returns empty result. Router escalates to `sa_green_id_book` or `sa_drivers_licence`. |
| Luhn fails | `errors.append("luhn_fail")`, overall_confidence capped at 0.4, person silo NOT created. |
| DOB mismatch | `errors.append("dob_id_mismatch")`, capped at 0.4. |
| Front-back mismatch | `errors.append("front_back_mismatch:<field>")`, capped at 0.5 — **possible forgery**, flag for human review. |
| OCR returns UNREADABLE for required field | Field marked `confidence=0.0`, overall capped at 0.5. |

## Cost target

Front face only: ~10 fields × ~200 input tokens each = ~2k tokens × $1/MTok = **~$0.002 per card**.
With back-face cross-match: ~$0.004 per card.

## Tests

`examples/` contains gold input/output pairs for regression. Run with:
```bash
python3 -m apps.the_volt.classification.skills.sa_smart_id_card.run \
    --image examples/george_du_preez_front.jpg --gold examples/george_du_preez.json
```
