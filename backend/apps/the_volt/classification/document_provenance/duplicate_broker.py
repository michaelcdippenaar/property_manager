"""
THE VOLT — Duplicate broker.

When a new file arrives we want to answer two questions BEFORE running
any expensive classification:

  1. Have I seen this file before? (exact / near / perceptual match)
  2. If yes — what should I do with the new copy?

The DuplicateBroker is a pure decision engine + an in-memory or
backend-pluggable fingerprint registry. It returns a `DuplicateDecision`
the caller acts on:

  • DISCARD          — exact duplicate, drop the upload, return existing VCN
  • UPDATE_LATEST    — same file content but better source (e.g. higher
                       resolution scan replacing older lower-res one)
  • KEEP_BOTH        — different enough to be a separate doc (e.g. two
                       people's ID cards on the same template)
  • MERGE            — different file, same logical document
                       (e.g. front + back of one ID card → one logical doc)
  • NOVEL            — never seen before, proceed with classification

Wired into the pipeline:

       upload
         │
         ▼
   compute_fingerprint
         │
         ▼
   broker.evaluate(fingerprint, submitter)
         │
   ┌─────┴───────────────────────────┐
   │ NOVEL            → classify     │
   │ DISCARD          → return VCN   │
   │ UPDATE_LATEST    → re-stamp     │
   │ MERGE/KEEP_BOTH  → flag review  │
   └─────────────────────────────────┘

The registry interface is a Protocol so the same broker logic works
against an in-memory dict (tests), a Django queryset (production), or a
ChromaDB collection (perceptual neighbour search).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Iterable, Optional, Protocol

from .fingerprint import VoltFingerprint, fingerprint_matches
from .submitter import SubmitterContext

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Decisions
# ---------------------------------------------------------------------------

class DuplicateDecision(str, Enum):
    NOVEL = "NOVEL"
    DISCARD = "DISCARD"
    UPDATE_LATEST = "UPDATE_LATEST"
    KEEP_BOTH = "KEEP_BOTH"
    MERGE = "MERGE"


@dataclass(frozen=True)
class DuplicateMatch:
    """A hit against the registry."""
    existing_vcn: str
    existing_doc_id: str               # storage backend's doc id (string for portability)
    existing_fingerprint: VoltFingerprint
    match_kind: str                    # 'EXACT' | 'NEAR' | 'PERCEPTUAL'
    matched_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DuplicateEvaluation:
    decision: DuplicateDecision
    match: Optional[DuplicateMatch] = None
    rationale: str = ""

    def is_duplicate(self) -> bool:
        return self.decision != DuplicateDecision.NOVEL


# ---------------------------------------------------------------------------
# Registry protocol
# ---------------------------------------------------------------------------

class FingerprintRegistry(Protocol):
    """Backend that knows about every classified file in a vault."""

    def lookup_exact(self, vault_id: int, fp: VoltFingerprint) -> Optional[DuplicateMatch]:
        ...

    def lookup_near(self, vault_id: int, fp: VoltFingerprint) -> Optional[DuplicateMatch]:
        ...

    def lookup_perceptual(self, vault_id: int, fp: VoltFingerprint,
                          *, max_distance: int = 4) -> Optional[DuplicateMatch]:
        ...

    def register(self, vault_id: int, fp: VoltFingerprint,
                 vcn: str, doc_id: str) -> None:
        ...


# ---------------------------------------------------------------------------
# In-memory reference implementation (tests + dev)
# ---------------------------------------------------------------------------

class InMemoryFingerprintRegistry:
    """Reference impl. Production swaps for a Django-backed implementation."""

    def __init__(self):
        self._rows: list[tuple[int, VoltFingerprint, str, str]] = []

    def lookup_exact(self, vault_id, fp):
        for vid, existing, vcn, doc_id in self._rows:
            if vid == vault_id and existing.matches_exact(fp):
                return DuplicateMatch(existing_vcn=vcn, existing_doc_id=doc_id,
                                      existing_fingerprint=existing, match_kind="EXACT")
        return None

    def lookup_near(self, vault_id, fp):
        for vid, existing, vcn, doc_id in self._rows:
            if vid == vault_id and existing.matches_near(fp) and not existing.matches_exact(fp):
                return DuplicateMatch(existing_vcn=vcn, existing_doc_id=doc_id,
                                      existing_fingerprint=existing, match_kind="NEAR")
        return None

    def lookup_perceptual(self, vault_id, fp, *, max_distance=4):
        for vid, existing, vcn, doc_id in self._rows:
            if vid != vault_id:
                continue
            if existing.matches_exact(fp) or existing.matches_near(fp):
                continue   # already handled by stricter layers
            if existing.matches_perceptual(fp, max_distance=max_distance):
                return DuplicateMatch(existing_vcn=vcn, existing_doc_id=doc_id,
                                      existing_fingerprint=existing, match_kind="PERCEPTUAL")
        return None

    def register(self, vault_id, fp, vcn, doc_id):
        self._rows.append((vault_id, fp, vcn, doc_id))


# ---------------------------------------------------------------------------
# Broker
# ---------------------------------------------------------------------------

@dataclass
class DuplicateBrokerPolicy:
    """Knobs for what to do per match-kind. Cleaner files always WIN —
    if the incoming upload has higher page-count or larger size at the
    NEAR layer, we update; if it's same-or-worse we discard."""
    on_exact: DuplicateDecision = DuplicateDecision.DISCARD
    on_near_better: DuplicateDecision = DuplicateDecision.UPDATE_LATEST
    on_near_equal_or_worse: DuplicateDecision = DuplicateDecision.DISCARD
    on_perceptual: DuplicateDecision = DuplicateDecision.KEEP_BOTH
    perceptual_max_distance: int = 4


class DuplicateBroker:
    """Pure decision logic + thin registry adapter."""

    def __init__(self, registry: FingerprintRegistry,
                 policy: Optional[DuplicateBrokerPolicy] = None):
        self.registry = registry
        self.policy = policy or DuplicateBrokerPolicy()

    def evaluate(self, *, vault_id: int, fp: VoltFingerprint,
                 submitter: Optional[SubmitterContext] = None) -> DuplicateEvaluation:
        # Layer 1: exact byte-for-byte
        m = self.registry.lookup_exact(vault_id, fp)
        if m:
            return DuplicateEvaluation(
                decision=self.policy.on_exact, match=m,
                rationale=f"exact sha256 match → {m.existing_vcn}",
            )
        # Layer 2: near (same start-of-file + dimensions)
        m = self.registry.lookup_near(vault_id, fp)
        if m:
            decision = (self.policy.on_near_better
                        if _is_better_copy(fp, m.existing_fingerprint)
                        else self.policy.on_near_equal_or_worse)
            return DuplicateEvaluation(
                decision=decision, match=m,
                rationale=f"near match (same first-4MiB + dims) → {m.existing_vcn}; "
                          f"better={decision == self.policy.on_near_better}",
            )
        # Layer 3: perceptual (re-scanned image of the same page)
        m = self.registry.lookup_perceptual(
            vault_id, fp, max_distance=self.policy.perceptual_max_distance,
        )
        if m:
            return DuplicateEvaluation(
                decision=self.policy.on_perceptual, match=m,
                rationale=f"perceptual match (phash distance ≤ {self.policy.perceptual_max_distance}) "
                          f"→ {m.existing_vcn} — flagging for human review",
            )
        return DuplicateEvaluation(decision=DuplicateDecision.NOVEL,
                                   rationale="no fingerprint match in vault")

    def commit(self, *, vault_id: int, fp: VoltFingerprint,
               vcn: str, doc_id: str) -> None:
        """Call this after a NOVEL upload has been stamped & stored."""
        self.registry.register(vault_id, fp, vcn, doc_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_better_copy(new: VoltFingerprint, old: VoltFingerprint) -> bool:
    """Heuristic: bigger + more pages + higher resolution = better.

    Used when two files are NEAR-equal — we keep the higher-quality copy.
    """
    score_new = (new.size_bytes
                 + (new.page_count or 0) * 1_000_000
                 + (new.image_width or 0) * (new.image_height or 0))
    score_old = (old.size_bytes
                 + (old.page_count or 0) * 1_000_000
                 + (old.image_width or 0) * (old.image_height or 0))
    return score_new > score_old
