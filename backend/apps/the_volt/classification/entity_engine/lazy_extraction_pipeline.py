"""
THE VOLT — Lazy / demand-driven extraction pipeline.

Principle (in the user's words):
    "If you have a map of a document like CIPRO, just vectorise the same
     area as last time. If you got everything you don't even need to pass
     tokens to LLM — query entity information table."

    "When N bank statements get uploaded, start training on bank
     statements. When a question gets asked and you don't know, only
     then go look it up."

    "Look at name of file" — filenames carry doc_type, person identity,
     certification flags, certification date, and language hints BEFORE
     any byte of the file is opened. That's Layer 0.

────────────────────────────────────────────────────────────────────────
Six-layer lookup (cheapest to most expensive)
────────────────────────────────────────────────────────────────────────

  Layer 0 — Filename Signal
      Cost: 0 tokens. Latency: microseconds (pure regex).
      Fired: every classification request, before anything else.
      Win: "Certified_ID_MC_Dippenaar_Jnr.pdf" yields
           {doc_type=SA_ID_CARD, certified=True, person="MC Dippenaar Jnr"}
           for free. Provisional Claims (cap conf=0.7) seed L1.

  Layer 1 — Entity Information Table (Claims DB)
      Cost: 0 tokens. Latency: ms.
      Fired: every external question first hits this.
      Win: "What is George's ID?" → already CONFIRMED → return + cite.

  Layer 2 — Doc Layout Map + Cached Bbox Crops
      Cost: 0 LLM tokens. Latency: tens of ms (image crop only).
      Fired: when a new doc of a KNOWN type arrives, or when Layer 1 missed
             but the source doc has been crop-extracted before.
      Win: another CoR14.3 arrives → run the existing layout, every
           bbox returns cached text, all fields filled deterministically.

  Layer 3 — Vision OCR per Field (Haiku, mapped layout)
      Cost: ~$0.002–$0.005 per document.
      Fired: doc type is known but layout cache misses (new variant,
             different version, hand-written values).
      Win: the SA Smart ID Card skill we just built.

  Layer 4 — Full LLM Extraction (Sonnet, 'read everything' fallback)
      Cost: ~$0.05–$0.30 per document.
      Fired: doc type is known but Layer 3 returns low confidence on the
             critical (root) attribute, OR doc type is novel (first
             encounter — no layout exists yet).

  Layer 5 — Auto-Train a New Skill (Opus, layout induction)
      Cost: $0.50–$5 once, then amortised.
      Fired: corpus_observer reports >= NEW_DOC_TYPE_THRESHOLD copies of
             a previously-unknown doc type. Opus inspects N samples,
             writes a new skill folder (layout.py + prompt.md + tools
             stub), runs the test battery against the samples.

────────────────────────────────────────────────────────────────────────
Demand-driven extraction
────────────────────────────────────────────────────────────────────────

We DO NOT pre-extract every field of every uploaded document. Only:

  • Root identity attributes are extracted on upload (ID number, reg
    number, etc. — this is the Identity-First doctrine).
  • All other fields are extracted lazily, when:
      - A slot_engine readiness check needs them
      - A user question references them
      - An autofill_proposal needs to populate a new form field
      - A consensus_extract run requests them across the corpus

This keeps token spend tied to actual value delivered.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Layer enum + per-layer routing
# ---------------------------------------------------------------------------

class Layer(str, Enum):
    L0_FILENAME_SIGNAL = "L0_filename_signal"
    L1_ENTITY_TABLE = "L1_entity_table"
    L2_LAYOUT_CACHE = "L2_layout_cache"
    L3_VISION_OCR = "L3_vision_ocr"
    L4_FULL_LLM = "L4_full_llm"
    L5_TRAIN_NEW = "L5_train_new"


@dataclass
class LookupRequest:
    """A demand: 'I need attribute X for entity Y, possibly from doc Z.'"""
    entity_id: str
    entity_type: str
    attribute: str
    doc_path: Optional[str] = None
    doc_type: Optional[str] = None
    doc_sha256: str = ""
    asker: str = ""        # who asked (slot_engine, autofill, user_query, consensus)
    min_confidence: float = 0.7


@dataclass
class LookupResult:
    value: Optional[Any]
    confidence: float
    layer_hit: Optional[Layer]
    citations: list[dict] = field(default_factory=list)
    cost_tokens: int = 0
    cost_usd: float = 0.0
    notes: str = ""


# ---------------------------------------------------------------------------
# Auto-train trigger
# ---------------------------------------------------------------------------

NEW_DOC_TYPE_THRESHOLD = 5     # see >= 5 copies of an unknown doc → mint a skill
ATTRIBUTE_RESCAN_THRESHOLD = 3 # an attribute newly missed 3 times → re-extract layer-by-layer


@dataclass
class CorpusObservation:
    """Per (doc_type, variant_signature) running counter the corpus_observer
    keeps in the Claims DB. When `unmapped_count >= NEW_DOC_TYPE_THRESHOLD`
    we trigger Layer 5."""
    doc_type: str                # "BANK_STATEMENT" or "UNKNOWN"
    variant_signature: str       # e.g. "FNB|2024-portrait" — fuzzy hash of layout features
    sample_paths: list[str] = field(default_factory=list)
    unmapped_count: int = 0
    has_skill: bool = False

    def needs_training(self) -> bool:
        return (not self.has_skill) and self.unmapped_count >= NEW_DOC_TYPE_THRESHOLD


# ---------------------------------------------------------------------------
# Pipeline (skeleton — concrete implementations live in the storage backend)
# ---------------------------------------------------------------------------

class LazyExtractionPipeline:
    """Each layer is a callable returning LookupResult or None.

    The concrete implementations are injected by the Volt storage layer:
      • layer0 → parses filename via filename_signals.extract_filename_signal
                 (default impl included — overridable for tests)
      • layer1 → reads from the Claims/Attribute table
      • layer2 → reads from the per-doc-type bbox crop cache
      • layer3 → invokes the right `skills/<doc_type>` extract()
      • layer4 → runs the Sonnet "read whole doc" extractor
      • layer5 → enqueues an Opus auto-train task (returns None synchronously)

    The pipeline doesn't know about the storage layer; it just chains.
    """

    def __init__(self, *, layer1, layer2, layer3, layer4, layer5, layer0=None):
        self.layer0 = layer0 or _default_layer0
        self.layer1 = layer1
        self.layer2 = layer2
        self.layer3 = layer3
        self.layer4 = layer4
        self.layer5 = layer5

    def lookup(self, req: LookupRequest) -> LookupResult:
        # L0 — free filename signal (only used when path supplied AND
        # the asked-for attribute is something the filename can supply)
        l0 = None
        if req.doc_path and req.attribute in _FILENAME_KNOWS:
            l0 = self.layer0(req)
            if l0 and l0.confidence >= req.min_confidence:
                l0.layer_hit = Layer.L0_FILENAME_SIGNAL
                return l0

        # L1 — already-confirmed Claim?
        r = self.layer1(req)
        if r and r.confidence >= req.min_confidence:
            r.layer_hit = Layer.L1_ENTITY_TABLE
            return r

        # No source doc supplied → can't go deeper
        if not req.doc_path:
            return r or l0 or LookupResult(value=None, confidence=0.0,
                                           layer_hit=None, notes="L1_miss_no_doc")

        # L2 — cached layout crop?
        r = self.layer2(req)
        if r and r.confidence >= req.min_confidence:
            r.layer_hit = Layer.L2_LAYOUT_CACHE
            return r

        # L3 — vision OCR via the per-doc-type skill
        r = self.layer3(req)
        if r and r.confidence >= req.min_confidence:
            r.layer_hit = Layer.L3_VISION_OCR
            return r

        # L4 — full Sonnet read
        r = self.layer4(req)
        if r and r.confidence >= req.min_confidence:
            r.layer_hit = Layer.L4_FULL_LLM
            return r

        # L5 — enqueue training run, return whatever we have
        # (prefer best non-None result we collected on the way down)
        self.layer5(req)
        return r or l0 or LookupResult(value=None, confidence=0.0,
                                       layer_hit=None, notes="all_layers_missed")


# ---------------------------------------------------------------------------
# L0 default implementation — wraps filename_signals
# ---------------------------------------------------------------------------

# Attributes the filename layer can reasonably supply. Other attributes
# (id_number, surname, address, etc.) require deeper layers; for those
# we skip L0 entirely so the pipeline doesn't pay even the regex cost.
_FILENAME_KNOWS = frozenset({
    "doc_type",
    "is_certified",
    "certification_date",
    "language_hint",
    "candidate_person",
    "candidate_counterparty",
    "candidate_reference_number",
})


def _default_layer0(req: LookupRequest) -> Optional[LookupResult]:
    """Parse the filename and return a provisional LookupResult."""
    if not req.doc_path:
        return None
    # Local import to keep the module importable even if filename_signals
    # is being evolved in parallel.
    from .filename_signals import extract_filename_signal
    sig = extract_filename_signal(req.doc_path)

    value: Any = None
    conf = 0.0
    notes_bits: list[str] = []

    if req.attribute == "doc_type":
        value, conf = sig.doc_type, sig.overall_confidence()
    elif req.attribute == "is_certified":
        value, conf = (True if sig.certified else None), (0.85 if sig.certified else 0.0)
    elif req.attribute == "certification_date":
        if sig.certification_date:
            value, conf = sig.certification_date.isoformat(), 0.8
    elif req.attribute == "language_hint":
        if sig.language_hint:
            value, conf = sig.language_hint, 0.7
    elif req.attribute == "candidate_person":
        if sig.persons:
            value = [p.normalised() for p in sig.persons]
            conf = max(p.confidence for p in sig.persons)
    elif req.attribute == "candidate_counterparty":
        if sig.counterparty:
            value, conf = sig.counterparty, 0.6
    elif req.attribute == "candidate_reference_number":
        if sig.ref_numbers:
            value, conf = sig.ref_numbers, 0.5

    if value is None:
        return None

    return LookupResult(
        value=value,
        confidence=conf,
        layer_hit=Layer.L0_FILENAME_SIGNAL,
        citations=[{
            "document_path": req.doc_path,
            "document_sha256": req.doc_sha256 or "",
            "page": None,
            "bbox": None,
            "field_name": "<filename>",
            "extracted_quote": sig.stem_clean,
            "extracted_by": "filename_signal@v1",
        }],
        cost_tokens=0,
        cost_usd=0.0,
        notes="; ".join(notes_bits),
    )


# ---------------------------------------------------------------------------
# Corpus observer trigger
# ---------------------------------------------------------------------------

def should_train_new_skill(obs: CorpusObservation) -> bool:
    """The exact rule for spawning a new skill — exposed for the scheduler."""
    return obs.needs_training()


def should_rescan_attribute(missed_count: int) -> bool:
    """If an attribute has been asked-and-missed N times, descend the
    layers again next time even if the previous result was cached."""
    return missed_count >= ATTRIBUTE_RESCAN_THRESHOLD
