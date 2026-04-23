"""
THE VOLT — Entity Anagram.

User's principle (paraphrased):
    "Each company should have a vectorised anagram that links the entities."

An *anagram* here is the rearrangement of an entity's identifying tokens
into a stable text form that vectorises well — and a centroid embedding
of all the documents and related entities that point at it.

For a Company entity (e.g. "Klikk (Pty) Ltd") the anagram pulls together:

  • the canonical name + every alias spotted in filenames or extractions
    ("Klikk", "Klikk Pty Ltd", "KLIKK (PTY) LTD", "Klikk_Pty_Ltd")
  • the CIPC registration number
  • the VAT number
  • every Person silo that has a relationship pointing at it
    (DIRECTOR_OF, MEMBER_OF, BENEFICIAL_OWNER_OF, SHAREHOLDER_OF)
  • the addresses sourced from BENEFICIAL_OWNERSHIP_REGISTER /
    PROOF_OF_ADDRESS docs

It produces TWO artefacts:

  1. anagram_text     — a single deterministic string that captures the
                        entity's identity ("Klikk Pty Ltd | reg=2020/12345/07
                        | dirs=Dippenaar MC, Dippenaar M Snr | addr=…").
                        This is what gets vectorised.

  2. anagram_vector   — embedding of anagram_text + centroid of all
                        document-chunk embeddings tagged with this
                        entity_id. Stored in ChromaDB collection
                        `volt_entity_anagrams` with metadata
                        {entity_id, entity_type, vault_id, anagram_text}.

Lookups built on top:

  • `link_entities_via_anagram(anagram_a, anagram_b)` — cosine ≥ τ → likely
    same entity (used to dedup "Klikk" vs "KLIKK PTY LTD" silos).
  • `find_neighbours(anagram, k=10)` — surface entities likely to be
    related to this one (used by the gateway to suggest "you also have
    these related silos").
"""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Iterable, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class EntityAnagram:
    """Stable, vectorisable identity record for one entity."""
    entity_id: str
    entity_type: str                  # PERSONAL | COMPANY | TRUST | …
    vault_id: int

    canonical_name: str
    aliases: list[str] = field(default_factory=list)
    identifying_numbers: dict = field(default_factory=dict)
    # Examples: {"id_number": "8...", "registration_number": "2020/123/07",
    #            "vat_number": "4...", "trust_number": "IT5678/2020"}
    addresses: list[str] = field(default_factory=list)
    related_entity_ids: list[str] = field(default_factory=list)

    # Provenance: which docs contributed to this anagram
    sourced_from_doc_paths: list[str] = field(default_factory=list)

    # Outputs
    anagram_text: str = ""
    anagram_text_hash: str = ""       # sha256 of anagram_text — change-detection
    anagram_vector: Optional[list[float]] = None

    def render_text(self) -> str:
        """Build the deterministic text used for embedding.

        We sort aliases & related ids so two equivalent inputs produce
        BYTE-IDENTICAL anagram_text — that's how the change-detection hash
        catches genuine drift.
        """
        parts: list[str] = [
            f"type={self.entity_type}",
            f"name={self.canonical_name}",
        ]
        if self.aliases:
            uniq_aliases = sorted({a.strip() for a in self.aliases if a.strip()})
            parts.append("aliases=" + ", ".join(uniq_aliases))
        for k in sorted(self.identifying_numbers):
            v = self.identifying_numbers[k]
            if v:
                parts.append(f"{k}={v}")
        if self.addresses:
            uniq_addr = sorted({a.strip() for a in self.addresses if a.strip()})
            parts.append("addresses=" + " ; ".join(uniq_addr))
        if self.related_entity_ids:
            parts.append("related=" + ",".join(sorted(set(self.related_entity_ids))))
        return " | ".join(parts)

    def finalise(self) -> "EntityAnagram":
        """Recompute anagram_text and its hash from current fields."""
        self.anagram_text = self.render_text()
        self.anagram_text_hash = hashlib.sha256(
            self.anagram_text.encode("utf-8")
        ).hexdigest()
        return self


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def build_anagram(
    *,
    entity_id: str,
    entity_type: str,
    vault_id: int,
    canonical_name: str,
    claims: Iterable,                       # iterable of provenance.Claim
    related_entity_ids: Optional[list[str]] = None,
    extra_aliases: Optional[list[str]] = None,
) -> EntityAnagram:
    """Walk the entity's CONFIRMED Claims → assemble + finalise anagram."""
    cls = list(claims)
    aliases: set[str] = set(extra_aliases or [])
    numbers: dict[str, str] = {}
    addresses: set[str] = set()
    sourced_from: set[str] = set()

    # Each Claim has .attribute, .value, .citations
    for c in cls:
        attr = (c.attribute or "").lower()
        val = c.value
        if val is None:
            continue
        for cit in (c.citations or []):
            if getattr(cit, "document_path", None):
                sourced_from.add(cit.document_path)
        if attr in {"id_number", "registration_number", "vat_number",
                    "tax_number", "trust_number", "master_reference"}:
            numbers[attr] = str(val)
        elif attr in {"residential_address", "registered_address",
                      "business_address", "address"}:
            addresses.add(str(val))
        elif attr in {"trade_name", "registered_name", "trust_name",
                      "alias", "alternative_name"}:
            aliases.add(str(val))
        elif attr in {"surname", "given_names", "names"}:
            aliases.add(str(val))   # for PERSONAL: surname/names go in alias bag

    a = EntityAnagram(
        entity_id=entity_id,
        entity_type=entity_type,
        vault_id=vault_id,
        canonical_name=canonical_name,
        aliases=sorted(aliases),
        identifying_numbers=numbers,
        addresses=sorted(addresses),
        related_entity_ids=sorted(set(related_entity_ids or [])),
        sourced_from_doc_paths=sorted(sourced_from),
    )
    return a.finalise()


# ---------------------------------------------------------------------------
# Same-entity decision based on two anagrams
# ---------------------------------------------------------------------------

@dataclass
class AnagramLinkResult:
    same_entity: bool
    score: float                      # 0..1 — higher = more confident
    rationale: list[str] = field(default_factory=list)


def link_entities_via_anagram(
    a: EntityAnagram, b: EntityAnagram,
    *, name_threshold: float = 0.8, identifier_weight: float = 0.7,
) -> AnagramLinkResult:
    """Decide whether two anagrams describe the SAME real-world entity.

    Strategy (no embeddings required — runs deterministically):

      1. Identifying numbers are the king-pin: any ONE shared
         registration/id/vat number + same entity_type → 95% same.
      2. Otherwise: name+alias overlap (token-set ratio) decides.
    """
    rationale: list[str] = []

    if a.entity_type != b.entity_type:
        return AnagramLinkResult(same_entity=False, score=0.0,
                                 rationale=["entity_type mismatch"])

    # Rule 1 — shared identifier
    shared_keys = set(a.identifying_numbers) & set(b.identifying_numbers)
    for k in shared_keys:
        va = _norm_number(a.identifying_numbers[k])
        vb = _norm_number(b.identifying_numbers[k])
        if va and va == vb:
            rationale.append(f"shared {k}={va}")
            return AnagramLinkResult(same_entity=True,
                                     score=identifier_weight + 0.25,
                                     rationale=rationale)

    # Rule 2 — token overlap on name + aliases
    a_tokens = _tokenise(a.canonical_name) | _tokenise(" ".join(a.aliases))
    b_tokens = _tokenise(b.canonical_name) | _tokenise(" ".join(b.aliases))
    if not a_tokens or not b_tokens:
        return AnagramLinkResult(same_entity=False, score=0.0,
                                 rationale=["empty token sets"])
    inter = a_tokens & b_tokens
    union = a_tokens | b_tokens
    jaccard = len(inter) / len(union)
    rationale.append(f"jaccard_name={jaccard:.2f} (intersection={sorted(inter)})")
    return AnagramLinkResult(
        same_entity=jaccard >= name_threshold,
        score=jaccard,
        rationale=rationale,
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

_TOKEN_NOISE = {"PTY", "LTD", "LIMITED", "INC", "CC", "TRUST",
                "(PTY)", "(LTD)", "EDMS", "BPK", "THE", "AND", "&"}

def _tokenise(text: str) -> set[str]:
    if not text:
        return set()
    raw = re.split(r"[^A-Za-z0-9]+", text.upper())
    return {t for t in raw if t and t not in _TOKEN_NOISE and len(t) > 1}


def _norm_number(v: str) -> str:
    """Strip whitespace, slashes, spaces — for cross-format identifier matching."""
    return re.sub(r"[\s/-]", "", v or "").upper()
