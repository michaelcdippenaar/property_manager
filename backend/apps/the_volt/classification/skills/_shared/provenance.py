"""
Provenance — every claim about an entity carries its source.

The rule: if you can't cite where it came from, you can't claim it.

A `Claim` is one assertion about an `Entity`'s `attribute`. It always
carries one or more `Citation` records that point to the document and
the location WITHIN the document where the value was found.

Search flow:
    "What is George's ID number?"
      → query Claims where (entity=George, attribute=id_number)
      → return canonical value + every Citation backing it

Reverse search:
    "Where does the claim 'George is a director of MoorAccountants' come from?"
      → query Claims where (subject=George, predicate=DIRECTOR_OF, object=MoorAccountants)
      → return Citation list

Slot-fill (the user's "search George ⇒ ID" rule):
    When a new document arrives with EMPTY typed slots (e.g. a fresh
    FICA Questionnaire with id_number_field, address_field, etc.) the
    engine pre-fills each slot with the canonical value from the entity's
    Claims, marked as PROPOSED (never auto-submitted — needs explicit
    user/owner confirmation per the Identity-First doctrine).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Citation — anchors a fact to a specific spot in a specific document
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Citation:
    document_path: str               # relative to vault root or absolute
    document_sha256: str             # immutable identity of the source file
    page: Optional[int] = None       # 1-based PDF page if applicable
    bbox: Optional[tuple[float, float, float, float]] = None  # normalised crop
    field_name: Optional[str] = None # which mapped layout field (e.g. "id_number")
    extracted_quote: Optional[str] = None  # 1–60 char snippet from source
    extracted_by: str = ""           # skill or model name (e.g. "skill:sa_smart_id_card@v1")
    extracted_at: datetime = field(default_factory=datetime.utcnow)
    extraction_confidence: float = 0.0


# ---------------------------------------------------------------------------
# Claim — one assertion about one (entity, attribute) tuple
# ---------------------------------------------------------------------------

@dataclass
class Claim:
    """A single asserted value for one entity attribute, with sources.

    A Claim is mutable in metadata only — citations are append-only.
    Two claims for the same (entity, attribute) with different `value`
    are a CONFLICT — the consensus engine resolves them.
    """
    entity_id: str                   # internal silo / entity ID
    attribute: str                   # canonical key, e.g. "id_number", "address"
    value: Any                       # the claimed value (string, dict, list, …)
    citations: list[Citation] = field(default_factory=list)
    confidence: float = 0.0          # rolled up from citations + validators
    verified_by_third_party: bool = False
    verifier: str = ""               # e.g. "DHA_HANIS", "ContactAble"
    verified_at: Optional[datetime] = None
    status: str = "PROPOSED"         # PROPOSED | CONFIRMED | DISPUTED | REJECTED
    notes: str = ""

    def add_citation(self, c: Citation) -> None:
        self.citations.append(c)
        # Rolled-up confidence: max of citation confidences, capped by validator results
        self.confidence = max(self.confidence, c.extraction_confidence)


# ---------------------------------------------------------------------------
# Relationship claim — for graph edges, e.g. DIRECTOR_OF, TRUSTEE_OF
# ---------------------------------------------------------------------------

@dataclass
class RelationshipClaim:
    """Same provenance discipline as Claim, but for entity-to-entity edges."""
    subject_entity_id: str
    predicate: str                   # e.g. "DIRECTOR_OF", "TRUSTEE_OF", "CHILD_OF"
    object_entity_id: str
    metadata: dict = field(default_factory=dict)   # share_pct, role, effective_date
    citations: list[Citation] = field(default_factory=list)
    confidence: float = 0.0
    status: str = "PROPOSED"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_citation_from_field(
    *,
    document_path: str,
    document_sha256: str,
    layout_field_name: str,
    bbox_norm: tuple[float, float, float, float],
    extracted_value: str,
    extracted_by: str,
    confidence: float,
    page: Optional[int] = 1,
) -> Citation:
    """Convenience: build a Citation from a skill's bbox-OCR output."""
    quote = (extracted_value or "")[:60]
    return Citation(
        document_path=document_path,
        document_sha256=document_sha256,
        page=page,
        bbox=bbox_norm,
        field_name=layout_field_name,
        extracted_quote=quote,
        extracted_by=extracted_by,
        extraction_confidence=confidence,
    )


def consensus(
    claims: list[Claim],
    *,
    min_citations: int = 2,
    require_third_party: bool = False,
) -> Optional[tuple[Any, list[Claim]]]:
    """Pick the canonical value for one (entity, attribute) from N claims.

    Returns (value, supporting_claims) or None if no consensus reaches
    min_citations citations and (optionally) third-party verification.
    """
    if not claims:
        return None
    by_value: dict[str, list[Claim]] = {}
    for c in claims:
        key = str(c.value)
        by_value.setdefault(key, []).append(c)

    # Sort buckets by total citation count + 3rd-party verified bonus
    def score(bucket: list[Claim]) -> tuple[int, int]:
        total_cits = sum(len(c.citations) for c in bucket)
        verified = sum(1 for c in bucket if c.verified_by_third_party)
        return (verified, total_cits)

    best_key = max(by_value, key=lambda k: score(by_value[k]))
    best_bucket = by_value[best_key]
    total_cits = sum(len(c.citations) for c in best_bucket)
    if total_cits < min_citations:
        return None
    if require_third_party and not any(c.verified_by_third_party for c in best_bucket):
        return None
    return best_bucket[0].value, best_bucket
