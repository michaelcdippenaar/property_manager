"""
Slot engine — the bridge between Claims (what we KNOW) and Required Docs
(what we NEED) for a given purpose (FICA / TRANSFER / KYC).

Two questions answered:

  1. Readiness:
       "Is George ready to be a trustee in the LucaNaude transfer?"
       → report({filled, empty, expired, mismatched})

  2. Autofill:
       "A new FICA Questionnaire form arrived for George. Which slots
        can we pre-fill from his already-confirmed entity attributes?"
       → list[AutofillProposal] with PROVENANCE (which prior doc each
         pre-fill came from).

Every fact in / out carries Citations — no slot is reported as filled
unless we can point to the exact document and field that fills it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Iterable, Optional

from .attributes import (
    Attribute, attributes_for, attributes_filled_by,
)
from .required_docs import DocSlot, slots_for, REQUIRED, RECOMMENDED, OPTIONAL


# ---------------------------------------------------------------------------
# Reporting dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SlotStatus:
    slot: DocSlot
    state: str               # FILLED | EMPTY | EXPIRED | MISMATCHED
    filling_doc_paths: list[str] = field(default_factory=list)
    filling_doc_shas: list[str] = field(default_factory=list)
    age_days: Optional[int] = None
    expires_in_days: Optional[int] = None
    mismatch_note: Optional[str] = None


@dataclass
class ReadinessReport:
    entity_id: str
    entity_type: str
    purpose: str
    slots: list[SlotStatus] = field(default_factory=list)
    overall_ready: bool = False
    blocking: list[str] = field(default_factory=list)   # doc_types that still must be filled

    def required_filled_count(self) -> int:
        return sum(1 for s in self.slots
                   if s.state == "FILLED" and s.slot.status == REQUIRED)

    def required_total(self) -> int:
        return sum(1 for s in self.slots if s.slot.status == REQUIRED)


@dataclass
class AutofillProposal:
    target_field: str             # e.g. "id_number_field" on the new form's template
    attribute_name: str           # the entity attribute supplying the value
    value: str
    confidence: float
    sourced_from_doc_paths: list[str]    # provenance: where the value originally came from
    third_party_verified: bool


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _doc_age_days(uploaded_at: datetime) -> int:
    return (datetime.utcnow() - uploaded_at).days


def _claim_value(claims, attribute: str):
    """Pick the canonical claim value for an attribute (CONFIRMED > PROPOSED)."""
    candidates = [c for c in claims if c.attribute == attribute]
    if not candidates:
        return None, None
    candidates.sort(key=lambda c: (c.status != "CONFIRMED",   # CONFIRMED first
                                   -c.confidence,
                                   -len(c.citations)))
    top = candidates[0]
    return top.value, top


# ---------------------------------------------------------------------------
# Readiness
# ---------------------------------------------------------------------------

def evaluate_readiness(
    *,
    entity_id: str,
    entity_type: str,
    purpose: str,
    documents,                # iterable of (doc_type, path, sha256, uploaded_at)
    claims,                   # iterable of Claim
) -> ReadinessReport:
    """Walk the slot map for (entity_type, purpose) and report status.

    `documents` is whatever the caller already has on record about which
    docs the entity has uploaded — at minimum the doc_type+timestamp.
    Claim mismatches (e.g. ID number on doc A != ID number on doc B)
    are detected via `claims`."""
    docs = list(documents)
    cls = list(claims)
    slots = slots_for(entity_type, purpose)
    rpt = ReadinessReport(entity_id=entity_id, entity_type=entity_type, purpose=purpose)

    for slot in slots:
        accepted_types = {slot.doc_type, *slot.alternatives}
        matching = [(t, p, sha, when) for (t, p, sha, when) in docs if t in accepted_types]
        if not matching:
            rpt.slots.append(SlotStatus(slot=slot, state="EMPTY"))
            if slot.status == REQUIRED:
                rpt.blocking.append(slot.doc_type)
            continue

        # Pick the freshest
        matching.sort(key=lambda x: x[3], reverse=True)
        t, p, sha, when = matching[0]
        age = _doc_age_days(when)

        if slot.max_age_days is not None and age > slot.max_age_days:
            rpt.slots.append(SlotStatus(
                slot=slot, state="EXPIRED",
                filling_doc_paths=[p], filling_doc_shas=[sha],
                age_days=age,
                expires_in_days=slot.max_age_days - age,
            ))
            if slot.status == REQUIRED:
                rpt.blocking.append(slot.doc_type)
            continue

        # Mismatch check: if this doc-type fills attributes that already
        # have CONFIRMED claims with different values → MISMATCHED
        mismatch_note = None
        for attr_name in attributes_filled_by(entity_type, t):
            confirmed_value, confirmed_claim = _claim_value(cls, attr_name)
            if not confirmed_claim or confirmed_claim.status != "CONFIRMED":
                continue
            # Find any citation from this exact doc on this attribute
            for cl in cls:
                if cl.attribute != attr_name:
                    continue
                if any(c.document_sha256 == sha for c in cl.citations):
                    if str(cl.value) != str(confirmed_value):
                        mismatch_note = (
                            f"{attr_name}: doc={cl.value!r} vs confirmed={confirmed_value!r}"
                        )
                        break
            if mismatch_note:
                break

        if mismatch_note:
            rpt.slots.append(SlotStatus(
                slot=slot, state="MISMATCHED",
                filling_doc_paths=[p], filling_doc_shas=[sha],
                age_days=age, mismatch_note=mismatch_note,
            ))
            if slot.status == REQUIRED:
                rpt.blocking.append(slot.doc_type)
        else:
            rpt.slots.append(SlotStatus(
                slot=slot, state="FILLED",
                filling_doc_paths=[p], filling_doc_shas=[sha],
                age_days=age,
                expires_in_days=(slot.max_age_days - age) if slot.max_age_days else None,
            ))

    rpt.overall_ready = (rpt.required_filled_count() == rpt.required_total())
    return rpt


# ---------------------------------------------------------------------------
# Autofill
# ---------------------------------------------------------------------------

def propose_autofill(
    *,
    entity_type: str,
    incoming_doc_type: str,
    blank_form_fields: Iterable[str],
    claims,
) -> list[AutofillProposal]:
    """For each blank field on a new form, propose the entity-attribute value.

    `blank_form_fields` is the list of field-names the form template
    declared as user-fillable (e.g. id_number_field, residential_address_field).
    Naming convention: form fields end in '_field' and the bit before is
    the canonical attribute name from `attributes.py`.
    """
    cls = list(claims)
    proposals: list[AutofillProposal] = []
    available_attrs = attributes_for(entity_type)

    for form_field in blank_form_fields:
        attr_name = form_field.removesuffix("_field")
        attr = available_attrs.get(attr_name)
        if not attr:
            continue
        value, claim = _claim_value(cls, attr_name)
        if value is None:
            continue
        sources = sorted({c.document_path for c in claim.citations if c.document_path})
        proposals.append(AutofillProposal(
            target_field=form_field,
            attribute_name=attr_name,
            value=str(value),
            confidence=claim.confidence,
            sourced_from_doc_paths=sources,
            third_party_verified=claim.verified_by_third_party,
        ))
    return proposals


# ---------------------------------------------------------------------------
# Pretty-printer (for debug/CLI use)
# ---------------------------------------------------------------------------

def render_report(rpt: ReadinessReport) -> str:
    lines = [
        f"\n{'='*72}",
        f"Readiness: {rpt.entity_type}/{rpt.entity_id} for {rpt.purpose}",
        f"{'='*72}",
        f"  filled={rpt.required_filled_count()}/{rpt.required_total()} required slots",
        f"  ready={'YES' if rpt.overall_ready else 'NO'}",
    ]
    if rpt.blocking:
        lines.append(f"  blocking: {', '.join(rpt.blocking)}")
    lines.append("")
    for s in rpt.slots:
        marker = {"FILLED": "✓", "EMPTY": "·", "EXPIRED": "!", "MISMATCHED": "✗"}.get(s.state, "?")
        req = {"REQUIRED": "[REQ]", "RECOMMENDED": "[REC]", "OPTIONAL": "[opt]"}[s.slot.status]
        line = f"  {marker} {req} {s.slot.doc_type:<28} {s.state}"
        if s.age_days is not None:
            line += f"  age={s.age_days}d"
        if s.mismatch_note:
            line += f"  ! {s.mismatch_note}"
        lines.append(line)
    return "\n".join(lines)
