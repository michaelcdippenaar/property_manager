"""
THE VOLT — Vectorisation rules.

Single source of truth for "what gets a vector and what doesn't".

────────────────────────────────────────────────────────────────────────
Rule 1 — Cross-Doc Frequency = Importance
────────────────────────────────────────────────────────────────────────
The user's principle, in their own words:

    "First just vectorise the entity details and tag. Address is
     important and ID, but not bank transactions for now. It is nowhere
     referenced. The more something occur in the data, the more
     important it is."

In code:  Attribute.vectorise = True  ⟺  attribute appears across
multiple documents about the same entity.

Examples (PERSONAL):
  ✓ id_number          — appears on every FICA, SARS, lease, contract
  ✓ residential_address — POA, FICA, banking, lease, utility bills
  ✓ surname / given_names
  ✓ phone, email, employer
  ✗ marital_status     — typically one form only
  ✗ occupation         — typically one form only

Bank statement noise:
  ✗ individual transaction lines    (single occurrence, no cross-ref)
  ✗ running balances                (single occurrence)
  ✓ account holder name              (cross-ref to FICA, lease, transfer)
  ✓ account number / branch          (cross-ref to debit-orders, leases)


────────────────────────────────────────────────────────────────────────
Rule 2 — NEVER vectorise raw identity images
────────────────────────────────────────────────────────────────────────
The Identity-First doctrine says the raw photo of an SA ID Card
(or passport, or driver's licence) is NEVER pushed into the vector
store. Reasons:
  • The ID number, photo, and signature are biometric-grade PII —
    the vector store has weaker access control than the encrypted
    file blob.
  • Vector similarity on raw card images is meaningless — a Smart
    ID Card looks like another Smart ID Card regardless of holder.
  • What IS searchable is the EXTRACTED VALUES: a Claim with
    id_number=8001015009087 + provenance, the surname text, the
    address string, etc.

So per identity document we vectorise:
  ✓ Each extracted Claim's value (via VoltDocumentChunk with
    metadata.field_name and metadata.entity_id)
  ✓ Small mapped crops (signature, photo) as separate chunks tagged
    image_kind="signature"/"photo" — for visual cross-doc matching
    (does the signature on doc A match the signature on doc B?)
  ✗ The full ID card image itself
  ✗ The full PDF page raster of a certified scan


────────────────────────────────────────────────────────────────────────
Rule 3 — Field-typed chunks beat raw text dumps
────────────────────────────────────────────────────────────────────────
For every extracted field we write a VoltDocumentChunk that contains
ONLY that field, with metadata identifying its type. Bigger chunks
mix unrelated facts and pull semantically irrelevant text into the
match window. So:

    chunk.text = "id_number: 8001015009087"
    chunk.metadata = {
        "owner_id": 1,
        "entity_id": 42,
        "field_name": "id_number",
        "doc_type": "SA_SMART_ID_CARD",
        "vector_weight": 1.5,
        "extracted_by": "skill:sa_smart_id_card@v1",
        "citation_id": "<uuid of Citation row>",
    }

Hybrid search by (query="George du Preez ID number") then becomes
both BM25-precise on the digit string AND semantically aware of the
"South African ID number" concept.
"""
from __future__ import annotations

from typing import Iterable

from .attributes import Attribute, attributes_for


# ---------------------------------------------------------------------------
# Whitelist / blacklist helpers
# ---------------------------------------------------------------------------

# Field names we explicitly REFUSE to vectorise, regardless of registry
NEVER_VECTORISE = frozenset({
    # Bank statement detail
    "transaction_line", "running_balance", "transaction_date",
    "transaction_amount", "transaction_description",
    # ID-document raw assets — only mapped crops with explicit image_kind go in
    "raw_id_image", "raw_id_pdf_page",
    # PII so sensitive that retrieval risk > value
    "biometric_template", "card_chip_data",
})


def should_vectorise(entity_type: str, attribute_name: str) -> bool:
    """Return True iff this (entity_type, attribute) is on the vectorise list."""
    if attribute_name in NEVER_VECTORISE:
        return False
    attrs = attributes_for(entity_type)
    a = attrs.get(attribute_name)
    return bool(a and a.vectorise)


def vectorisable_attributes(entity_type: str) -> list[Attribute]:
    """List of Attributes for this EntityType that the registry says to vectorise."""
    return [a for a in attributes_for(entity_type).values()
            if a.vectorise and a.name not in NEVER_VECTORISE]


def chunk_metadata_for(
    *,
    entity_type: str,
    attribute_name: str,
    owner_id: int,
    entity_id: int,
    doc_type: str,
    citation_id: str,
    extracted_by: str,
) -> dict:
    """Standardised metadata block for a per-attribute VoltDocumentChunk."""
    attrs = attributes_for(entity_type)
    a = attrs.get(attribute_name)
    weight = a.vector_weight if a else 1.0
    return {
        "owner_id": int(owner_id),
        "entity_id": int(entity_id),
        "entity_type": entity_type,
        "field_name": attribute_name,
        "doc_type": doc_type,
        "vector_weight": weight,
        "extracted_by": extracted_by,
        "citation_id": citation_id,
        "is_identity_attr": bool(a and a.is_identity),
        "is_root_attr": bool(a and a.is_root),
    }


def render_field_chunk(attribute_name: str, value: str) -> str:
    """The text body that gets embedded for a field-typed chunk.
    Format chosen so BM25 + dense both pick it up cleanly."""
    return f"{attribute_name}: {value}"


# ---------------------------------------------------------------------------
# Frequency-aware re-evaluation
# ---------------------------------------------------------------------------

def occurs_across_n_documents(
    attribute_name: str,
    claims: Iterable,
) -> int:
    """How many distinct documents (by sha256) cite this attribute?
    Use this to validate the "high frequency = vectorise" rule on real data:
    if a supposedly-vectorisable attribute occurs in ≤1 doc, it's noise."""
    seen = set()
    for cl in claims:
        if getattr(cl, "attribute", None) != attribute_name:
            continue
        for c in getattr(cl, "citations", []) or []:
            if c.document_sha256:
                seen.add(c.document_sha256)
    return len(seen)


def recommend_vectorise_flag(
    attribute_name: str,
    claims: Iterable,
    *,
    threshold: int = 2,
) -> bool:
    """Frequency-based recommendation, independent of the registry default.
    True if this attribute appears across `threshold` or more distinct documents
    in the supplied Claim history."""
    return occurs_across_n_documents(attribute_name, claims) >= threshold
