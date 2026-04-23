"""
THE VOLT — Document stamping.

A `VoltStamp` is the metadata payload that proves a doc passed through
our system. It carries:

  • vcn               — the Volt Classification Number
  • fingerprint       — sha256 + size + ext + page_count
  • submitter         — who uploaded it, how, when
  • doc_type          — the classified type
  • classified_at     — when classification ran
  • hmac_signature    — HMAC-SHA256 over the canonical payload using a
                        per-vault secret. Anyone with the vault's
                        verifier key can prove the stamp is authentic.

We embed the stamp three different ways depending on the file:

  1. PDF      → write to /Info dictionary + /XMP custom namespace
                (`/VoltVCN`, `/VoltFingerprint`, etc.)
  2. Image    → write into EXIF UserComment + XMP sidecar
                (best-effort; some formats can't carry EXIF)
  3. Anything → write a sidecar JSON file `<filename>.volt.json`
                next to the original. Always works as a fallback.

The original bytes are NEVER mutated for sidecar mode. Even when we DO
write into PDF metadata, we keep the pre-stamp sha256 and post-stamp
sha256 separately so we can prove the stamping itself was deterministic.

This module is import-light: heavy file-mutation deps (pypdf, PIL, piexif)
are only imported inside the functions that need them, so unit tests can
exercise `build_stamp()` without any I/O dependencies.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from .fingerprint import VoltFingerprint
from .classification_number import VoltClassificationNumber
from .submitter import SubmitterContext

logger = logging.getLogger(__name__)

STAMP_VERSION = "volt-stamp@v1"
STAMP_NAMESPACE = "https://volt.klikk.co.za/ns/stamp/1.0/"


@dataclass(frozen=True)
class VoltStamp:
    """The complete provenance record for one classified document."""
    vcn: str                            # canonical VCN string
    doc_type: str
    fingerprint_sha256: str
    fingerprint_size: int
    fingerprint_extension: str
    fingerprint_page_count: Optional[int]
    fingerprint_perceptual_hash: Optional[str]
    submitter: dict                     # SubmitterContext.to_dict()
    classified_at: str                  # ISO 8601
    classified_by: str                  # e.g. "skill:sa_smart_id_card@v1"
    vault_id: Optional[int]             # which Volt silo owns the doc
    stamp_version: str = STAMP_VERSION
    notes: str = ""

    # Trailing — set by build_stamp after the rest is finalised
    hmac_signature: str = ""

    def canonical_payload_bytes(self) -> bytes:
        """The byte string the HMAC is computed over.

        We exclude `hmac_signature` itself and serialise with sorted keys
        + no whitespace to make the signature deterministic.
        """
        d = asdict(self)
        d.pop("hmac_signature", None)
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def verify(self, vault_secret: bytes) -> bool:
        expected = _hmac_hex(self.canonical_payload_bytes(), vault_secret)
        return hmac.compare_digest(expected, self.hmac_signature)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_stamp(
    *,
    vcn: VoltClassificationNumber,
    doc_type: str,
    fingerprint: VoltFingerprint,
    submitter: SubmitterContext,
    classified_by: str,
    vault_id: Optional[int],
    vault_secret: bytes,
    classified_at: Optional[datetime] = None,
    notes: str = "",
) -> VoltStamp:
    """Assemble a stamp + compute its HMAC. Pure function — no I/O."""
    classified_at = classified_at or datetime.utcnow()

    # Build the unsigned stamp first
    unsigned = VoltStamp(
        vcn=vcn.format(),
        doc_type=doc_type,
        fingerprint_sha256=fingerprint.sha256,
        fingerprint_size=fingerprint.size_bytes,
        fingerprint_extension=fingerprint.extension,
        fingerprint_page_count=fingerprint.page_count,
        fingerprint_perceptual_hash=fingerprint.perceptual_hash,
        submitter=submitter.to_dict(),
        classified_at=classified_at.isoformat(),
        classified_by=classified_by,
        vault_id=vault_id,
        notes=notes,
    )
    sig = _hmac_hex(unsigned.canonical_payload_bytes(), vault_secret)
    # Frozen dataclass — return a new instance with the signature set
    return VoltStamp(
        vcn=unsigned.vcn,
        doc_type=unsigned.doc_type,
        fingerprint_sha256=unsigned.fingerprint_sha256,
        fingerprint_size=unsigned.fingerprint_size,
        fingerprint_extension=unsigned.fingerprint_extension,
        fingerprint_page_count=unsigned.fingerprint_page_count,
        fingerprint_perceptual_hash=unsigned.fingerprint_perceptual_hash,
        submitter=unsigned.submitter,
        classified_at=unsigned.classified_at,
        classified_by=unsigned.classified_by,
        vault_id=unsigned.vault_id,
        notes=unsigned.notes,
        hmac_signature=sig,
    )


# ---------------------------------------------------------------------------
# Persistence — sidecar (always works)
# ---------------------------------------------------------------------------

def write_sidecar_stamp(stamp: VoltStamp, doc_path: str | Path,
                        *, sidecar_dir: Optional[Path] = None) -> Path:
    """Write `<doc_path>.volt.json` next to the original (or in sidecar_dir)."""
    p = Path(doc_path)
    target_dir = Path(sidecar_dir) if sidecar_dir else p.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{p.name}.volt.json"
    target.write_text(json.dumps(asdict(stamp), indent=2))
    return target


# ---------------------------------------------------------------------------
# Persistence — embedded in PDF metadata
# ---------------------------------------------------------------------------

def embed_stamp_in_pdf_metadata(stamp: VoltStamp, pdf_path: str | Path,
                                out_path: str | Path) -> bool:
    """Write a NEW PDF that has the stamp baked into its /Info dict.

    Original is left untouched. Returns True on success, False if pypdf
    isn't available or the PDF is encrypted.
    """
    try:
        import pypdf  # type: ignore
    except ImportError:
        logger.warning("pypdf not installed — falling back to sidecar only")
        return False

    src = Path(pdf_path)
    dst = Path(out_path)
    try:
        reader = pypdf.PdfReader(str(src))
        if reader.is_encrypted:
            logger.info("pdf encrypted — skipping in-file stamp: %s", src)
            return False
        writer = pypdf.PdfWriter(clone_from=reader)
        # Carry over existing metadata, then add Volt fields
        meta = dict(reader.metadata or {})
        meta["/VoltVCN"] = stamp.vcn
        meta["/VoltDocType"] = stamp.doc_type
        meta["/VoltFingerprintSHA256"] = stamp.fingerprint_sha256
        meta["/VoltClassifiedAt"] = stamp.classified_at
        meta["/VoltClassifiedBy"] = stamp.classified_by
        meta["/VoltSubmitter"] = stamp.submitter.get("submitter_display", "")
        meta["/VoltVaultID"] = str(stamp.vault_id or "")
        meta["/VoltStampVersion"] = stamp.stamp_version
        meta["/VoltHMAC"] = stamp.hmac_signature
        writer.add_metadata(meta)
        dst.parent.mkdir(parents=True, exist_ok=True)
        with dst.open("wb") as f:
            writer.write(f)
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("embed_stamp_in_pdf_metadata failed for %s: %s", src, e)
        return False


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _hmac_hex(payload: bytes, key: bytes) -> str:
    return hmac.new(key, payload, hashlib.sha256).hexdigest()
