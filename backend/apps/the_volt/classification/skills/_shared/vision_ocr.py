"""
Field-typed vision OCR.

Each skill crops its layout's bboxes and asks Claude (Haiku for cost) to
read each crop with a field-type-specific prompt. The model never sees
the whole document at once — it sees one ~200x80 px crop at a time and
is told exactly what kind of value lives there.

Why crop-then-OCR instead of "send the whole image"?
  • 70-90% token saving (1 small crop ≈ 1.5k tokens vs ~12k for full ID)
  • Field-typed prompts ("read 13 digits") prevent hallucinated text
  • Failed fields can be re-tried independently (with deskew, contrast,
    upscale) without re-OCR'ing the whole document
  • Bbox crops become the audit trail — we save them next to the result
"""
from __future__ import annotations

import base64
import io
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


FIELD_TYPE_PROMPTS = {
    "digits": (
        "Read the digits in this image. Output ONLY the digits, no spaces, "
        "no labels, no commentary. If the value is unreadable, output exactly: UNREADABLE."
    ),
    "name": (
        "Read the given name(s) in this image. Output the name exactly as printed, "
        "preserving capitalisation and spacing. No labels, no commentary."
    ),
    "surname": (
        "Read the surname (last name) in this image. Output ONLY the surname, "
        "exactly as printed. No labels, no commentary."
    ),
    "date_dmy": (
        "Read the date in this image. Normalise to format: DD MMM YYYY "
        "(e.g. '15 JAN 1980'). If the date is unreadable, output: UNREADABLE."
    ),
    "date_yyyymmdd": (
        "Read the date and output in ISO format YYYY-MM-DD. "
        "If unreadable, output: UNREADABLE."
    ),
    "gender": (
        "Read the sex/gender field. Output exactly one character: M or F. "
        "If unreadable, output: UNREADABLE."
    ),
    "country_iso2": (
        "Read the country code in this image. Output the 3-letter ISO code "
        "(e.g. RSA, ZIM, NAM). If you can only see the full country name, output the ISO-3 code for it. "
        "If unreadable, output: UNREADABLE."
    ),
    "mrz_line": (
        "Read this machine-readable zone line EXACTLY, including '<' filler "
        "characters. Output only the line, no commentary."
    ),
    "place_of_birth": (
        "Read the place-of-birth field. Output the place exactly as printed."
    ),
    "text": (
        "Read the text in this image exactly as printed. No commentary, "
        "no labels. If unreadable, output: UNREADABLE."
    ),
}


@dataclass
class OCRResult:
    raw: str
    confidence: float
    in_tokens: int
    out_tokens: int
    seconds: float


def ocr_field(
    *,
    crop_png_bytes: bytes,
    field_type: str,
    extra_hint: str = "",
    model: str = "claude-haiku-4-5",
    client=None,
) -> OCRResult:
    """OCR a single bbox crop with a field-typed prompt.

    `client` is an `anthropic.Anthropic()` instance (caller-supplied so we
    don't open a new HTTP session per field).
    """
    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        import anthropic  # lazy
        client = anthropic.Anthropic()

    base_prompt = FIELD_TYPE_PROMPTS.get(field_type, FIELD_TYPE_PROMPTS["text"])
    if extra_hint:
        prompt = f"{base_prompt}\nContext: {extra_hint}"
    else:
        prompt = base_prompt

    b64 = base64.standard_b64encode(crop_png_bytes).decode("ascii")
    t0 = time.time()
    msg = client.messages.create(
        model=model,
        max_tokens=80,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64", "media_type": "image/png", "data": b64,
                }},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    dt = time.time() - t0
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()

    # Heuristic confidence from the model's own output:
    if text.upper() == "UNREADABLE":
        conf = 0.0
    elif field_type == "digits":
        # All-digit fields: require model output to actually be digits
        digits = "".join(c for c in text if c.isdigit())
        conf = 0.85 if len(digits) >= 3 else 0.0
    elif field_type == "gender":
        conf = 0.95 if text.strip().upper() in ("M", "F") else 0.0
    else:
        conf = 0.85 if text else 0.0

    return OCRResult(
        raw=text,
        confidence=conf,
        in_tokens=msg.usage.input_tokens,
        out_tokens=msg.usage.output_tokens,
        seconds=dt,
    )


def crop_to_png_bytes(pil_image, bbox_pixels: tuple[int, int, int, int]) -> bytes:
    """Crop the PIL image to bbox_pixels (L,U,R,D) and return PNG bytes."""
    crop = pil_image.crop(bbox_pixels)
    buf = io.BytesIO()
    crop.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def normalised_to_pixels(
    norm_bbox: tuple[float, float, float, float],
    img_w: int,
    img_h: int,
) -> tuple[int, int, int, int]:
    x, y, w, h = norm_bbox
    return (
        max(0, int(x * img_w)),
        max(0, int(y * img_h)),
        min(img_w, int((x + w) * img_w)),
        min(img_h, int((y + h) * img_h)),
    )


def save_crop(crop_png: bytes, dest: Path, name: str) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"{name}.png"
    path.write_bytes(crop_png)
    return path
