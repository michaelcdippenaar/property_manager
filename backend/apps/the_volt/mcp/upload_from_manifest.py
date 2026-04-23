"""
upload_from_manifest.py — Bulk-upload enriched JSONL manifests into The Volt.

Reads enriched JSONL manifests (with extracted_data) and uploads documents
directly via Django ORM — no HTTP, no MCP transport, no API keys required.

Usage:
    python upload_from_manifest.py --manifest /path/to/manifest.jsonl \\
        --vault-owner-email owner@example.com

    python upload_from_manifest.py --manifest-dir /path/to/manifests/ \\
        --vault-owner-email owner@example.com --dry-run

    python upload_from_manifest.py --manifest /path/to/manifest.jsonl \\
        --vault-owner-email owner@example.com --skip-other
"""
from __future__ import annotations

# ── 1. Bootstrap Django ────────────────────────────────────────────────────────
import os
import sys

# Ensure the backend/ directory is on sys.path so Django can resolve apps
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", "..", "..", ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django  # noqa: E402

django.setup()

# ── 2. Std-library + third-party imports (after Django setup) ─────────────────
import argparse
import base64
import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from django.core.files.base import ContentFile
from django.db import transaction

# ── 3. Internal imports ───────────────────────────────────────────────────────
from apps.the_volt.documents.models import DocumentVersion, VaultDocument
from apps.the_volt.encryption.utils import encrypt_bytes
from apps.the_volt.entities.models import (
    EntityRelationship,
    RelationshipTypeCatalogue,
    VaultEntity,
)
from apps.the_volt.gateway.models import VaultWriteAudit
from apps.the_volt.owners.models import VaultOwner
from apps.the_volt.mcp.tools.write import _upsert_entity

# ── 4. Logging setup ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("upload_from_manifest")


# ── 5. Fake MCP context so _upsert_entity / write_audit work offline ──────────

@dataclass(frozen=True)
class _ScriptApiKey:
    """Stub API key used in audit rows when running from the upload script.

    We set pk=None so write_audit stores api_key=NULL in the DB, clearly
    distinguishing script-origin writes from MCP tool writes.
    """
    label: str = "upload_from_manifest.py"
    api_key_prefix: str = "script_"
    pk: int | None = None


@dataclass(frozen=True)
class _ScriptContext:
    """Mimics VoltMcpContext but resolves from VaultOwner directly.

    api_key is a stub — write_audit passes it to VaultWriteAudit.api_key (a nullable FK).
    We override write_audit at install time to pass api_key=None instead.
    """
    vault_owner: VaultOwner
    api_key: _ScriptApiKey = field(default_factory=_ScriptApiKey)

    @property
    def vault_id(self) -> int:
        return self.vault_owner.pk

    @property
    def user_email(self) -> str:
        return self.vault_owner.user.email


_ACTIVE_CONTEXT: _ScriptContext | None = None


def _install_context(ctx: _ScriptContext) -> None:
    """Install our script context so _upsert_entity / write_audit resolve the vault owner.

    We set the module-level _cached_stdio_context directly (the cached path used by
    get_context) AND replace the get_context function itself for any code that
    imported the function reference before this patch ran.
    """
    import apps.the_volt.mcp.auth as _auth_module

    # Set the cached context — this is what get_context() returns in stdio mode
    _auth_module._cached_stdio_context = ctx

    # Also replace the function itself for belt-and-suspenders
    _original_get_context = _auth_module.get_context

    def _get_context_override():
        return ctx

    _auth_module.get_context = _get_context_override

    # Replace in the write module too (it may have imported the function reference)
    try:
        from apps.the_volt.mcp.tools import write as _write_module
        # write.py uses get_context via the audit module, so patch audit too
        from apps.the_volt.mcp import audit as _audit_module
        _audit_module.get_context = _get_context_override
    except ImportError:
        pass

    global _ACTIVE_CONTEXT
    _ACTIVE_CONTEXT = ctx
    logger.debug("Installed script context for vault owner: %s", ctx.user_email)


# ── 6. Processing order ───────────────────────────────────────────────────────

# Identity-establishing document types that must be processed first
_IDENTITY_FIRST = {
    "sa_id_document",
    "passport",
    "cipc_cor14_3",
    "ck1_registration",
    "trust_deed",
    "letters_of_authority",
}

_CONFIDENCE_ORDER = {"high": 0, "medium": 1, "low": 2}


def _sort_key(entry: dict) -> tuple[int, int]:
    """Identity docs first (0), then by confidence (high=0, medium=1, low=2)."""
    doc_type = entry.get("document_type_code", "")
    is_identity = 0 if doc_type in _IDENTITY_FIRST else 1
    confidence = _CONFIDENCE_ORDER.get(entry.get("confidence", "low"), 2)
    return (is_identity, confidence)


# ── 7. Entity field extraction ────────────────────────────────────────────────

def _fields_for_personal(data: dict) -> dict:
    return {k: data[k] for k in ("id_number", "date_of_birth", "email", "phone") if k in data}


def _fields_for_company(data: dict) -> dict:
    return {k: data[k] for k in ("reg_number", "company_name") if k in data}


def _fields_for_trust(data: dict) -> dict:
    return {k: data[k] for k in ("trust_number", "trust_name") if k in data}


def _fields_for_asset(data: dict) -> dict:
    return {k: data[k] for k in ("registration_number", "address") if k in data}


_FIELD_EXTRACTORS = {
    "personal": _fields_for_personal,
    "company": _fields_for_company,
    "trust": _fields_for_trust,
    "close_corporation": _fields_for_company,  # also uses reg_number
    "sole_proprietary": _fields_for_personal,
    "asset": _fields_for_asset,
}


# ── 8. Relationship building ──────────────────────────────────────────────────

# CRITICAL BUSINESS RULE: Only legal documents may create entity relationships.
# Bank statements, ID copies, proof-of-address etc. may mention directors/trustees
# in their extracted_data, but those mentions are informational — not authoritative.
# Only the legal instrument itself (trust deed, CIPC registration, court order, MOI,
# share certificate, resolution, etc.) is the source of truth for a relationship.
_LEGAL_DOCUMENT_TYPES = {
    # Trust instruments
    "trust_deed",
    "letters_of_authority",
    "trust_resolution",
    # Company / CC instruments
    "cipc_cor14_3",       # Company registration certificate
    "cipc_cor39",         # Annual return / amendment
    "ck1_registration",   # CC founding statement
    "cc_founding_statement",
    "moi",                # Memorandum of Incorporation
    "share_certificate",
    "directors_resolution",
    "shareholder_resolution",
    "shareholder_agreement",
    # Marriage / divorce
    "marriage_certificate",
    "antenuptial_contract",
    "divorce_order",
    "court_order",
    # Ownership / title
    "title_deed",
    # Powers / mandates
    "power_of_attorney",
    # Will / estate
    "will",
    "estate_liquidation_account",
}

# Maps extracted_data key → (relationship_type_code, role in the relationship)
# Each mapping: (list_key_in_extracted_data, rel_code)
_RELATIONSHIP_MAPS = [
    ("trustees", "trustee_of"),
    ("trustees_authorised", "trustee_of"),
    ("directors", "director_of"),
    ("directors_present", "director_of"),
    ("shareholders", "shareholder_of"),
    ("beneficiaries", "beneficial_owner_of"),
    ("members", "member_of"),
]


def _rel_type_cache() -> dict[str, RelationshipTypeCatalogue]:
    """Lazy-loaded cache of all active RelationshipTypeCatalogue entries by code."""
    if not hasattr(_rel_type_cache, "_cache"):
        _rel_type_cache._cache = {
            r.code: r for r in RelationshipTypeCatalogue.objects.filter(is_active=True)
        }
    return _rel_type_cache._cache


def _create_relationship(
    from_entity: VaultEntity,
    to_entity: VaultEntity,
    rel_code: str,
    vault_owner: VaultOwner,
    dry_run: bool,
    stats: "Stats",
) -> None:
    """Create (or skip on dry_run) an EntityRelationship edge. Idempotent."""
    catalogue = _rel_type_cache()
    rel_type = catalogue.get(rel_code)
    if rel_type is None:
        logger.warning(
            "  Relationship type '%s' not found in catalogue — skipping link %s → %s",
            rel_code,
            from_entity.name,
            to_entity.name,
        )
        return

    if dry_run:
        logger.info(
            "  [DRY-RUN] Would link: %s -[%s]-> %s",
            from_entity.name,
            rel_code,
            to_entity.name,
        )
        stats.relationships_created += 1
        return

    with transaction.atomic():
        rel, created = EntityRelationship.objects.update_or_create(
            from_entity=from_entity,
            to_entity=to_entity,
            relationship_type=rel_type,
            defaults={"vault": vault_owner, "metadata": {}},
        )

    action = "Created" if created else "Already exists"
    logger.info(
        "  %s relationship: %s -[%s]-> %s",
        action,
        from_entity.name,
        rel_code,
        to_entity.name,
    )
    if created:
        stats.relationships_created += 1


def _clean_party_name(raw: str) -> str:
    """Strip parenthetical suffixes from party names.

    'Stefanie Dippenaar (née Viljoen, ID 8701180125085)' → 'Stefanie Dippenaar'
    'Michaelis Christoffel Dippenaar (ID 8205315092087)' → 'Michaelis Christoffel Dippenaar'
    """
    import re
    # Remove everything from the first opening paren to the end
    cleaned = re.sub(r"\s*\(.*$", "", raw).strip()
    return cleaned if cleaned else raw.strip()


_NAME_SUFFIXES = {"snr", "jnr", "sr", "jr", "senior", "junior", "(snr)", "(jnr)"}


def _normalise_name(raw: str) -> tuple[str, list[str]]:
    """Normalise a name for comparison. Returns (surname, [other_parts])."""
    parts = raw.lower().strip().split()
    # Strip suffixes like Snr, Jnr
    parts = [p for p in parts if p not in _NAME_SUFFIXES]
    if not parts:
        return ("", [])
    # Last word is surname
    return (parts[-1], parts[:-1])


def _is_same_person(name_a: str, name_b: str) -> bool:
    """Fuzzy match for South African names.

    Handles:
    - Suffix variations: 'Michael Dippenaar Snr' vs 'Michaelis Christoffel Dippenaar'
    - Formal vs informal: 'Michael' vs 'Michaelis' (one starts with the other)
    - Contained names: 'MC Dippenaar' vs 'Michaelis Christoffel Dippenaar'
    """
    a = name_a.lower().strip()
    b = name_b.lower().strip()
    if a == b:
        return True
    if a in b or b in a:
        return True

    # Normalise: strip suffixes, split into surname + other parts
    surname_a, parts_a = _normalise_name(name_a)
    surname_b, parts_b = _normalise_name(name_b)

    # Must share a surname
    if surname_a != surname_b or not surname_a:
        return False

    # Same surname — check if first names overlap
    if not parts_a or not parts_b:
        # One is just the surname — might be same person
        return True

    first_a = parts_a[0]
    first_b = parts_b[0]

    # Exact first name match
    if first_a == first_b:
        return True

    # One first name starts with the other (MC ↔ Michaelis, Michael ↔ Michaelis)
    if first_a.startswith(first_b) or first_b.startswith(first_a):
        return True

    # Initials match: "mc" matches "michaelis christoffel"
    if len(first_a) <= 3 and len(parts_b) >= 2:
        initials_b = "".join(p[0] for p in parts_b)
        if first_a == initials_b:
            return True
    if len(first_b) <= 3 and len(parts_a) >= 2:
        initials_a = "".join(p[0] for p in parts_a)
        if first_b == initials_a:
            return True

    return False


def _build_spouse_relationships(
    extracted_data: dict,
    primary_entity: VaultEntity,
    vault_owner: VaultOwner,
    document_type_code: str,
    dry_run: bool,
    stats: "Stats",
) -> None:
    """Handle marriage_certificate, divorce_order, and antenuptial_contract.

    These documents list two parties/spouses. We create a bidirectional
    relationship between the two people (married_to or divorced_from).
    The primary_entity is the person the document is filed under — we find
    the OTHER party and link them.
    """
    # Determine which relationship to create based on document type
    if document_type_code == "marriage_certificate":
        rel_code = "married_to"
        # Marriage certs use spouse_names list
        parties = extracted_data.get("spouse_names") or extracted_data.get("parties") or []
        metadata = {}
        if extracted_data.get("date_of_marriage"):
            metadata["date_of_marriage"] = extracted_data["date_of_marriage"]
        if extracted_data.get("regime"):
            metadata["marriage_regime"] = extracted_data["regime"]
    elif document_type_code == "antenuptial_contract":
        rel_code = "married_to"
        parties = extracted_data.get("parties") or []
        metadata = {}
        if extracted_data.get("registration_number"):
            metadata["anc_number"] = extracted_data["registration_number"]
        if extracted_data.get("accrual_system") is not None:
            metadata["marriage_regime"] = (
                "ANC with accrual" if extracted_data["accrual_system"] else "ANC without accrual"
            )
    elif document_type_code == "divorce_order":
        rel_code = "divorced_from"
        parties = extracted_data.get("parties") or []
        metadata = {}
        if extracted_data.get("date"):
            metadata["date_of_divorce"] = extracted_data["date"]
    else:
        return  # Not a spouse-related document type

    if not parties or not isinstance(parties, list) or len(parties) < 2:
        return

    # Find the OTHER party (not the primary entity)
    other_parties = []
    for p in parties:
        if not isinstance(p, str):
            continue
        cleaned = _clean_party_name(p)
        if not cleaned:
            continue
        # Skip the primary entity
        if _is_same_person(cleaned, primary_entity.name):
            continue
        other_parties.append(cleaned)

    for other_name in other_parties:
        logger.info(
            "  Upserting spouse/party: '%s' (from %s → %s)",
            other_name,
            document_type_code,
            rel_code,
        )
        try:
            other_result = _upsert_entity(
                entity_type="personal",
                name=other_name,
                fields={},
                op="upload_script",
            )
            other_entity = VaultEntity.objects.get(pk=other_result["id"])
        except Exception as exc:
            logger.error("  Failed to upsert spouse '%s': %s", other_name, exc)
            stats.errors += 1
            continue

        _create_relationship(
            from_entity=primary_entity,
            to_entity=other_entity,
            rel_code=rel_code,
            vault_owner=vault_owner,
            dry_run=dry_run,
            stats=stats,
        )


def _build_relationships(
    extracted_data: dict,
    primary_entity: VaultEntity,
    vault_owner: VaultOwner,
    document_type_code: str,
    dry_run: bool,
    stats: "Stats",
) -> None:
    """Walk extracted_data lists and create person → entity relationships.

    Also handles pair-based relationships:
    - marriage_certificate: spouse_names → married_to (bidirectional)
    - divorce_order: parties → divorced_from (bidirectional)
    - antenuptial_contract: parties → married_to with ANC metadata
    """
    entity_type = primary_entity.entity_type

    # ── Pair-based spouse relationships ──────────────────────────────────────
    _build_spouse_relationships(
        extracted_data=extracted_data,
        primary_entity=primary_entity,
        vault_owner=vault_owner,
        document_type_code=document_type_code,
        dry_run=dry_run,
        stats=stats,
    )

    # ── List-based relationships (directors, trustees, etc.) ─────────────────
    for list_key, rel_code in _RELATIONSHIP_MAPS:
        people = extracted_data.get(list_key)
        if not people:
            continue
        if not isinstance(people, list):
            logger.warning("  %s is not a list in extracted_data, skipping", list_key)
            continue

        for person_entry in people:
            if not person_entry:
                continue

            # Handle both formats:
            #   string:  "Michaelis Christoffel Dippenaar"
            #   dict:    {"name": "...", "id_number": "...", ...}
            person_fields: dict = {}
            if isinstance(person_entry, dict):
                person_name = person_entry.get("name", "").strip()
                if not person_name:
                    continue
                # Carry identity data through for dedup
                if person_entry.get("id_number"):
                    person_fields["id_number"] = str(person_entry["id_number"])
                if person_entry.get("appointment_date"):
                    person_fields["appointment_date"] = person_entry["appointment_date"]
            elif isinstance(person_entry, str):
                person_name = person_entry.strip()
            else:
                continue

            if not person_name:
                continue

            logger.info("  Upserting person: '%s' (from %s)", person_name, list_key)
            try:
                person_result = _upsert_entity(
                    entity_type="personal",
                    name=person_name,
                    fields=person_fields,
                    op="upload_script",
                )
                person_entity = VaultEntity.objects.get(pk=person_result["id"])
            except Exception as exc:
                logger.error(
                    "  Failed to upsert person '%s': %s", person_name, exc
                )
                stats.errors += 1
                continue

            _create_relationship(
                from_entity=person_entity,
                to_entity=primary_entity,
                rel_code=rel_code,
                vault_owner=vault_owner,
                dry_run=dry_run,
                stats=stats,
            )

    # registered_owner → holds_asset (person or entity linked to this asset)
    registered_owner = extracted_data.get("registered_owner")
    if registered_owner and isinstance(registered_owner, str):
        registered_owner = registered_owner.strip()
        if registered_owner:
            logger.info("  Upserting registered_owner: '%s'", registered_owner)
            try:
                owner_result = _upsert_entity(
                    entity_type="personal",
                    name=registered_owner,
                    fields={},
                    op="upload_script",
                )
                owner_entity = VaultEntity.objects.get(pk=owner_result["id"])
                _create_relationship(
                    from_entity=owner_entity,
                    to_entity=primary_entity,
                    rel_code="holds_asset",
                    vault_owner=vault_owner,
                    dry_run=dry_run,
                    stats=stats,
                )
            except Exception as exc:
                logger.error(
                    "  Failed to link registered_owner '%s': %s", registered_owner, exc
                )
                stats.errors += 1


# ── 8b. Counterparty entity creation (transaction documents) ────────────────

# Transaction document types that establish property ownership chains and tenancy.
# These are NOT the same as the _LEGAL_DOCUMENT_TYPES guard above — transaction
# documents create counterparty entities and ownership/tenancy edges.
_TRANSACTION_DOCUMENT_TYPES = {
    "otp",                  # Offer to Purchase — seller, buyer, agent
    "transfer_statement",   # Transfer recon — transfer_from, transfer_to
    "title_deed",           # Title deed — previous and new owner
    "rental_agreement",     # Lease — tenant(s), managing agent, landlord
    "bond_facility_letter", # Bond — bank/lender
}

# Known self-entities to skip (we don't create Klikk as a counterparty)
_SELF_ENTITY_NAMES = {
    "klikk", "klikk (pty) ltd", "klikk pty ltd", "klikk (eiendoms) bpk",
    "klikk (pty) ltd 2016/113758/07", "klikk pty ltd (2016/113758/07)",
}

# SA Trust pattern: contains 'trust' or 'familietrust'
_TRUST_INDICATORS = {"trust", "familietrust", "familie trust"}

# CC pattern: ends with ' cc' or 'cc' or 'bk'
_CC_INDICATORS = {" cc", " bk"}


def _infer_entity_type(name: str, reg_hint: str | None = None) -> str:
    """Infer entity_type from the name/registration context.

    Returns 'trust', 'company', 'close_corporation', or 'personal'.
    """
    lower = name.lower().strip()

    # Trust detection
    for indicator in _TRUST_INDICATORS:
        if indicator in lower:
            return "trust"

    # CC detection
    for indicator in _CC_INDICATORS:
        if lower.endswith(indicator):
            return "close_corporation"

    # Company detection: (Pty) Ltd, Bpk, Ltd, Proprietary, etc.
    company_markers = ["(pty)", "pty ltd", "bpk", "proprietary", "limited", "inc"]
    for marker in company_markers:
        if marker in lower:
            return "company"

    # Registration number hints
    if reg_hint:
        reg_lower = reg_hint.lower().strip()
        if reg_lower.startswith("it"):
            return "trust"
        if "/" in reg_lower and len(reg_lower) > 5:
            return "company"

    return "personal"


def _fields_for_counterparty(entity_type: str, extracted_data: dict, name: str) -> dict:
    """Build identity fields for a counterparty entity from transaction document data."""
    fields: dict[str, Any] = {}

    if entity_type == "trust":
        # Try to extract trust number from seller_trust_numbers, seller_reg, etc.
        trust_num = (
            extracted_data.get("seller_trust_numbers")
            or extracted_data.get("seller_reg")
            or extracted_data.get("trust_number")
        )
        if trust_num:
            # May be comma-separated for multi-trust sellers
            if isinstance(trust_num, str) and "," not in trust_num:
                fields["trust_number"] = trust_num
            elif isinstance(trust_num, str):
                # Take first trust number for this entity
                parts = [p.strip() for p in trust_num.split(",")]
                # Match by name if possible
                lower_name = name.lower()
                for p in parts:
                    if lower_name.startswith(p[:3].lower()):
                        fields["trust_number"] = p
                        break
                else:
                    fields["trust_number"] = parts[0]
        fields["trust_name"] = name

    elif entity_type == "company":
        reg = (
            extracted_data.get("seller_reg")
            or extracted_data.get("buyer_reg")
            or extracted_data.get("tenant_reg")
        )
        if reg:
            fields["reg_number"] = reg
        fields["company_name"] = name

    elif entity_type == "close_corporation":
        reg = extracted_data.get("tenant_reg")
        if reg:
            fields["reg_number"] = reg
        fields["company_name"] = name

    elif entity_type == "personal":
        id_num = (
            extracted_data.get("seller_id")
            or extracted_data.get("tenant_id")
        )
        if id_num:
            fields["id_number"] = id_num
        email = (
            extracted_data.get("seller_email")
            or extracted_data.get("seller_contact")
            or extracted_data.get("tenant_email")
        )
        if email and "@" in str(email):
            fields["email"] = email
        phone = extracted_data.get("seller_cell") or extracted_data.get("tenant_cell")
        if phone:
            fields["phone"] = phone

    return fields


def _is_self_entity(name: str) -> bool:
    """Check if this entity name refers to Klikk itself (skip creating it as counterparty)."""
    lower = name.lower().strip()
    return lower in _SELF_ENTITY_NAMES or lower.startswith("klikk")


def _upsert_counterparty(
    name: str,
    entity_type: str,
    fields: dict,
    dry_run: bool,
    stats: "Stats",
) -> VaultEntity | None:
    """Create or find a counterparty entity. Returns the entity or None on failure."""
    if dry_run:
        logger.info("  [DRY-RUN] Would upsert counterparty: %s (%s)", name, entity_type)
        stats.entities_created += 1
        return None

    try:
        result = _upsert_entity(
            entity_type=entity_type,
            name=name,
            fields=fields,
            op="upload_script_counterparty",
        )
        entity = VaultEntity.objects.get(pk=result["id"])
        action = "Created" if result.get("created") else "Found"
        logger.info("  %s counterparty: %s (id=%d, type=%s)", action, name, entity.pk, entity_type)
        if result.get("created"):
            stats.entities_created += 1
        return entity
    except Exception as exc:
        logger.error("  Failed to upsert counterparty '%s': %s", name, exc)
        stats.errors += 1
        return None


def _build_counterparty_entities(
    extracted_data: dict,
    primary_entity: VaultEntity,
    vault_owner: VaultOwner,
    document_type_code: str,
    dry_run: bool,
    stats: "Stats",
) -> None:
    """Create counterparty entities and relationships from transaction documents.

    Handles:
    - OTP: seller entity + sold_to relationship, agent
    - Transfer statement: transfer_from/to entities
    - Rental agreement: tenant entities + tenant_of relationship, managing agent
    - Title deed: transfer entities + holds_asset
    """
    if document_type_code not in _TRANSACTION_DOCUMENT_TYPES:
        return

    # ── Sellers / Previous Owners ───────────────────────────────────────────
    seller_name = extracted_data.get("seller") or extracted_data.get("transfer_from")
    if seller_name and isinstance(seller_name, str) and not _is_self_entity(seller_name):
        seller_name = seller_name.strip()
        seller_reg = extracted_data.get("seller_reg") or extracted_data.get("seller_trust_numbers")
        entity_type = _infer_entity_type(seller_name, seller_reg)
        fields = _fields_for_counterparty(entity_type, extracted_data, seller_name)

        seller_entity = _upsert_counterparty(seller_name, entity_type, fields, dry_run, stats)
        if seller_entity and primary_entity.entity_type == "asset":
            # Seller sold this asset → sold_to → Klikk (but we model as seller → sold_to → asset)
            _create_relationship(
                from_entity=seller_entity,
                to_entity=primary_entity,
                rel_code="sold_to",
                vault_owner=vault_owner,
                dry_run=dry_run,
                stats=stats,
            )

        # Handle multi-trust sellers (e.g. "Renee Steenkamp Familietrust & Callie Steenkamp Familietrust")
        if seller_name and "&" in seller_name:
            parts = [p.strip() for p in seller_name.split("&")]
            trust_numbers = extracted_data.get("seller_trust_numbers", "")
            trust_nums = [t.strip() for t in trust_numbers.split(",")] if trust_numbers else []

            for i, part_name in enumerate(parts):
                part_name = part_name.strip()
                if not part_name or _is_self_entity(part_name):
                    continue
                part_type = _infer_entity_type(part_name)
                part_fields: dict[str, Any] = {}
                if part_type == "trust" and i < len(trust_nums):
                    part_fields["trust_number"] = trust_nums[i]
                    part_fields["trust_name"] = part_name

                part_entity = _upsert_counterparty(part_name, part_type, part_fields, dry_run, stats)
                if part_entity and primary_entity.entity_type == "asset":
                    _create_relationship(
                        from_entity=part_entity,
                        to_entity=primary_entity,
                        rel_code="sold_to",
                        vault_owner=vault_owner,
                        dry_run=dry_run,
                        stats=stats,
                    )

    # ── Buyers ──────────────────────────────────────────────────────────────
    buyer_name = extracted_data.get("buyer") or extracted_data.get("transfer_to")
    if buyer_name and isinstance(buyer_name, str):
        buyer_name = buyer_name.strip()
        if _is_self_entity(buyer_name):
            # Buyer is us (Klikk) → create holds_asset from Klikk to this property
            if primary_entity.entity_type == "asset":
                try:
                    klikk_result = _upsert_entity(
                        entity_type="company",
                        name="Klikk (Pty) Ltd",
                        fields={"reg_number": "2016/113758/07"},
                        op="upload_script_counterparty",
                    )
                    klikk_entity = VaultEntity.objects.get(pk=klikk_result["id"])
                    _create_relationship(
                        from_entity=klikk_entity,
                        to_entity=primary_entity,
                        rel_code="holds_asset",
                        vault_owner=vault_owner,
                        dry_run=dry_run,
                        stats=stats,
                    )
                    logger.info("  Linked Klikk → holds_asset → %s", primary_entity.name)
                except Exception as exc:
                    logger.error("  Failed to link Klikk ownership: %s", exc)
                    stats.errors += 1
        else:
            # External buyer → create counterparty + purchased_from edge
            buyer_reg = extracted_data.get("buyer_reg")
            entity_type = _infer_entity_type(buyer_name, buyer_reg)
            fields = _fields_for_counterparty(entity_type, extracted_data, buyer_name)

            buyer_entity = _upsert_counterparty(buyer_name, entity_type, fields, dry_run, stats)
            if buyer_entity and primary_entity.entity_type == "asset":
                _create_relationship(
                    from_entity=buyer_entity,
                    to_entity=primary_entity,
                    rel_code="purchased_from",
                    vault_owner=vault_owner,
                    dry_run=dry_run,
                    stats=stats,
                )

    # ── Tenants ─────────────────────────────────────────────────────────────
    if document_type_code == "rental_agreement":
        # Tenant entity (CC, company, etc.)
        tenant_entity_name = extracted_data.get("tenant_entity")
        if tenant_entity_name and isinstance(tenant_entity_name, str) and not _is_self_entity(tenant_entity_name):
            tenant_entity_name = tenant_entity_name.strip()
            tenant_reg = extracted_data.get("tenant_reg")
            entity_type = _infer_entity_type(tenant_entity_name, tenant_reg)
            fields = _fields_for_counterparty(entity_type, extracted_data, tenant_entity_name)
            if extracted_data.get("tenant_vat"):
                fields["vat_number"] = extracted_data["tenant_vat"]

            t_entity = _upsert_counterparty(tenant_entity_name, entity_type, fields, dry_run, stats)
            if t_entity and primary_entity.entity_type == "asset":
                _create_relationship(
                    from_entity=t_entity,
                    to_entity=primary_entity,
                    rel_code="tenant_of",
                    vault_owner=vault_owner,
                    dry_run=dry_run,
                    stats=stats,
                )

        # Individual tenants
        tenant_names = extracted_data.get("tenant_names", [])
        if isinstance(tenant_names, list):
            for tn in tenant_names:
                if not tn or not isinstance(tn, str):
                    continue
                tn = tn.strip()
                if not tn or _is_self_entity(tn):
                    continue

                # Individual tenants are always personal
                t_fields: dict[str, Any] = {}
                if extracted_data.get("tenant_id") and len(tenant_names) == 1:
                    t_fields["id_number"] = extracted_data["tenant_id"]

                t_entity = _upsert_counterparty(tn, "personal", t_fields, dry_run, stats)
                if t_entity and primary_entity.entity_type == "asset":
                    _create_relationship(
                        from_entity=t_entity,
                        to_entity=primary_entity,
                        rel_code="tenant_of",
                        vault_owner=vault_owner,
                        dry_run=dry_run,
                        stats=stats,
                    )

                    # If there's a tenant_entity, link the person to the CC/company
                    if tenant_entity_name and not _is_self_entity(tenant_entity_name):
                        try:
                            te_type = _infer_entity_type(tenant_entity_name)
                            te_result = _upsert_entity(
                                entity_type=te_type,
                                name=tenant_entity_name.strip(),
                                fields={},
                                op="upload_script_counterparty",
                            )
                            te_entity = VaultEntity.objects.get(pk=te_result["id"])
                            rel_code = "member_of" if te_type == "close_corporation" else "director_of"
                            _create_relationship(
                                from_entity=t_entity,
                                to_entity=te_entity,
                                rel_code=rel_code,
                                vault_owner=vault_owner,
                                dry_run=dry_run,
                                stats=stats,
                            )
                        except Exception as exc:
                            logger.error("  Failed to link tenant to entity: %s", exc)

    # ── Managing Agents ─────────────────────────────────────────────────────
    managing_agent = extracted_data.get("managing_agent")
    if managing_agent and isinstance(managing_agent, str) and not _is_self_entity(managing_agent):
        managing_agent = managing_agent.strip()
        entity_type = _infer_entity_type(managing_agent)
        if entity_type == "personal":
            entity_type = "company"  # managing agents are always companies

        ma_entity = _upsert_counterparty(managing_agent, entity_type, {"company_name": managing_agent}, dry_run, stats)
        if ma_entity and primary_entity.entity_type == "asset":
            _create_relationship(
                from_entity=primary_entity,
                to_entity=ma_entity,
                rel_code="managed_by",
                vault_owner=vault_owner,
                dry_run=dry_run,
                stats=stats,
            )

    # ── Estate Agents / Brokers ─────────────────────────────────────────────
    agent_company = extracted_data.get("agent_company")
    if agent_company and isinstance(agent_company, str) and not _is_self_entity(agent_company):
        agent_company = agent_company.strip()
        ac_entity = _upsert_counterparty(
            agent_company, "company", {"company_name": agent_company}, dry_run, stats
        )
        if ac_entity and primary_entity.entity_type == "asset":
            _create_relationship(
                from_entity=primary_entity,
                to_entity=ac_entity,
                rel_code="brokered_by",
                vault_owner=vault_owner,
                dry_run=dry_run,
                stats=stats,
            )

    # ── Previous Owner (from transfer docs with owner_at_time) ──────────────
    owner_at_time = extracted_data.get("owner_at_time")
    if owner_at_time and isinstance(owner_at_time, str) and not _is_self_entity(owner_at_time):
        owner_at_time = owner_at_time.strip()
        entity_type = _infer_entity_type(owner_at_time)
        fields = _fields_for_counterparty(entity_type, extracted_data, owner_at_time)

        ot_entity = _upsert_counterparty(owner_at_time, entity_type, fields, dry_run, stats)
        if ot_entity and primary_entity.entity_type == "asset":
            _create_relationship(
                from_entity=ot_entity,
                to_entity=primary_entity,
                rel_code="sold_to",
                vault_owner=vault_owner,
                dry_run=dry_run,
                stats=stats,
            )


# ── 9. Document upload ────────────────────────────────────────────────────────

def _attach_document(
    entity: VaultEntity,
    vault_owner: VaultOwner,
    document_type_code: str,
    label: str,
    plaintext: bytes,
    original_filename: str,
    mime_type: str,
    extracted_data: dict,
    dry_run: bool,
    stats: "Stats",
) -> dict | None:
    """Encrypt + persist a DocumentVersion. Returns result dict or None on dry_run."""
    sha256_hash = hashlib.sha256(plaintext).hexdigest()
    file_size = len(plaintext)

    if dry_run:
        logger.info(
            "  [DRY-RUN] Would upload %s (%d bytes, sha256=%s…)",
            original_filename,
            file_size,
            sha256_hash[:12],
        )
        stats.documents_uploaded += 1
        return {"dry_run": True, "sha256_hash": sha256_hash}

    encrypted = encrypt_bytes(plaintext, vault_owner.pk)

    with transaction.atomic():
        doc, doc_created = VaultDocument.objects.get_or_create(
            entity=entity,
            document_type=document_type_code,
            label=label,
        )
        version = DocumentVersion(
            document=doc,
            original_filename=original_filename,
            file_size_bytes=file_size,
            sha256_hash=sha256_hash,
            mime_type=mime_type,
            extracted_data=extracted_data,
        )
        version.save()
        version.file.save(
            f"{version.version_number}.enc",
            ContentFile(encrypted),
            save=True,
        )
        doc.current_version = version
        doc.save(update_fields=["current_version", "updated_at"])

    # Audit row (api_key=None — script caller, not an MCP API key)
    try:
        VaultWriteAudit.objects.create(
            vault=vault_owner,
            api_key=None,
            operation="attach_document",
            target_model="DocumentVersion",
            target_id=version.pk,
            before={},
            after={
                "document_id": doc.pk,
                "version_number": version.version_number,
                "sha256_hash": sha256_hash,
                "file_size_bytes": file_size,
                "document_created": doc_created,
                "source": "upload_from_manifest.py",
            },
            client_info={"tool": "upload_from_manifest", "filename": original_filename},
        )
    except Exception:
        logger.exception("Failed to write VaultWriteAudit for document upload")

    logger.info(
        "  Uploaded: %s (doc_id=%d, version=%d, %d bytes)",
        original_filename,
        doc.pk,
        version.version_number,
        file_size,
    )
    stats.documents_uploaded += 1
    return {
        "document_id": doc.pk,
        "version_id": version.pk,
        "version_number": version.version_number,
        "sha256_hash": sha256_hash,
        "document_created": doc_created,
    }


# ── 10. Per-entry processor ───────────────────────────────────────────────────

@dataclass
class Stats:
    entities_created: int = 0
    documents_uploaded: int = 0
    relationships_created: int = 0
    errors: int = 0
    skipped: int = 0


def _process_entry(
    entry: dict,
    vault_owner: VaultOwner,
    dry_run: bool,
    skip_other: bool,
    stats: Stats,
) -> None:
    """Process one JSONL entry end-to-end."""
    source_path = entry.get("source_path", "")
    entity_name = entry.get("entity_name", "")
    entity_type = entry.get("entity_type", "personal")
    document_type_code = entry.get("document_type_code", "other")
    label = entry.get("label") or document_type_code
    mime_type = entry.get("mime_type", "application/octet-stream")
    extracted_data: dict = entry.get("extracted_data") or {}

    logger.info(
        "Processing: %s | %s | %s | %s",
        entity_name,
        entity_type,
        document_type_code,
        os.path.basename(source_path),
    )

    # Skip 'other' if requested
    if skip_other and document_type_code == "other":
        logger.info("  Skipping: document_type_code='other' (--skip-other)")
        stats.skipped += 1
        return

    # Validate source file
    if not source_path or not os.path.isfile(source_path):
        logger.error("  source_path not found or missing: '%s' — skipping", source_path)
        stats.errors += 1
        return

    # 1. Create / find the primary entity
    field_extractor = _FIELD_EXTRACTORS.get(entity_type, lambda d: {})
    fields = field_extractor(extracted_data)

    try:
        entity_result = _upsert_entity(
            entity_type=entity_type,
            name=entity_name,
            fields=fields,
            op="upload_script",
        )
    except Exception as exc:
        logger.error("  Failed to upsert entity '%s': %s", entity_name, exc)
        stats.errors += 1
        return

    if entity_result.get("created"):
        logger.info("  Created entity: %s (id=%d)", entity_name, entity_result["id"])
        stats.entities_created += 1
    else:
        logger.info("  Found entity: %s (id=%d)", entity_name, entity_result["id"])

    primary_entity = VaultEntity.objects.get(pk=entity_result["id"])

    # 2. Upload document
    try:
        plaintext = Path(source_path).read_bytes()
    except OSError as exc:
        logger.error("  Cannot read file '%s': %s", source_path, exc)
        stats.errors += 1
        return

    original_filename = os.path.basename(source_path)

    _attach_document(
        entity=primary_entity,
        vault_owner=vault_owner,
        document_type_code=document_type_code,
        label=label,
        plaintext=plaintext,
        original_filename=original_filename,
        mime_type=mime_type,
        extracted_data=extracted_data,
        dry_run=dry_run,
        stats=stats,
    )

    # 3. Build relationships from extracted_data — ONLY for legal documents.
    #    Non-legal docs (bank statements, IDs, etc.) may mention directors/trustees
    #    but are not authoritative sources for relationship creation.
    if extracted_data and document_type_code in _LEGAL_DOCUMENT_TYPES:
        _build_relationships(
            extracted_data=extracted_data,
            primary_entity=primary_entity,
            vault_owner=vault_owner,
            document_type_code=document_type_code,
            dry_run=dry_run,
            stats=stats,
        )
    elif extracted_data and document_type_code not in _LEGAL_DOCUMENT_TYPES:
        # Log that we're skipping relationship building for non-legal docs
        rel_keys_present = [k for k, _ in _RELATIONSHIP_MAPS if k in extracted_data]
        if rel_keys_present:
            logger.debug(
                "  Skipping relationship building for non-legal doc type '%s' "
                "(has keys: %s)",
                document_type_code,
                ", ".join(rel_keys_present),
            )

    # 4. Build counterparty entities from transaction documents.
    #    OTPs, transfer statements, rental agreements create seller/buyer/tenant
    #    entities and ownership/tenancy relationship edges.
    if extracted_data and document_type_code in _TRANSACTION_DOCUMENT_TYPES:
        _build_counterparty_entities(
            extracted_data=extracted_data,
            primary_entity=primary_entity,
            vault_owner=vault_owner,
            document_type_code=document_type_code,
            dry_run=dry_run,
            stats=stats,
        )


# ── 11. Manifest loader ───────────────────────────────────────────────────────

def _load_manifest(path: Path) -> list[dict]:
    """Load a JSONL file, returning a list of dicts (bad lines are logged/skipped)."""
    entries: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for i, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as exc:
                logger.warning("  Line %d in %s: JSON parse error — %s", i, path.name, exc)
    return entries


def _collect_manifests(args: argparse.Namespace) -> list[Path]:
    """Resolve the list of manifest files from CLI args."""
    paths: list[Path] = []
    if args.manifest:
        p = Path(args.manifest)
        if not p.is_file():
            logger.error("--manifest file not found: %s", p)
            sys.exit(1)
        paths.append(p)
    if args.manifest_dir:
        d = Path(args.manifest_dir)
        if not d.is_dir():
            logger.error("--manifest-dir is not a directory: %s", d)
            sys.exit(1)
        found = sorted(d.glob("*.jsonl"))
        if not found:
            logger.warning("No .jsonl files found in: %s", d)
        paths.extend(found)
    if not paths:
        logger.error("Provide --manifest or --manifest-dir")
        sys.exit(1)
    return paths


# ── 12. Main ──────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload enriched JSONL manifests into The Volt via Django ORM."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--manifest", metavar="PATH", help="Single JSONL manifest file")
    group.add_argument("--manifest-dir", metavar="PATH", help="Directory of *.jsonl files")
    parser.add_argument(
        "--vault-owner-email",
        required=True,
        metavar="EMAIL",
        help="Email of the Django user whose vault will receive the documents",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate everything but write nothing to the database",
    )
    parser.add_argument(
        "--skip-other",
        action="store_true",
        help="Skip entries with document_type_code='other'",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Resolve vault owner
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user = User.objects.get(email=args.vault_owner_email)
    except User.DoesNotExist:
        logger.error("No user found with email: %s", args.vault_owner_email)
        sys.exit(1)

    vault_owner = VaultOwner.get_or_create_for_user(user)
    logger.info(
        "Vault owner resolved: %s (vault_id=%d)",
        user.email,
        vault_owner.pk,
    )

    # Install script context so _upsert_entity / write_audit work without MCP auth
    ctx = _ScriptContext(vault_owner=vault_owner)
    _install_context(ctx)

    if args.dry_run:
        logger.info("DRY-RUN mode — no writes will be made")

    # Collect manifests
    manifest_paths = _collect_manifests(args)
    logger.info("Manifests to process: %d", len(manifest_paths))

    total_stats = Stats()

    for manifest_path in manifest_paths:
        logger.info("")
        logger.info("=" * 60)
        logger.info("Manifest: %s", manifest_path)
        logger.info("=" * 60)

        entries = _load_manifest(manifest_path)
        if not entries:
            logger.warning("  Empty manifest — skipping")
            continue

        # Sort: identity docs first, then by confidence
        entries.sort(key=_sort_key)
        logger.info("  Entries: %d", len(entries))

        manifest_stats = Stats()
        for i, entry in enumerate(entries, start=1):
            print(
                f"  [{i:>3}/{len(entries)}] "
                f"{entry.get('entity_name', '?')[:40]} | "
                f"{entry.get('document_type_code', '?')}"
            )
            try:
                _process_entry(
                    entry=entry,
                    vault_owner=vault_owner,
                    dry_run=args.dry_run,
                    skip_other=args.skip_other,
                    stats=manifest_stats,
                )
            except Exception as exc:
                logger.exception(
                    "Unexpected error on entry %d of %s: %s", i, manifest_path.name, exc
                )
                manifest_stats.errors += 1

        # Per-manifest summary
        logger.info("")
        logger.info(
            "  Manifest done — entities_created=%d  documents_uploaded=%d  "
            "relationships_created=%d  skipped=%d  errors=%d",
            manifest_stats.entities_created,
            manifest_stats.documents_uploaded,
            manifest_stats.relationships_created,
            manifest_stats.skipped,
            manifest_stats.errors,
        )

        total_stats.entities_created += manifest_stats.entities_created
        total_stats.documents_uploaded += manifest_stats.documents_uploaded
        total_stats.relationships_created += manifest_stats.relationships_created
        total_stats.skipped += manifest_stats.skipped
        total_stats.errors += manifest_stats.errors

    # Final summary
    print("")
    print("=" * 60)
    print("UPLOAD COMPLETE" + (" (DRY-RUN)" if args.dry_run else ""))
    print("=" * 60)
    print(f"  Entities created:        {total_stats.entities_created}")
    print(f"  Documents uploaded:      {total_stats.documents_uploaded}")
    print(f"  Relationships created:   {total_stats.relationships_created}")
    print(f"  Entries skipped:         {total_stats.skipped}")
    print(f"  Errors:                  {total_stats.errors}")
    print("=" * 60)

    if total_stats.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
