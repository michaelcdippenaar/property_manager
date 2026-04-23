"""
Image loading + PDF-to-image fallback used by every identity skill.

Caller passes a Path; we figure out:
  • JPG/PNG → load directly with Pillow
  • PDF (single-page identity scan) → render page 1 at 300 DPI via pdf2image
    (poppler) OR fall back to pypdf-extracted images
  • PDF (multi-page) → render the page that looks most like an ID
    (largest aspect-deviation from text-page A4 portrait)

Returns a PIL.Image.Image and a dict of metadata (width, height, source).
"""
from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def load_image(path: Path):
    """Return (PIL.Image, info_dict).

    Raises RuntimeError if the file can't be loaded as an image.
    """
    from PIL import Image

    suffix = path.suffix.lower()
    if suffix in (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"):
        img = Image.open(path).convert("RGB")
        return img, {
            "width": img.width,
            "height": img.height,
            "source": "image",
            "page": None,
        }

    if suffix == ".pdf":
        return _load_pdf_first_image_page(path)

    raise RuntimeError(f"Unsupported file type for identity extraction: {suffix}")


def _load_pdf_first_image_page(path: Path):
    """Try pdf2image first (best fidelity). Fall back to extracting embedded
    images via pypdf if poppler isn't installed."""
    from PIL import Image

    # Strategy 1: pdf2image (poppler-backed, render at 300 DPI)
    try:
        from pdf2image import convert_from_path
        pages = convert_from_path(str(path), dpi=300)
        if pages:
            img = pages[0].convert("RGB")
            return img, {
                "width": img.width, "height": img.height,
                "source": "pdf:pdf2image", "page": 1,
            }
    except Exception as e:  # noqa: BLE001
        logger.debug("pdf2image unavailable for %s: %s", path, e)

    # Strategy 2: extract embedded images via pypdf
    try:
        from pypdf import PdfReader
        r = PdfReader(str(path))
        for page_no, page in enumerate(r.pages, start=1):
            for image in (getattr(page, "images", []) or []):
                try:
                    img = Image.open(io.BytesIO(image.data)).convert("RGB")
                    if img.width >= 600:   # skip thumbnails / icons
                        return img, {
                            "width": img.width, "height": img.height,
                            "source": "pdf:pypdf-embedded", "page": page_no,
                        }
                except Exception:
                    continue
    except Exception as e:  # noqa: BLE001
        logger.debug("pypdf image extraction failed for %s: %s", path, e)

    # Strategy 3: PyMuPDF (fitz) — last resort, often pre-installed for OCR
    try:
        import fitz  # type: ignore
        doc = fitz.open(str(path))
        for page_no in range(len(doc)):
            page = doc.load_page(page_no)
            pix = page.get_pixmap(dpi=300)
            png = pix.tobytes("png")
            img = Image.open(io.BytesIO(png)).convert("RGB")
            return img, {
                "width": img.width, "height": img.height,
                "source": "pdf:pymupdf", "page": page_no + 1,
            }
    except Exception as e:  # noqa: BLE001
        logger.debug("PyMuPDF unavailable for %s: %s", path, e)

    raise RuntimeError(
        f"Could not render PDF {path} to an image. "
        "Install one of: pdf2image+poppler, PyMuPDF, or upgrade pypdf."
    )


def aspect_ratio(img) -> float:
    return img.width / max(img.height, 1)
