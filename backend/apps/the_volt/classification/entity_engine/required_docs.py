"""
Required-document slot maps per (EntityType, Purpose).

Different downstream uses need different document packs:
  • FICA          — bank/conveyancer verification of identity + address
  • TRANSFER      — full property-transfer pack (FICA + tax + bond)
  • CIPC_MANDATE  — appointment to act on behalf of a company
  • TRUST_MANDATE — appointment to act on behalf of a trust
  • ONBOARDING    — minimum needed to create a NaturalPersonSilo / EntitySilo

Each slot has:
  doc_type     — exact match against the classifier's output
  status       — REQUIRED | RECOMMENDED | OPTIONAL
  max_age_days — None for never-expires, else days
  notes        — human explanation
  alternatives — list of other doc_types that satisfy the same slot
                 (e.g. SA_PASSPORT can substitute for SA_SMART_ID_CARD)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .attributes import (
    PERSONAL, TRUST, COMPANY, CLOSE_CORPORATION, SOLE_PROPRIETARY, ASSET,
    SA_SMART_ID_CARD, SA_GREEN_ID_BOOK, SA_PASSPORT, SA_DRIVERS_LICENCE,
    SA_BIRTH_CERT_UNABRIDGED,
    PROOF_OF_ADDRESS, BANK_CONFIRMATION, SARS_NOR, SARS_VAT_NOR,
    FICA_QUEST_NATPERSON, FICA_QUEST_COMPANY, POPI_CONSENT,
    COR14_3, COR14_1, COR14_1A, COR15_1A, SHARE_CERTIFICATE,
    RES_INCORP, RES_AUTH_SIGN, RES_SHARE_TRANSFER,
    LETTERS_OF_AUTHORITY, TRUST_DEED,
    TITLE_DEED, INSURANCE_POLICY, VEHICLE_REG,
)


REQUIRED = "REQUIRED"
RECOMMENDED = "RECOMMENDED"
OPTIONAL = "OPTIONAL"


@dataclass
class DocSlot:
    doc_type: str
    status: str = REQUIRED
    max_age_days: Optional[int] = None
    notes: str = ""
    alternatives: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Purpose registry
# ---------------------------------------------------------------------------

# (entity_type, purpose) -> list[DocSlot]
SLOTS: dict[tuple[str, str], list[DocSlot]] = {

    # ── PERSONAL ─────────────────────────────────────────────────────────
    (PERSONAL, "ONBOARDING"): [
        DocSlot(SA_SMART_ID_CARD, REQUIRED,
                notes="Root identity. SA Smart ID Card preferred.",
                alternatives=[SA_GREEN_ID_BOOK, SA_PASSPORT, SA_BIRTH_CERT_UNABRIDGED]),
    ],
    (PERSONAL, "FICA"): [
        DocSlot(SA_SMART_ID_CARD, REQUIRED,
                notes="Photo + 13-digit ID, Luhn-validated.",
                alternatives=[SA_GREEN_ID_BOOK, SA_PASSPORT]),
        DocSlot(PROOF_OF_ADDRESS, REQUIRED, max_age_days=90,
                notes="Utility bill / bank statement / municipal account, < 3 months."),
        DocSlot(SARS_NOR, RECOMMENDED,
                notes="Tax registration confirms tax_number."),
        DocSlot(BANK_CONFIRMATION, OPTIONAL,
                notes="Confirms banking details for refunds."),
    ],
    (PERSONAL, "TRANSFER_BUYER"): [
        DocSlot(SA_SMART_ID_CARD, REQUIRED, alternatives=[SA_GREEN_ID_BOOK, SA_PASSPORT]),
        DocSlot(PROOF_OF_ADDRESS, REQUIRED, max_age_days=90),
        DocSlot(SARS_NOR, REQUIRED, notes="Required for transfer duty calculation."),
        DocSlot(BANK_CONFIRMATION, REQUIRED, notes="For deposit refund + bond."),
        DocSlot(FICA_QUEST_NATPERSON, REQUIRED, max_age_days=180),
        DocSlot(POPI_CONSENT, REQUIRED, notes="Conveyancer's POPI consent form."),
    ],
    (PERSONAL, "DIRECTOR_APPOINTMENT"): [
        DocSlot(SA_SMART_ID_CARD, REQUIRED, alternatives=[SA_GREEN_ID_BOOK, SA_PASSPORT]),
        DocSlot(PROOF_OF_ADDRESS, REQUIRED, max_age_days=90),
        DocSlot(SARS_NOR, REQUIRED),
    ],
    (PERSONAL, "TRUSTEE_APPOINTMENT"): [
        DocSlot(SA_SMART_ID_CARD, REQUIRED, alternatives=[SA_GREEN_ID_BOOK, SA_PASSPORT]),
        DocSlot(PROOF_OF_ADDRESS, REQUIRED, max_age_days=90),
        DocSlot(SARS_NOR, REQUIRED),
        DocSlot(FICA_QUEST_NATPERSON, REQUIRED, max_age_days=365,
                notes="Independent trustee FICA form."),
    ],

    # ── COMPANY ─────────────────────────────────────────────────────────
    (COMPANY, "ONBOARDING"): [
        DocSlot(COR14_3, REQUIRED, notes="Registration certificate."),
    ],
    (COMPANY, "FICA"): [
        DocSlot(COR14_3, REQUIRED),
        DocSlot(COR14_1A, REQUIRED, notes="Initial directors / shareholders."),
        DocSlot(COR15_1A, RECOMMENDED, notes="MOI."),
        DocSlot(SARS_NOR, REQUIRED),
        DocSlot(SARS_VAT_NOR, OPTIONAL, notes="If VAT vendor."),
        DocSlot(PROOF_OF_ADDRESS, REQUIRED, max_age_days=90,
                notes="Of registered address."),
        DocSlot(BANK_CONFIRMATION, REQUIRED),
        DocSlot(FICA_QUEST_COMPANY, REQUIRED, max_age_days=180),
    ],
    (COMPANY, "TRANSFER_BUYER"): [
        DocSlot(COR14_3, REQUIRED),
        DocSlot(COR14_1A, REQUIRED),
        DocSlot(SARS_NOR, REQUIRED),
        DocSlot(SARS_VAT_NOR, OPTIONAL),
        DocSlot(BANK_CONFIRMATION, REQUIRED),
        DocSlot(RES_AUTH_SIGN, REQUIRED,
                notes="Resolution authorising the signatory for the transfer."),
        DocSlot(FICA_QUEST_COMPANY, REQUIRED, max_age_days=180),
        DocSlot(POPI_CONSENT, REQUIRED),
    ],

    # ── CLOSE_CORPORATION ───────────────────────────────────────────────
    (CLOSE_CORPORATION, "ONBOARDING"): [
        DocSlot(COR14_3, REQUIRED),
    ],
    (CLOSE_CORPORATION, "FICA"): [
        DocSlot(COR14_3, REQUIRED),
        DocSlot(SARS_NOR, REQUIRED),
        DocSlot(PROOF_OF_ADDRESS, REQUIRED, max_age_days=90),
        DocSlot(BANK_CONFIRMATION, REQUIRED),
    ],

    # ── TRUST ───────────────────────────────────────────────────────────
    (TRUST, "ONBOARDING"): [
        DocSlot(LETTERS_OF_AUTHORITY, REQUIRED,
                notes="Issued by the Master of the High Court."),
    ],
    (TRUST, "FICA"): [
        DocSlot(LETTERS_OF_AUTHORITY, REQUIRED),
        DocSlot(TRUST_DEED, REQUIRED),
        DocSlot(SARS_NOR, REQUIRED),
        DocSlot(BANK_CONFIRMATION, REQUIRED),
        DocSlot(FICA_QUEST_COMPANY, REQUIRED, max_age_days=180,
                notes="Trusts use the company FICA template."),
    ],
    (TRUST, "TRANSFER_BUYER"): [
        DocSlot(LETTERS_OF_AUTHORITY, REQUIRED),
        DocSlot(TRUST_DEED, REQUIRED),
        DocSlot(SARS_NOR, REQUIRED),
        DocSlot(BANK_CONFIRMATION, REQUIRED),
        DocSlot(RES_AUTH_SIGN, REQUIRED,
                notes="Trustees' resolution to purchase the property."),
        DocSlot(FICA_QUEST_COMPANY, REQUIRED, max_age_days=180),
    ],

    # ── SOLE_PROPRIETARY ────────────────────────────────────────────────
    (SOLE_PROPRIETARY, "ONBOARDING"): [
        DocSlot(SA_SMART_ID_CARD, REQUIRED, alternatives=[SA_GREEN_ID_BOOK]),
    ],
    (SOLE_PROPRIETARY, "FICA"): [
        DocSlot(SA_SMART_ID_CARD, REQUIRED, alternatives=[SA_GREEN_ID_BOOK]),
        DocSlot(PROOF_OF_ADDRESS, REQUIRED, max_age_days=90),
        DocSlot(SARS_NOR, REQUIRED),
        DocSlot(BANK_CONFIRMATION, REQUIRED),
    ],

    # ── ASSET (PROPERTY / VEHICLE) ──────────────────────────────────────
    (ASSET, "TRANSFER"): [
        DocSlot(TITLE_DEED, REQUIRED),
        DocSlot(INSURANCE_POLICY, RECOMMENDED),
    ],
}


def slots_for(entity_type: str, purpose: str) -> list[DocSlot]:
    return SLOTS.get((entity_type, purpose), [])


def all_purposes_for(entity_type: str) -> list[str]:
    return sorted({pur for (et, pur) in SLOTS if et == entity_type})
