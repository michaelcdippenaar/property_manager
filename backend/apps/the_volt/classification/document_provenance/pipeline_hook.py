"""
THE VOLT — Pipeline hook.

Single entry point that wires `document_provenance` into the
classification flow. Call `attach_provenance(...)` ONCE per classified
document, immediately after the skill returns its `ExtractionResult`,
and you get back a `ProvenanceRecord` describing what we did.

Side-effects (in order):

  1. compute_fingerprint(doc_path)              [pure read, no I/O writes]
  2. broker.evaluate(vault_id, fp)              [in-mem or DB lookup]
  3. if DISCARD → return early, NO new VCN, NO stamp written
  4. mint_vcn(doc_type=…, sequence=…)
  5. build_stamp(…)                              [HMAC-signs the payload]
  6. write_sidecar_stamp(stamp, doc_path)        [<filename>.volt.json]
  7. embed_stamp_in_pdf_metadata(...)            [PDFs only, best-effort]
  8. broker.commit(vault_id, fp, vcn, doc_id)
  9. result.metadata['provenance'] = record.to_dict()
 10. return record

The function is designed for both production (DB-backed registry +
per-vault Django sequence) and tests (InMemoryFingerprintRegistry +
itertools.count). Everything injectable lives behind a Protocol or a
plain callable so the unit tests don't need Django at all.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Optional, Protocol

from .classification_number import VoltClassificationNumber, mint_vcn
from .duplicate_broker import (
    DuplicateBroker, DuplicateDecision, DuplicateEvaluation,
)
from .fingerprint import VoltFingerprint, compute_fingerprint
from .stamp import (
    VoltStamp, build_stamp, write_sidecar_stamp,
    embed_stamp_in_pdf_metadata,
)
from .submitter import SubmitterContext

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Injectables
# ---------------------------------------------------------------------------

class SequenceSupplier(Protocol):
    """Returns the next per-(vault, doc_type) sequence number.

    Production: backed by an atomic Django F() update on a per-vault row.
    Tests: any callable, e.g. `next(itertools.count(1))` wrapped in a
    closure scoped by doc_type.
    """
    def __call__(self, *, vault_id: int, doc_type: str) -> int: ...


VaultSecretLookup = Callable[[int], bytes]
"""Given a vault_id, return its 32-byte HMAC secret (loaded from KMS)."""


# ---------------------------------------------------------------------------
# Result envelope
# ---------------------------------------------------------------------------

@dataclass
class ProvenanceRecord:
    """The provenance trail for ONE classified document."""
    vcn: Optional[str]                          # None when DISCARDED to existing VCN
    decision: str                               # DuplicateDecision.value
    decision_rationale: str
    duplicate_of_vcn: Optional[str] = None      # set when DISCARD/UPDATE_LATEST
    fingerprint_sha256: str = ""
    fingerprint_size_bytes: int = 0
    fingerprint_extension: str = ""
    fingerprint_page_count: Optional[int] = None
    fingerprint_perceptual_hash: Optional[str] = None

    # Stamp artefacts
    stamp_hmac: Optional[str] = None
    stamp_classified_by: str = ""
    stamp_classified_at: Optional[str] = None
    sidecar_path: Optional[str] = None
    stamped_pdf_path: Optional[str] = None

    # Submitter snapshot — useful for downstream audit even if SubmitterContext is gone
    submitter_display: str = ""
    submitter_channel: str = ""

    # Bookkeeping
    vault_id: Optional[int] = None
    doc_type: str = ""
    classified_at_iso: str = ""
    notes: list[str] = field(default_factory=list)

    def is_duplicate(self) -> bool:
        return self.decision != DuplicateDecision.NOVEL.value

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def attach_provenance(
    *,
    extraction_result: Any,                     # apps.the_volt.classification.skills._shared.types.ExtractionResult
    doc_path: str | Path,
    doc_id: str,                                # storage backend's id (string for portability)
    vault_id: int,
    submitter: SubmitterContext,
    classified_by: str,                         # e.g. "skill:sa_smart_id_card@v1"
    broker: DuplicateBroker,
    sequence_supplier: SequenceSupplier,
    vault_secret_lookup: VaultSecretLookup,
    write_sidecar: bool = True,
    embed_in_pdf: bool = True,
    sidecar_dir: Optional[Path] = None,
    pdf_out_dir: Optional[Path] = None,
) -> ProvenanceRecord:
    """Attach a tamper-evident provenance trail to a classified document.

    Mutates `extraction_result.metadata['provenance']` in-place AND
    returns the record (so callers can persist it independently).
    """
    doc_path = Path(doc_path)
    doc_type = (extraction_result.doc_type or "").upper() or "UNKNOWN"

    # ── 1. fingerprint ──────────────────────────────────────────────────
    fp = compute_fingerprint(doc_path)

    # ── 2. duplicate broker ─────────────────────────────────────────────
    ev: DuplicateEvaluation = broker.evaluate(
        vault_id=vault_id, fp=fp, submitter=submitter,
    )

    base_record = ProvenanceRecord(
        vcn=None,
        decision=ev.decision.value,
        decision_rationale=ev.rationale,
        duplicate_of_vcn=ev.match.existing_vcn if ev.match else None,
        fingerprint_sha256=fp.sha256,
        fingerprint_size_bytes=fp.size_bytes,
        fingerprint_extension=fp.extension,
        fingerprint_page_count=fp.page_count,
        fingerprint_perceptual_hash=fp.perceptual_hash,
        submitter_display=submitter.submitter_display,
        submitter_channel=submitter.channel,
        vault_id=vault_id,
        doc_type=doc_type,
    )

    # ── 3. early-exit: exact duplicate, nothing new to stamp ────────────
    if ev.decision == DuplicateDecision.DISCARD:
        base_record.vcn = ev.match.existing_vcn if ev.match else None
        base_record.notes.append(
            "DISCARD — incoming bytes already classified; reusing existing VCN"
        )
        _attach_to_metadata(extraction_result, base_record)
        return base_record

    # ── 4. mint a fresh VCN ─────────────────────────────────────────────
    seq = sequence_supplier(vault_id=vault_id, doc_type=doc_type)
    vcn = mint_vcn(doc_type=doc_type, sequence=seq)
    base_record.vcn = vcn.format()

    # ── 5. build + sign stamp ───────────────────────────────────────────
    secret = vault_secret_lookup(vault_id)
    stamp: VoltStamp = build_stamp(
        vcn=vcn,
        doc_type=doc_type,
        fingerprint=fp,
        submitter=submitter,
        classified_by=classified_by,
        vault_id=vault_id,
        vault_secret=secret,
    )
    base_record.stamp_hmac = stamp.hmac_signature
    base_record.stamp_classified_by = stamp.classified_by
    base_record.stamp_classified_at = stamp.classified_at
    base_record.classified_at_iso = stamp.classified_at

    # ── 6. sidecar JSON (always works) ──────────────────────────────────
    if write_sidecar:
        try:
            sc = write_sidecar_stamp(stamp, doc_path, sidecar_dir=sidecar_dir)
            base_record.sidecar_path = str(sc)
        except Exception as e:  # noqa: BLE001
            logger.warning("sidecar stamp write failed for %s: %s", doc_path, e)
            base_record.notes.append(f"sidecar_failed: {e}")

    # ── 7. embed into PDF metadata (best-effort, PDFs only) ─────────────
    if embed_in_pdf and fp.extension == ".pdf":
        out_dir = pdf_out_dir or doc_path.parent
        out_pdf = out_dir / f"{doc_path.stem}.STAMPED.pdf"
        ok = embed_stamp_in_pdf_metadata(stamp, doc_path, out_pdf)
        if ok:
            base_record.stamped_pdf_path = str(out_pdf)
        else:
            base_record.notes.append("pdf_embed_skipped (encrypted or pypdf missing)")

    # ── 8. register fingerprint so future uploads can dedup ─────────────
    broker.commit(vault_id=vault_id, fp=fp, vcn=vcn.format(), doc_id=doc_id)

    # ── 9. attach + 10. return ──────────────────────────────────────────
    base_record.notes.append(
        f"NOVEL — VCN minted, stamp hmac={stamp.hmac_signature[:12]}…"
        if ev.decision == DuplicateDecision.NOVEL
        else f"{ev.decision.value} — superseding {ev.match.existing_vcn if ev.match else '?'}"
    )
    _attach_to_metadata(extraction_result, base_record)
    return base_record


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _attach_to_metadata(result: Any, record: ProvenanceRecord) -> None:
    """Attach the record dict to `result.metadata['provenance']`.

    `metadata` is created if missing, so this works on any duck-typed
    object that has a `metadata` attribute (or `setattr`-able dict).
    """
    md = getattr(result, "metadata", None)
    if md is None:
        try:
            setattr(result, "metadata", {})
            md = result.metadata
        except Exception:
            return
    md["provenance"] = record.to_dict()


# ---------------------------------------------------------------------------
# Default suppliers (use these in tests / dev; production overrides them)
# ---------------------------------------------------------------------------

def make_in_memory_sequence_supplier() -> SequenceSupplier:
    """Reference SequenceSupplier: per-(vault, doc_type) counter held in RAM.

    Production swaps this for a Django-backed atomic F() update so two
    workers stamping concurrently can't collide on the same sequence.
    """
    counters: dict[tuple[int, str], int] = {}

    def _next(*, vault_id: int, doc_type: str) -> int:
        key = (vault_id, doc_type.upper())
        counters[key] = counters.get(key, 0) + 1
        return counters[key]

    return _next


def make_static_secret_lookup(secret: bytes) -> VaultSecretLookup:
    """Reference VaultSecretLookup: same secret for every vault.

    Production replaces this with a KMS / Django settings lookup keyed
    by vault_id so each owner's stamps verify under their own key.
    """
    def _lookup(vault_id: int) -> bytes:
        return secret
    return _lookup
