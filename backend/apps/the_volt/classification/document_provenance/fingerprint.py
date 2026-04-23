"""
THE VOLT — Physical file fingerprint.

A `VoltFingerprint` is the answer to "is this physically the same file?"

Three layers of equality, increasing in tolerance:

  1. EXACT  — sha256 + byte-size + extension match.
              Same bytes on disk. Highest confidence dedup.

  2. NEAR   — same sha256_first_4mb + same page_count + same dimensions.
              Same file content even if metadata bytes differ
              (PDF re-saved, JPEG re-encoded with identical visual data).

  3. PERCEPTUAL — phash distance ≤ threshold (images only).
              Same picture taken slightly differently
              (a re-scanned ID card on a different scanner).

The DuplicateBroker walks these layers in order and decides what to do
with the new upload (discard / merge / update / keep both).

External deps: PyPDF2/pypdf for page count, PIL+imagehash for perceptual.
All optional — any failure degrades gracefully to fewer signal layers.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 4 MiB — enough to fingerprint the meaningful start of any document
# without slurping a 200-page PDF into RAM. Two PDFs that differ only
# in the trailing /Producer and /CreationDate metadata still hash
# identically on the first 4 MiB.
_FAST_HASH_BYTES = 4 * 1024 * 1024


@dataclass(frozen=True)
class VoltFingerprint:
    """All the things that physically identify a file. Frozen → hashable."""
    sha256: str                     # full-file sha256 (hex)
    sha256_first_4mb: str           # first-N sha256 (for near-dup)
    size_bytes: int
    extension: str                  # ".pdf" — lowercase
    mime_type_guess: Optional[str] = None

    # Optional richer signal — present when libs are installed and parse OK
    page_count: Optional[int] = None        # PDFs
    image_width: Optional[int] = None       # images / first PDF page
    image_height: Optional[int] = None
    perceptual_hash: Optional[str] = None   # imagehash.phash hex (images)

    # Bookkeeping
    file_path_at_compute: str = ""

    # ---- equality helpers ------------------------------------------------

    def matches_exact(self, other: "VoltFingerprint") -> bool:
        return (self.sha256 == other.sha256
                and self.size_bytes == other.size_bytes
                and self.extension == other.extension)

    def matches_near(self, other: "VoltFingerprint") -> bool:
        # Same start-of-file + same dimensions/page count
        if self.sha256_first_4mb != other.sha256_first_4mb:
            return False
        if self.page_count is not None and other.page_count is not None:
            if self.page_count != other.page_count:
                return False
        if (self.image_width is not None and other.image_width is not None
                and self.image_width != other.image_width):
            return False
        return True

    def matches_perceptual(self, other: "VoltFingerprint", *, max_distance: int = 4) -> bool:
        """Hamming distance between phash hexes (images only)."""
        if not self.perceptual_hash or not other.perceptual_hash:
            return False
        return _hamming_hex(self.perceptual_hash, other.perceptual_hash) <= max_distance


# ---------------------------------------------------------------------------
# Compute
# ---------------------------------------------------------------------------

def compute_fingerprint(path: str | Path) -> VoltFingerprint:
    """Read a file once, fingerprint everything we can.

    Cost: O(file_size) for the sha256, plus optional PDF/image parse.
    Cheaper than any LLM call by orders of magnitude.
    """
    p = Path(path)
    size = p.stat().st_size
    ext = p.suffix.lower()

    sha_full, sha_fast = _hash_file(p)

    page_count = None
    width = height = None
    phash_hex = None
    mime_guess = _guess_mime(ext)

    if ext == ".pdf":
        page_count = _try_pdf_page_count(p)
        # Try to render page 1 for phash + dimensions (best-effort)
        try:
            width, height, phash_hex = _try_pdf_first_page_image_signals(p)
        except Exception as e:  # noqa: BLE001
            logger.debug("pdf first-page signals skipped for %s: %s", p, e)
    elif ext in {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp"}:
        try:
            width, height, phash_hex = _try_image_signals(p)
        except Exception as e:  # noqa: BLE001
            logger.debug("image signals skipped for %s: %s", p, e)

    return VoltFingerprint(
        sha256=sha_full,
        sha256_first_4mb=sha_fast,
        size_bytes=size,
        extension=ext,
        mime_type_guess=mime_guess,
        page_count=page_count,
        image_width=width,
        image_height=height,
        perceptual_hash=phash_hex,
        file_path_at_compute=str(p),
    )


def fingerprint_matches(
    a: VoltFingerprint, b: VoltFingerprint,
    *, perceptual_threshold: int = 4,
) -> str:
    """Return the strongest equivalence class that holds: 'EXACT' | 'NEAR' | 'PERCEPTUAL' | ''."""
    if a.matches_exact(b):
        return "EXACT"
    if a.matches_near(b):
        return "NEAR"
    if a.matches_perceptual(b, max_distance=perceptual_threshold):
        return "PERCEPTUAL"
    return ""


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _hash_file(p: Path) -> tuple[str, str]:
    """Single-pass: full sha256 + first-4MiB sha256."""
    full = hashlib.sha256()
    fast = hashlib.sha256()
    consumed = 0
    with p.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            full.update(chunk)
            if consumed < _FAST_HASH_BYTES:
                # Trim the chunk so fast-hash caps at exactly 4 MiB
                take = min(len(chunk), _FAST_HASH_BYTES - consumed)
                fast.update(chunk[:take])
                consumed += take
    return full.hexdigest(), fast.hexdigest()


_MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png", ".tif": "image/tiff", ".tiff": "image/tiff",
    ".webp": "image/webp", ".bmp": "image/bmp",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".rtf": "application/rtf",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

def _guess_mime(ext: str) -> Optional[str]:
    return _MIME_BY_EXT.get(ext)


def _try_pdf_page_count(p: Path) -> Optional[int]:
    try:
        import pypdf  # type: ignore
        return len(pypdf.PdfReader(str(p)).pages)
    except Exception:
        try:
            import fitz  # PyMuPDF — type: ignore
            with fitz.open(str(p)) as doc:
                return doc.page_count
        except Exception:
            return None


def _try_pdf_first_page_image_signals(p: Path) -> tuple[Optional[int], Optional[int], Optional[str]]:
    """Render PDF page 1 → grab dimensions + phash. Best-effort."""
    try:
        import fitz  # type: ignore
        with fitz.open(str(p)) as doc:
            if doc.page_count == 0:
                return None, None, None
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=72)        # 72dpi = enough for phash
            from PIL import Image
            import imagehash  # type: ignore
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            return pix.width, pix.height, str(imagehash.phash(img))
    except Exception:
        return None, None, None


def _try_image_signals(p: Path) -> tuple[Optional[int], Optional[int], Optional[str]]:
    try:
        from PIL import Image
        import imagehash  # type: ignore
        with Image.open(p) as img:
            return img.width, img.height, str(imagehash.phash(img))
    except Exception:
        # Dimensions without phash if imagehash isn't installed
        try:
            from PIL import Image
            with Image.open(p) as img:
                return img.width, img.height, None
        except Exception:
            return None, None, None


def _hamming_hex(h1: str, h2: str) -> int:
    """Bitwise hamming distance between two equal-length hex strings."""
    if len(h1) != len(h2):
        return max(len(h1), len(h2)) * 4   # max possible
    return bin(int(h1, 16) ^ int(h2, 16)).count("1")
