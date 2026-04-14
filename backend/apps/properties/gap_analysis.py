"""
Scenario-aware readiness / gap analysis for a Landlord.

Phase 9 of the owner-document pipeline. Takes `Landlord.classification_data`
(produced by the AI classifier) and a scenario key, walks the requirements
for that scenario, and produces a structured readiness block.

V1 implements `rental_mandate`. `purchase` is reserved for v2 and returns
None — the caller uses that as a signal the scenario wasn't computed.

See `.claude/skills/klikk-documents-owner-cipro/references/mandate-requirements.md`
for the source rules.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

SCENARIO_RENTAL_MANDATE = "rental_mandate"
SCENARIO_PURCHASE = "purchase"

# Documents required per entity type for a rental mandate.
# Keys match the classifier's normalised doc types (snake_case).
_REQUIRED_DOCS_BY_ENTITY: dict[str, list[str]] = {
    "individual": ["sa_id", "proof_of_address", "bank_confirmation", "tax_certificate", "title_deed"],
    "company": [
        "cor14_3", "cor39", "moi",
        "bank_confirmation", "proof_of_address", "tax_certificate", "title_deed",
    ],
    "cc": ["ck1", "bank_confirmation", "proof_of_address", "tax_certificate", "title_deed"],
    "trust": [
        "trust_deed", "letters_of_authority",
        "bank_confirmation", "proof_of_address", "tax_certificate", "title_deed",
    ],
    "partnership": [
        "partnership_agreement", "bank_confirmation",
        "proof_of_address", "tax_certificate", "title_deed",
    ],
}

# Required extracted fields per entity type.
_REQUIRED_FIELDS_BY_ENTITY: dict[str, list[str]] = {
    "individual": ["legal_name", "id_number", "tax_number", "physical_address", "marital_regime"],
    "company": ["legal_name", "registration_number", "tax_number", "physical_address"],
    "cc": ["legal_name", "registration_number", "tax_number", "physical_address"],
    "trust": ["legal_name", "registration_number", "tax_number", "physical_address"],
    "partnership": ["legal_name", "tax_number", "physical_address"],
}

PROOF_OF_ADDRESS_WARN_DAYS = 90
PROOF_OF_ADDRESS_BLOCK_DAYS = 180

# Identity documents are interchangeable for FICA purposes — any one of
# these satisfies the "sa_id" requirement. Passport is the fallback for
# foreign nationals or when the SA ID isn't to hand.
_IDENTITY_DOC_SYNONYMS: set[str] = {
    "sa_id", "smart_id", "id_book", "id_card", "id_document",
    "green_id", "green_id_book", "identity_document",
    "passport", "drivers_licence", "driver_licence", "drivers_license",
}


@dataclass
class MandateReadiness:
    status: str = "missing_info"
    required_signatories: list[dict[str, Any]] = field(default_factory=list)
    extracted_fields: dict[str, Any] = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
    blocking_issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "required_signatories": self.required_signatories,
            "extracted_fields": self.extracted_fields,
            "missing_fields": self.missing_fields,
            "blocking_issues": self.blocking_issues,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _norm_type(raw: str | None) -> str:
    if not raw:
        return ""
    s = raw.strip().lower()
    for ch in (".", "-", " ", "/"):
        s = s.replace(ch, "_")
    while "__" in s:
        s = s.replace("__", "_")
    return s.strip("_")


def _present_doc_types(classification_data: dict) -> set[str]:
    out: set[str] = set()
    for bucket_key in ("fica", "cipc"):
        bucket = classification_data.get(bucket_key) or {}
        for doc in bucket.get("documents") or []:
            if (doc or {}).get("status") == "found":
                out.add(_norm_type(doc.get("type")))
    return {t for t in out if t}


def _parse_iso_date(value: Any) -> date | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _find_doc(classification_data: dict, doc_type_key: str) -> dict | None:
    """Return the first classified doc matching doc_type_key (normalised)."""
    target = _norm_type(doc_type_key)
    for bucket_key in ("fica", "cipc"):
        bucket = classification_data.get(bucket_key) or {}
        for doc in bucket.get("documents") or []:
            if _norm_type((doc or {}).get("type")) == target:
                return doc
    return None


# ---------------------------------------------------------------------------
# Rental mandate computation
# ---------------------------------------------------------------------------

def _compute_rental_mandate(landlord) -> MandateReadiness:
    data = landlord.classification_data or {}
    readiness = MandateReadiness()

    entity_type = (landlord.landlord_type or "").lower() or "individual"
    extracted = (data.get("extracted_data") or {}).copy()

    # Populate known extracted_fields from multiple sources
    readiness.extracted_fields = {
        "legal_name": extracted.get("company_name") or extracted.get("legal_name") or landlord.name or None,
        "registration_number": extracted.get("registration_number") or landlord.registration_number or None,
        "id_number": extracted.get("id_number") or landlord.id_number or None,
        "vat_number": extracted.get("vat_number") or landlord.vat_number or None,
        "tax_number": extracted.get("tax_number") or None,
        "physical_address": extracted.get("address") or None,
        "postal_address": extracted.get("postal_address") or None,
        "bank_payout": _bank_payout_summary(landlord),
        "title_deed": _title_deed_summary(data),
        "marital_regime": extracted.get("marital_regime"),
    }

    # Missing required docs.
    # The "sa_id" requirement is satisfied by any identity document
    # synonym (passport, smart ID card, green book, etc.).
    required_docs = _REQUIRED_DOCS_BY_ENTITY.get(entity_type, [])
    present = _present_doc_types(data)
    identity_satisfied = bool(present & _IDENTITY_DOC_SYNONYMS)
    for doc_key in required_docs:
        if doc_key == "sa_id" and identity_satisfied:
            continue
        if doc_key not in present:
            readiness.missing_fields.append(f"document:{doc_key}")

    # Missing required fields
    required_fields = _REQUIRED_FIELDS_BY_ENTITY.get(entity_type, [])
    for f_key in required_fields:
        if not readiness.extracted_fields.get(f_key):
            if f_key not in readiness.missing_fields:
                readiness.missing_fields.append(f_key)

    # Blocking checks
    _check_company_status(data, readiness)
    _check_letters_of_authority(data, readiness, entity_type)
    _check_bank_holder_match(landlord, readiness)
    _check_title_deed_ownership(data, readiness)
    _check_proof_of_address_age(data, readiness)
    _check_identity_doc_expiry(data, readiness)

    # Authority / signatories (entity-type specific)
    readiness.required_signatories = _compute_signatories(data, landlord, readiness)

    # Status derivation
    if readiness.blocking_issues:
        readiness.status = "blocked"
    elif readiness.missing_fields:
        readiness.status = "missing_info"
    else:
        readiness.status = "ready"

    return readiness


def _bank_payout_summary(landlord) -> dict | None:
    """Pull from Landlord.bank_accounts (preferred) or classification_data."""
    acct = landlord.bank_accounts.filter(is_default=True).first()
    if not acct:
        acct = landlord.bank_accounts.first()
    if acct is None:
        return None
    last4 = (acct.account_number or "")[-4:] or None
    return {
        "holder_name": acct.account_holder or "",
        "bank": acct.bank_name or "",
        "branch_code": acct.branch_code or "",
        "account_type": acct.account_type or "",
        "account_last_4": last4,
        "confirmation_letter_present": bool(acct.confirmation_letter and acct.confirmation_letter.name),
    }


def _title_deed_summary(data: dict) -> dict | None:
    doc = _find_doc(data, "title_deed")
    if not doc:
        return None
    extracted = doc.get("extracted") or {}
    return {
        "title_deed_number": extracted.get("title_deed_number"),
        "erf": extracted.get("erf") or extracted.get("property_description"),
        "registered_owner": extracted.get("registered_owner"),
        # Match-to-entity flag is filled in by _check_title_deed_ownership
        "registered_owner_matches_entity": None,
    }


def _check_company_status(data: dict, readiness: MandateReadiness) -> None:
    cor143 = _find_doc(data, "cor14_3")
    if not cor143:
        return
    status = ((cor143.get("extracted") or {}).get("cipc_status") or "").lower()
    if status and status != "active":
        readiness.blocking_issues.append(
            f"Company CIPC status is '{status}'. Only Active companies can grant a valid rental mandate."
        )


def _check_letters_of_authority(data: dict, readiness: MandateReadiness, entity_type: str) -> None:
    if entity_type != "trust":
        return
    loa = _find_doc(data, "letters_of_authority")
    if not loa:
        # Already recorded via missing_fields if required
        return
    extracted = loa.get("extracted") or {}
    # If the classifier identified the LoA is superseded, block
    if extracted.get("is_superseded") is True:
        readiness.blocking_issues.append(
            "Letters of Authority on file have been superseded. Upload the current Letters of Authority issued by the Master of the High Court."
        )
    # Cross-check trustees against trust deed if both have trustee lists
    trust_deed = _find_doc(data, "trust_deed")
    loa_trustees = set((extracted.get("trustees") or []))
    deed_trustees = set(((trust_deed or {}).get("extracted") or {}).get("trustees") or [])
    if loa_trustees and deed_trustees and not loa_trustees.issubset(deed_trustees | loa_trustees):
        # Only warn — deed may list historical trustees
        readiness.warnings.append(
            "Letters of Authority and Trust Deed list different trustees — confirm which trustees are currently authorised."
        )


def _check_bank_holder_match(landlord, readiness: MandateReadiness) -> None:
    bank = readiness.extracted_fields.get("bank_payout") or {}
    if not bank:
        return
    legal_name = (readiness.extracted_fields.get("legal_name") or "").strip().lower()
    holder = (bank.get("holder_name") or "").strip().lower()
    if not holder or not legal_name:
        return
    if not _names_match(legal_name, holder):
        readiness.blocking_issues.append(
            f"Bank account holder '{bank.get('holder_name')}' does not match entity legal name "
            f"'{readiness.extracted_fields.get('legal_name')}'. Rent must be paid into an account in the entity's name."
        )


def _check_title_deed_ownership(data: dict, readiness: MandateReadiness) -> None:
    td = readiness.extracted_fields.get("title_deed")
    if not td:
        return
    owner = (td.get("registered_owner") or "").strip().lower()
    legal_name = (readiness.extracted_fields.get("legal_name") or "").strip().lower()
    if not owner or not legal_name:
        td["registered_owner_matches_entity"] = None
        return
    matches = _names_match(legal_name, owner)
    td["registered_owner_matches_entity"] = matches
    if not matches:
        readiness.blocking_issues.append(
            f"Title deed is registered to '{td.get('registered_owner')}', but the entity being onboarded is "
            f"'{readiness.extracted_fields.get('legal_name')}'. Confirm ownership chain."
        )


def _check_proof_of_address_age(data: dict, readiness: MandateReadiness) -> None:
    poa = _find_doc(data, "proof_of_address")
    if not poa:
        return
    extracted = poa.get("extracted") or {}
    doc_date = _parse_iso_date(extracted.get("document_date") or extracted.get("date"))
    if not doc_date:
        return
    age_days = (date.today() - doc_date).days
    if age_days > PROOF_OF_ADDRESS_BLOCK_DAYS:
        readiness.blocking_issues.append(
            f"Proof of address dated {doc_date.isoformat()} is older than 6 months. "
            "FICA requires recent proof — upload a document from the last 3 months."
        )
    elif age_days > PROOF_OF_ADDRESS_WARN_DAYS:
        readiness.warnings.append(
            f"Proof of address dated {doc_date.isoformat()} is past the 3-month FICA threshold — consider refreshing."
        )


def _check_identity_doc_expiry(data: dict, readiness: MandateReadiness) -> None:
    """Passports and driver's licences expire — flag any that already have."""
    today = date.today()
    for bucket_key in ("fica", "cipc"):
        bucket = data.get(bucket_key) or {}
        for doc in bucket.get("documents") or []:
            t = _norm_type((doc or {}).get("type"))
            if t not in {"passport", "drivers_licence", "driver_licence", "drivers_license"}:
                continue
            expiry = _parse_iso_date((doc.get("extracted") or {}).get("expiry_date"))
            if expiry and expiry < today:
                label = "Passport" if t == "passport" else "Driver's licence"
                readiness.blocking_issues.append(
                    f"{label} on file expired on {expiry.isoformat()}. Upload a current one before signing the mandate."
                )


def _compute_signatories(data: dict, landlord, readiness: MandateReadiness) -> list[dict]:
    """Minimal v1 — enumerate candidate signatories from classification_data.

    The chat / agent is expected to confirm the actual signer; we just surface
    who the documents say is authorised.
    """
    entity_type = (landlord.landlord_type or "").lower()
    out: list[dict] = []

    if entity_type == "company":
        directors = (data.get("extracted_data") or {}).get("directors") or []
        for d in directors:
            out.append({
                "role": "director",
                "name": d.get("full_name"),
                "id_number": d.get("id_number"),
                "authority_proof": "CoR39",
                "can_sign_alone": None,  # depends on MOI clause — unknown until parsed
                "reason": "Listed as director; MOI signing rule must be confirmed.",
            })
    elif entity_type == "trust":
        trust = data.get("trust_entity") or {}
        for t in trust.get("trustees") or []:
            out.append({
                "role": "trustee",
                "name": t.get("full_name"),
                "id_number": t.get("id_number"),
                "authority_proof": "Letters of Authority",
                "can_sign_alone": False,
                "reason": "Trustees must act jointly unless the deed provides otherwise.",
            })
    elif entity_type in ("individual",):
        out.append({
            "role": "owner",
            "name": landlord.name,
            "id_number": landlord.id_number or None,
            "authority_proof": "SA ID",
            "can_sign_alone": True,
            "reason": "Individual owner signs personally.",
        })
    return out


def _names_match(a: str, b: str) -> bool:
    """Loose case/punctuation-insensitive match allowing Pty-Ltd variants."""
    def norm(s: str) -> str:
        s = s.lower()
        for rep in ("(pty) ltd", "proprietary limited", "(pty)", "ltd", "limited", ",", ".", "-"):
            s = s.replace(rep, " ")
        return " ".join(s.split())
    na, nb = norm(a), norm(b)
    if na == nb:
        return True
    # Token subset match (handles "ACME Property" vs "ACME Property (Pty) Ltd")
    ta, tb = set(na.split()), set(nb.split())
    if ta and tb and (ta.issubset(tb) or tb.issubset(ta)):
        return True
    return False


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compute_gap_analysis(landlord, scenario: str = SCENARIO_RENTAL_MANDATE) -> dict | None:
    """Return the readiness block for one scenario, or None for unsupported.

    Callers should treat None as 'not computed for this run' — never fabricate.
    """
    if scenario == SCENARIO_RENTAL_MANDATE:
        return _compute_rental_mandate(landlord).to_dict()
    if scenario == SCENARIO_PURCHASE:
        # Reserved for v2
        return None
    logger.warning("compute_gap_analysis: unknown scenario %r", scenario)
    return None
