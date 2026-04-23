"""
Shared dataclasses used by every skill.

Keeping these in one place means the orchestrator, every skill, and
downstream Volt code all speak the same vocabulary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Layout primitives (each skill defines its own LAYOUT instance)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IDField:
    name: str
    bbox: tuple[float, float, float, float]   # x, y, w, h in [0, 1]
    field_type: str
    required: bool = True
    hint: str = ""


@dataclass
class IDLayout:
    name: str
    doc_type: str
    aspect_ratio: float
    aspect_tolerance: float
    side: str = "front"
    fields: list[IDField] = field(default_factory=list)
    anchors: list[str] = field(default_factory=list)
    notes: str = ""

    def field_by_name(self, name: str) -> Optional[IDField]:
        return next((f for f in self.fields if f.name == name), None)


# ---------------------------------------------------------------------------
# Extraction result envelope (what every skill returns)
# ---------------------------------------------------------------------------

@dataclass
class FieldResult:
    name: str
    value: Optional[str]
    confidence: float
    raw: Optional[str] = None         # raw OCR before normalisation
    field_type: str = ""
    error: Optional[str] = None       # validator or OCR error, if any


@dataclass
class ExtractionResult:
    doc_type: str                     # e.g. SA_SMART_ID_CARD
    layout_name: str                  # e.g. "SA Smart ID Card 2013+ (front)"
    layout_score: float               # confidence of layout detection
    fields: dict[str, FieldResult] = field(default_factory=dict)
    crops: dict[str, str] = field(default_factory=dict)   # field_name → crop file path
    overall_confidence: float = 0.0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def primary_identifier(self) -> Optional[str]:
        """Return the canonical identity number for this doc, if extracted."""
        for key in ("id_number", "child_id_number", "passport_no", "licence_number"):
            f = self.fields.get(key)
            if f and f.value:
                return f.value
        return None
