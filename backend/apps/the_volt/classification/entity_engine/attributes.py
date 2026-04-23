"""
Canonical attribute registry for every EntityType.

Each Attribute knows:
  - data_type           (str | digits | date | address | phone | email | money …)
  - is_identity         (true if a verifier service can confirm it — ID#, tax#)
  - root                (true if the entity cannot exist without it — e.g. id_number for PERSONAL)
  - validators          (callable list, returns list[str] of errors)
  - sourceable_from     (which document_types can supply this attribute)
  - autofill_priority   (higher = use this attribute first when prefilling forms)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


# ---------------------------------------------------------------------------
# EntityType vocabulary (mirrors apps.the_volt.entities.models.EntityType)
# ---------------------------------------------------------------------------

PERSONAL = "PERSONAL"
TRUST = "TRUST"
COMPANY = "COMPANY"
CLOSE_CORPORATION = "CLOSE_CORPORATION"
SOLE_PROPRIETARY = "SOLE_PROPRIETARY"
ASSET = "ASSET"

ALL_ENTITY_TYPES = (PERSONAL, TRUST, COMPANY, CLOSE_CORPORATION, SOLE_PROPRIETARY, ASSET)


# ---------------------------------------------------------------------------
# DocumentType vocabulary (mirrors apps.the_volt.documents.models.DocumentType
# plus the granular sub-types used by the classification skills)
# ---------------------------------------------------------------------------

# Identity-class
SA_SMART_ID_CARD = "SA_SMART_ID_CARD"
SA_GREEN_ID_BOOK = "SA_GREEN_ID_BOOK"
SA_PASSPORT = "SA_PASSPORT"
SA_DRIVERS_LICENCE = "SA_DRIVERS_LICENCE"
SA_BIRTH_CERT_UNABRIDGED = "SA_BIRTH_CERT_UNABRIDGED"

# FICA-class
PROOF_OF_ADDRESS = "PROOF_OF_ADDRESS"
BANK_CONFIRMATION = "BANK_CONFIRMATION"
SARS_NOR = "SARS_NOR"             # Notice of Registration (tax)
SARS_VAT_NOR = "SARS_VAT_NOR"
FICA_QUEST_NATPERSON = "FICA_QUEST_NATPERSON"
FICA_QUEST_COMPANY = "FICA_QUEST_COMPANY"
POPI_CONSENT = "POPI_CONSENT"

# CIPC-class
COR14_3 = "COR14_3"
COR14_1 = "COR14_1"
COR14_1A = "COR14_1A"
COR15_1A = "COR15_1A"
SHARE_CERTIFICATE = "SHARE_CERTIFICATE"
RES_INCORP = "RES_INCORP"
RES_AUTH_SIGN = "RES_AUTH_SIGN"
RES_SHARE_TRANSFER = "RES_SHARE_TRANSFER"

# Trust-class
LETTERS_OF_AUTHORITY = "LETTERS_OF_AUTHORITY"
TRUST_DEED = "TRUST_DEED"

# Asset-class
TITLE_DEED = "TITLE_DEED"
INSURANCE_POLICY = "INSURANCE_POLICY"
VEHICLE_REG = "VEHICLE_REG"


# ---------------------------------------------------------------------------
# Attribute dataclass
# ---------------------------------------------------------------------------

@dataclass
class Attribute:
    name: str
    data_type: str                         # digits | name | date | address | phone | email | text | money | iso_country | list
    label: str = ""
    is_identity: bool = False
    is_root: bool = False                  # entity cannot exist without it
    sourceable_from: list[str] = field(default_factory=list)
    autofill_priority: int = 50
    third_party_verifier: Optional[str] = None   # e.g. "DHA_HANIS", "CIPC_LIVE", "SARS_eFiling"
    description: str = ""

    # ─── Vectorisation policy (Cross-Doc Frequency rule) ────────────────
    #   vectorise=True  → write a VoltDocumentChunk per occurrence so the
    #                     attribute is searchable across the corpus.
    #   vectorise=False → store only as a structured Claim, never embedded.
    #   The rule of thumb: an attribute that occurs across MANY documents
    #   (id_number, address, surname, registered_name) is worth indexing.
    #   An attribute that lives on ONE document only (bank balance,
    #   transaction line, single-meter reading) is NOT — it has no
    #   cross-doc references that would make a vector search useful, and
    #   each one would just add noise to the index.
    vectorise: bool = False
    vector_weight: float = 1.0             # multiplied into hybrid score


# ---------------------------------------------------------------------------
# Per-EntityType attribute maps
# ---------------------------------------------------------------------------

PERSONAL_ATTRIBUTES: dict[str, Attribute] = {a.name: a for a in [
    Attribute("id_number", "digits",
              label="South African ID number",
              is_identity=True, is_root=True,
              sourceable_from=[SA_SMART_ID_CARD, SA_GREEN_ID_BOOK, SA_PASSPORT,
                               SA_DRIVERS_LICENCE, SA_BIRTH_CERT_UNABRIDGED,
                               FICA_QUEST_NATPERSON, SARS_NOR],
              autofill_priority=100, third_party_verifier="DHA_HANIS",
              vectorise=True, vector_weight=1.5,
              description="13-digit SA ID. Luhn-validated. Decoded into DOB+sex+citizenship. Highest cross-doc frequency."),
    Attribute("passport_number", "text",
              label="Passport number",
              is_identity=True,
              sourceable_from=[SA_PASSPORT],
              autofill_priority=80,
              vectorise=True, vector_weight=1.2),
    Attribute("surname", "name",
              sourceable_from=[SA_SMART_ID_CARD, SA_GREEN_ID_BOOK, SA_PASSPORT,
                               SA_DRIVERS_LICENCE, FICA_QUEST_NATPERSON],
              autofill_priority=90,
              vectorise=True, vector_weight=1.3),
    Attribute("given_names", "name",
              sourceable_from=[SA_SMART_ID_CARD, SA_GREEN_ID_BOOK, SA_PASSPORT,
                               SA_DRIVERS_LICENCE, FICA_QUEST_NATPERSON],
              autofill_priority=90,
              vectorise=True, vector_weight=1.2),
    Attribute("date_of_birth", "date",
              sourceable_from=[SA_SMART_ID_CARD, SA_GREEN_ID_BOOK, SA_PASSPORT,
                               SA_DRIVERS_LICENCE, SA_BIRTH_CERT_UNABRIDGED],
              autofill_priority=85,
              vectorise=False,    # derivable from id_number, no cross-ref value alone
              description="Cross-checked against first 6 digits of id_number."),
    Attribute("sex", "text",
              sourceable_from=[SA_SMART_ID_CARD, SA_GREEN_ID_BOOK, SA_PASSPORT,
                               SA_BIRTH_CERT_UNABRIDGED],
              autofill_priority=80,
              vectorise=False),    # derivable from id_number
    Attribute("nationality", "iso_country",
              sourceable_from=[SA_SMART_ID_CARD, SA_PASSPORT],
              autofill_priority=70, vectorise=False),
    Attribute("residential_address", "address",
              sourceable_from=[PROOF_OF_ADDRESS, FICA_QUEST_NATPERSON,
                               BANK_CONFIRMATION],
              autofill_priority=85,
              vectorise=True, vector_weight=1.4,
              description="HIGH cross-doc value — same address appears on POA, FICA form, banking confirm, lease, etc. Must be < 3 months old for FICA."),
    Attribute("phone", "phone",
              sourceable_from=[FICA_QUEST_NATPERSON],
              autofill_priority=60,
              vectorise=True, vector_weight=0.8),
    Attribute("email", "email",
              sourceable_from=[FICA_QUEST_NATPERSON],
              autofill_priority=60,
              vectorise=True, vector_weight=0.8),
    Attribute("tax_number", "digits",
              is_identity=True,
              sourceable_from=[SARS_NOR, FICA_QUEST_NATPERSON],
              autofill_priority=75, third_party_verifier="SARS_eFiling",
              vectorise=True, vector_weight=1.2),
    Attribute("bank_account", "text",
              sourceable_from=[BANK_CONFIRMATION],
              autofill_priority=70,
              vectorise=True, vector_weight=0.9,
              description="Account number is referenced across leases, debit-orders, transfer files."),
    Attribute("marital_status", "text",
              sourceable_from=[FICA_QUEST_NATPERSON],
              autofill_priority=40, vectorise=False),
    Attribute("occupation", "text",
              sourceable_from=[FICA_QUEST_NATPERSON],
              autofill_priority=40, vectorise=False),
    Attribute("employer", "text",
              sourceable_from=[FICA_QUEST_NATPERSON],
              autofill_priority=40,
              vectorise=True, vector_weight=0.7,
              description="Employer name often appears on payslip + FICA + lease application — worth indexing."),
]}


COMPANY_ATTRIBUTES: dict[str, Attribute] = {a.name: a for a in [
    Attribute("registration_number", "text",
              label="CIPC registration number",
              is_identity=True, is_root=True,
              sourceable_from=[COR14_3, COR14_1, COR14_1A, COR15_1A,
                               SARS_NOR, FICA_QUEST_COMPANY],
              autofill_priority=100, third_party_verifier="CIPC_LIVE",
              vectorise=True, vector_weight=1.5,
              description="Format YYYY/NNNNNN/NN. Highest cross-doc frequency for any company."),
    Attribute("registered_name", "name",
              sourceable_from=[COR14_3, COR15_1A, SARS_NOR],
              autofill_priority=95,
              vectorise=True, vector_weight=1.4),
    Attribute("trading_name", "name",
              sourceable_from=[COR14_3, FICA_QUEST_COMPANY],
              autofill_priority=70,
              vectorise=True, vector_weight=1.0),
    Attribute("date_of_incorporation", "date",
              sourceable_from=[COR14_3], autofill_priority=80,
              vectorise=False),    # appears on CoR14.3 only
    Attribute("registered_address", "address",
              sourceable_from=[COR14_3, COR15_1A, FICA_QUEST_COMPANY],
              autofill_priority=85,
              vectorise=True, vector_weight=1.3),
    Attribute("tax_number", "digits",
              is_identity=True, sourceable_from=[SARS_NOR],
              autofill_priority=80, third_party_verifier="SARS_eFiling",
              vectorise=True, vector_weight=1.2),
    Attribute("vat_number", "digits",
              is_identity=True, sourceable_from=[SARS_VAT_NOR],
              autofill_priority=70, third_party_verifier="SARS_eFiling",
              vectorise=True, vector_weight=1.1),
    Attribute("financial_year_end", "date",
              sourceable_from=[COR14_3], autofill_priority=50,
              vectorise=False),
    Attribute("directors", "list",
              sourceable_from=[COR14_1A, RES_AUTH_SIGN, FICA_QUEST_COMPANY],
              autofill_priority=85,
              vectorise=True, vector_weight=1.3,
              description="Each entry: {entity_id, role, effective_date}. Director names + IDs are referenced across many docs."),
    Attribute("shareholders", "list",
              sourceable_from=[COR14_1A, SHARE_CERTIFICATE, RES_SHARE_TRANSFER],
              autofill_priority=80,
              vectorise=True, vector_weight=1.2),
]}


TRUST_ATTRIBUTES: dict[str, Attribute] = {a.name: a for a in [
    Attribute("trust_number", "text",
              label="Master's reference (e.g. IT 1234/2019)",
              is_identity=True, is_root=True,
              sourceable_from=[LETTERS_OF_AUTHORITY, TRUST_DEED],
              autofill_priority=100, third_party_verifier="MASTER_OFFICE"),
    Attribute("trust_name", "name",
              sourceable_from=[LETTERS_OF_AUTHORITY, TRUST_DEED],
              autofill_priority=95),
    Attribute("trust_type", "text",
              sourceable_from=[TRUST_DEED], autofill_priority=60,
              description="inter vivos | testamentary | bewind"),
    Attribute("master_office", "text",
              sourceable_from=[LETTERS_OF_AUTHORITY], autofill_priority=70,
              description="High Court Master that issued the LOA, e.g. Cape Town."),
    Attribute("deed_date", "date",
              sourceable_from=[TRUST_DEED], autofill_priority=70),
    Attribute("trustees", "list",
              sourceable_from=[LETTERS_OF_AUTHORITY, TRUST_DEED],
              autofill_priority=90),
    Attribute("beneficiaries", "list",
              sourceable_from=[TRUST_DEED], autofill_priority=80),
    Attribute("tax_number", "digits",
              is_identity=True, sourceable_from=[SARS_NOR],
              autofill_priority=75, third_party_verifier="SARS_eFiling"),
]}


CLOSE_CORPORATION_ATTRIBUTES: dict[str, Attribute] = {a.name: a for a in [
    Attribute("registration_number", "text",
              is_identity=True, is_root=True,
              sourceable_from=[COR14_3, SARS_NOR],
              autofill_priority=100, third_party_verifier="CIPC_LIVE"),
    Attribute("registered_name", "name",
              sourceable_from=[COR14_3], autofill_priority=95),
    Attribute("members", "list", sourceable_from=[COR14_1A], autofill_priority=85),
    Attribute("registered_address", "address",
              sourceable_from=[COR14_3], autofill_priority=80),
    Attribute("tax_number", "digits",
              is_identity=True, sourceable_from=[SARS_NOR],
              autofill_priority=75, third_party_verifier="SARS_eFiling"),
]}


SOLE_PROPRIETARY_ATTRIBUTES: dict[str, Attribute] = {a.name: a for a in [
    Attribute("owner_id_number", "digits", is_identity=True, is_root=True,
              sourceable_from=[SA_SMART_ID_CARD, SA_GREEN_ID_BOOK],
              autofill_priority=100, third_party_verifier="DHA_HANIS"),
    Attribute("trade_name", "name",
              sourceable_from=[FICA_QUEST_COMPANY], autofill_priority=80),
    Attribute("tax_number", "digits", is_identity=True,
              sourceable_from=[SARS_NOR], autofill_priority=80,
              third_party_verifier="SARS_eFiling"),
    Attribute("business_address", "address",
              sourceable_from=[PROOF_OF_ADDRESS], autofill_priority=70),
]}


ASSET_ATTRIBUTES: dict[str, Attribute] = {a.name: a for a in [
    Attribute("asset_type", "text", is_root=True),
    Attribute("description", "text", autofill_priority=50),
    Attribute("registration_number", "text", is_identity=True,
              sourceable_from=[TITLE_DEED, VEHICLE_REG], autofill_priority=90),
    Attribute("address", "address", sourceable_from=[TITLE_DEED], autofill_priority=80),
    Attribute("acquisition_date", "date", sourceable_from=[TITLE_DEED]),
    Attribute("acquisition_value", "money", sourceable_from=[TITLE_DEED]),
    Attribute("insured", "text", sourceable_from=[INSURANCE_POLICY]),
    Attribute("insurer", "text", sourceable_from=[INSURANCE_POLICY]),
]}


# ---------------------------------------------------------------------------
# Master registry
# ---------------------------------------------------------------------------

ATTRIBUTES_BY_ENTITY_TYPE: dict[str, dict[str, Attribute]] = {
    PERSONAL: PERSONAL_ATTRIBUTES,
    COMPANY: COMPANY_ATTRIBUTES,
    TRUST: TRUST_ATTRIBUTES,
    CLOSE_CORPORATION: CLOSE_CORPORATION_ATTRIBUTES,
    SOLE_PROPRIETARY: SOLE_PROPRIETARY_ATTRIBUTES,
    ASSET: ASSET_ATTRIBUTES,
}


def attributes_for(entity_type: str) -> dict[str, Attribute]:
    """Return the canonical attribute map for an entity type."""
    return ATTRIBUTES_BY_ENTITY_TYPE.get(entity_type, {})


def root_attributes_for(entity_type: str) -> list[Attribute]:
    """Attributes the entity cannot exist without — block silo creation if missing."""
    return [a for a in attributes_for(entity_type).values() if a.is_root]


def sourceable_doc_types_for(entity_type: str, attribute_name: str) -> list[str]:
    """Which document types could supply this attribute?
    (Inverse: 'I have a doc of type X — which attributes can it fill?')"""
    attrs = attributes_for(entity_type)
    a = attrs.get(attribute_name)
    return a.sourceable_from if a else []


def attributes_filled_by(entity_type: str, doc_type: str) -> list[str]:
    """Which attributes can a document of `doc_type` fill on an entity of `entity_type`?"""
    return [
        a.name for a in attributes_for(entity_type).values()
        if doc_type in a.sourceable_from
    ]
