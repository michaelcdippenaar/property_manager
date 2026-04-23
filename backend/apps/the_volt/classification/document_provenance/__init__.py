"""
THE VOLT — Document Provenance package.

Once a document has been classified, we want to PROVE it passed through
our system. That involves five concerns, each in its own module:

  fingerprint.py      → physical hash of the file (sha256 + size + ext +
                        page-count + perceptual hash for images)

  classification_number.py
                      → Volt Classification Number (VCN): a stable
                        human-readable, credit-card-style identifier
                        stamped on every classified doc

  stamp.py            → embed Volt metadata INTO the file (PDF XMP /
                        image EXIF / sidecar JSON for unsupported
                        types). Carries: VCN, fingerprint, submitter,
                        timestamp, HMAC signature

  duplicate_broker.py → fingerprint registry + dedup decisions
                        (DISCARD | MERGE | KEEP_BOTH | UPDATE_LATEST)

  submitter.py        → who submitted the file: user_id, IP, device,
                        ingestion-channel (email / web / mcp / api)

  entity_anagram.py   → per-entity vector signature ("anagram") that
                        links the entity to all of its documents and
                        to related entities

Together these turn an opaque pile of documents into a tamper-evident,
self-describing graph.
"""
from .fingerprint import (
    VoltFingerprint, compute_fingerprint, fingerprint_matches,
)
from .classification_number import (
    VoltClassificationNumber, mint_vcn, parse_vcn, format_vcn,
)
from .submitter import SubmitterContext
from .stamp import (
    VoltStamp, build_stamp, write_sidecar_stamp, embed_stamp_in_pdf_metadata,
)
from .duplicate_broker import (
    DuplicateBroker, DuplicateBrokerPolicy, DuplicateDecision,
    DuplicateMatch, DuplicateEvaluation,
    FingerprintRegistry, InMemoryFingerprintRegistry,
)
from .entity_anagram import (
    EntityAnagram, build_anagram, link_entities_via_anagram,
)
from .pipeline_hook import (
    ProvenanceRecord, attach_provenance,
    SequenceSupplier, VaultSecretLookup,
    make_in_memory_sequence_supplier, make_static_secret_lookup,
)

__all__ = [
    "VoltFingerprint", "compute_fingerprint", "fingerprint_matches",
    "VoltClassificationNumber", "mint_vcn", "parse_vcn", "format_vcn",
    "SubmitterContext",
    "VoltStamp", "build_stamp", "write_sidecar_stamp", "embed_stamp_in_pdf_metadata",
    "DuplicateBroker", "DuplicateBrokerPolicy", "DuplicateDecision",
    "DuplicateMatch", "DuplicateEvaluation",
    "FingerprintRegistry", "InMemoryFingerprintRegistry",
    "EntityAnagram", "build_anagram", "link_entities_via_anagram",
    "ProvenanceRecord", "attach_provenance",
    "SequenceSupplier", "VaultSecretLookup",
    "make_in_memory_sequence_supplier", "make_static_secret_lookup",
]
