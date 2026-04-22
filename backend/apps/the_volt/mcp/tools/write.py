"""
Volt MCP — write tools.

Mutations against the owner's vault. Every tool writes a VaultWriteAudit row.
File uploads encrypt plaintext bytes using the owner's Fernet key before
writing them to disk — the MCP tool never stores plaintext at rest.
"""
from __future__ import annotations

import base64
import hashlib
import logging
from io import BytesIO
from typing import Any

from django.core.files.base import ContentFile
from django.db import transaction

from ..audit import write_audit
from ..auth import get_context

logger = logging.getLogger(__name__)


def _snapshot_entity(e) -> dict[str, Any]:
    return {
        "id": e.pk,
        "entity_type": e.entity_type,
        "name": e.name,
        "data": e.data,
        "is_active": e.is_active,
    }


def register(mcp) -> None:
    # ───────────────────────────────── ensure_vault ─────────────────────────────────
    @mcp.tool()
    def ensure_vault() -> dict[str, Any]:
        """Confirm the owner's vault exists and return its id + user email.

        No-op if already present. Safe to call at the start of every CoWork session.
        """
        ctx = get_context()
        return {
            "vault_id": ctx.vault_id,
            "user_email": ctx.user_email,
            "api_key_label": ctx.api_key.label,
        }

    # ───────────────────────────────── upsert_entity (generic) ────────────────────
    @mcp.tool()
    def upsert_entity(
        entity_type: str,
        name: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create or update ANY vault entity — generic tool for all 6 entity types.

        Use this for company, trust, close_corporation, sole_proprietary entities
        (or personal/asset if you don't need the convenience args of the specialised tools).

        Matches on (entity_type + name). Second call with same name MERGES the data dict.

        Args:
            entity_type: One of: personal, trust, company, close_corporation,
                sole_proprietary, asset.
            name: Display name of the entity.
            data: Structured fields per DATA_SCHEMAS[entity_type]. Key fields:
                - company: {reg_number, vat_number, company_type, directors[], shareholders[]}
                - trust: {trust_number, trust_type, trustees[], beneficiaries[], deed_date}
                - close_corporation: {reg_number, members[], member_interest_pct{}}
                - sole_proprietary: {trade_name, id_number, tax_number, vat_number}
                - personal: {id_number, date_of_birth, email, phone, address}
                - asset: {asset_type, address, registration_number}

        Returns:
            {id, entity_type, name, data, created}
        """
        from apps.the_volt.entities.models import VaultEntity

        valid_types = [t[0] for t in VaultEntity.EntityType.choices]
        if entity_type not in valid_types:
            return {"error": f"Invalid entity_type '{entity_type}'. Must be one of: {valid_types}"}

        return _upsert_entity(
            entity_type=entity_type,
            name=name,
            fields=data or {},
            op="upsert_entity",
        )

    # ───────────────────────────────── upsert_owner ─────────────────────────────────
    @mcp.tool()
    def upsert_owner(
        name: str,
        id_number: str | None = None,
        date_of_birth: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        address: str | None = None,
        tax_number: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create or update the owner's own Personal entity.

        Matches on entity_type='personal' + name. Only one call needed to bootstrap
        the vault. Later calls with the same name MERGE the data dict — existing
        keys are preserved unless overwritten.

        Args:
            name: Full legal name of the person.
            id_number: SA ID or passport number.
            date_of_birth: ISO date "YYYY-MM-DD".
            email, phone, address, tax_number: optional.
            extra_data: Additional fields per VaultEntity.DATA_SCHEMAS['personal'].

        Returns:
            {id, entity_type, name, data, created}
        """
        return _upsert_entity(
            entity_type="personal",
            name=name,
            fields={
                "id_number": id_number,
                "date_of_birth": date_of_birth,
                "email": email,
                "phone": phone,
                "address": address,
                "tax_number": tax_number,
                **(extra_data or {}),
            },
            op="upsert_owner",
        )

    # ───────────────────────────────── upsert_property ──────────────────────────────
    @mcp.tool()
    def upsert_property(
        name: str,
        address: str | None = None,
        registration_number: str | None = None,
        acquisition_date: str | None = None,
        acquisition_value: float | None = None,
        current_value: float | None = None,
        description: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create or update a property Asset entity.

        Args:
            name: Display name, e.g. "12 Dorp Street, Stellenbosch".
            address: Full physical address.
            registration_number: Title deed number or ERF number.
            acquisition_date, acquisition_value, current_value: optional metadata.
            description: Free text.
            extra_data: Additional fields per DATA_SCHEMAS['asset'].

        Returns:
            {id, entity_type, name, data, created}
        """
        return _upsert_entity(
            entity_type="asset",
            name=name,
            fields={
                "asset_type": "property",
                "address": address,
                "registration_number": registration_number,
                "acquisition_date": acquisition_date,
                "acquisition_value": acquisition_value,
                "current_value": current_value,
                "description": description,
                **(extra_data or {}),
            },
            op="upsert_property",
        )

    # ───────────────────────────────── upsert_tenant ────────────────────────────────
    @mcp.tool()
    def upsert_tenant(
        name: str,
        id_number: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        leases_property_id: int | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create or update a tenant as a Personal entity, optionally linking them
        to a property they lease FROM.

        Args:
            name: Tenant full name.
            id_number, email, phone: optional.
            leases_property_id: If given, creates an EntityRelationship
                (tenant) -[LEASES_FROM]-> (property).
            extra_data: Additional fields.

        Returns:
            {id, entity_type, name, data, created, relationship_id}
        """
        result = _upsert_entity(
            entity_type="personal",
            name=name,
            fields={
                "id_number": id_number,
                "email": email,
                "phone": phone,
                **(extra_data or {}),
            },
            op="upsert_tenant",
        )

        if leases_property_id:
            rel = link_entities(  # type: ignore  # nested tool call — local fn below
                from_entity_id=result["id"],
                to_entity_id=leases_property_id,
                relationship_type="leases_from",
            )
            result["relationship_id"] = rel.get("id")
        return result

    # ───────────────────────────────── upsert_company ────────────────────────────────
    @mcp.tool()
    def upsert_company(
        name: str,
        reg_number: str | None = None,
        vat_number: str | None = None,
        company_type: str | None = None,
        registration_date: str | None = None,
        registered_address: str | None = None,
        tax_number: str | None = None,
        financial_year_end: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create or update a Company entity.

        Matches on reg_number first (identity key), then falls back to name.
        Later calls with the same reg_number MERGE the data dict.

        Args:
            name: Company name, e.g. "LucaNaude (Pty) Ltd".
            reg_number: CIPC registration number, e.g. "2025/693002/07".
            vat_number: VAT registration number.
            company_type: e.g. "private", "public", "non-profit".
            registration_date: ISO date "YYYY-MM-DD".
            registered_address: Full registered address.
            tax_number: SARS income tax number.
            financial_year_end: e.g. "February" or "2026-02-28".
            extra_data: Additional fields — directors (list), shareholders (list),
                or any other DATA_SCHEMAS['company'] fields.

        Returns:
            {id, entity_type, name, data, created}
        """
        return _upsert_entity(
            entity_type="company",
            name=name,
            fields={
                "reg_number": reg_number,
                "vat_number": vat_number,
                "company_type": company_type,
                "registration_date": registration_date,
                "registered_address": registered_address,
                "tax_number": tax_number,
                "financial_year_end": financial_year_end,
                **(extra_data or {}),
            },
            op="upsert_company",
        )

    # ───────────────────────────────── upsert_trust ────────────────────────────────
    @mcp.tool()
    def upsert_trust(
        name: str,
        trust_number: str | None = None,
        trust_type: str | None = None,
        master_reference: str | None = None,
        deed_date: str | None = None,
        tax_number: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create or update a Trust entity.

        Matches on trust_number first (identity key), then falls back to name.
        Later calls with the same trust_number MERGE the data dict.

        Args:
            name: Trust name, e.g. "Naude Dippenaar Trust".
            trust_number: Master's Office number, e.g. "IT001973/2025".
            trust_type: "inter_vivos" or "testamentary".
            master_reference: URN from Master of the High Court.
            deed_date: ISO date the trust deed was signed.
            tax_number: SARS income tax number for the trust.
            extra_data: Additional fields — trustees (list), beneficiaries (list),
                or any other DATA_SCHEMAS['trust'] fields.

        Returns:
            {id, entity_type, name, data, created}
        """
        return _upsert_entity(
            entity_type="trust",
            name=name,
            fields={
                "trust_name": name,
                "trust_number": trust_number,
                "trust_type": trust_type,
                "master_reference": master_reference,
                "deed_date": deed_date,
                "tax_number": tax_number,
                **(extra_data or {}),
            },
            op="upsert_trust",
        )

    # ───────────────────────────────── upsert_close_corporation ─────────────────────
    @mcp.tool()
    def upsert_close_corporation(
        name: str,
        reg_number: str | None = None,
        vat_number: str | None = None,
        registered_address: str | None = None,
        financial_year_end: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create or update a Close Corporation entity.

        Matches on reg_number first (identity key), then falls back to name.

        Args:
            name: CC name, e.g. "Smith Plumbing CC".
            reg_number: CK registration number, e.g. "CK1999/012345/23".
            vat_number: VAT registration number.
            registered_address: Full registered address.
            financial_year_end: e.g. "February" or "2026-02-28".
            extra_data: Additional fields — members (list),
                member_interest_pct (dict), or other DATA_SCHEMAS['close_corporation'] fields.

        Returns:
            {id, entity_type, name, data, created}
        """
        return _upsert_entity(
            entity_type="close_corporation",
            name=name,
            fields={
                "reg_number": reg_number,
                "vat_number": vat_number,
                "registered_address": registered_address,
                "financial_year_end": financial_year_end,
                **(extra_data or {}),
            },
            op="upsert_close_corporation",
        )

    # ───────────────────────────────── upsert_sole_proprietor ──────────────────────
    @mcp.tool()
    def upsert_sole_proprietor(
        name: str,
        trade_name: str | None = None,
        id_number: str | None = None,
        tax_number: str | None = None,
        vat_number: str | None = None,
        business_address: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create or update a Sole Proprietor entity.

        Matches on id_number first (identity key), then falls back to name.

        Args:
            name: Owner's full name (also the entity display name).
            trade_name: Trading-as name if different from owner name.
            id_number: SA ID number of the sole proprietor.
            tax_number: SARS income tax number.
            vat_number: VAT registration number.
            business_address: Physical business address.
            extra_data: Additional fields — fic_registered (boolean),
                or other DATA_SCHEMAS['sole_proprietary'] fields.

        Returns:
            {id, entity_type, name, data, created}
        """
        return _upsert_entity(
            entity_type="sole_proprietary",
            name=name,
            fields={
                "owner_name": name,
                "trade_name": trade_name,
                "id_number": id_number,
                "tax_number": tax_number,
                "vat_number": vat_number,
                "business_address": business_address,
                **(extra_data or {}),
            },
            op="upsert_sole_proprietor",
        )

    # ───────────────────────────────── update_entity ───────────────────────────────
    @mcp.tool()
    def update_entity(
        entity_id: int,
        name: str | None = None,
        data: dict[str, Any] | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any]:
        """Update an existing entity by its ID — bypasses name matching.

        Use this when you know the exact entity ID and want to update its name,
        merge additional data fields, or soft-delete it. Safer than upsert when
        you want to avoid accidental creation of a new entity.

        Args:
            entity_id: VaultEntity primary key.
            name: New display name (if changing). None = keep current.
            data: Fields to merge into the existing data dict. Existing keys
                are preserved unless overwritten. None = no data changes.
            is_active: Set to False to soft-delete, True to reactivate. None = no change.

        Returns:
            {id, entity_type, name, data, is_active, updated} or {error}.
        """
        from apps.the_volt.entities.models import VaultEntity

        ctx = get_context()
        try:
            entity = VaultEntity.objects.get(pk=entity_id, vault=ctx.vault_owner)
        except VaultEntity.DoesNotExist:
            return {"error": "Entity not found in this vault", "entity_id": entity_id}

        before = _snapshot_entity(entity)
        update_fields = ["updated_at"]

        with transaction.atomic():
            if name is not None and name != entity.name:
                entity.name = name
                update_fields.append("name")

            if data is not None:
                entity.data = {**(entity.data or {}), **data}
                update_fields.append("data")

            if is_active is not None and is_active != entity.is_active:
                entity.is_active = is_active
                update_fields.append("is_active")

            if len(update_fields) > 1:  # more than just updated_at
                entity.save(update_fields=update_fields)

        after = _snapshot_entity(entity)

        write_audit(
            ctx,
            operation="update_entity",
            target_model="VaultEntity",
            target_id=entity.pk,
            before=before,
            after=after,
            tool_name="update_entity",
        )

        return {
            "id": entity.pk,
            "entity_type": entity.entity_type,
            "name": entity.name,
            "data": entity.data,
            "is_active": entity.is_active,
            "updated": len(update_fields) > 1,
        }

    # ───────────────────────────────── deactivate_entity ───────────────────────────
    @mcp.tool()
    def deactivate_entity(entity_id: int) -> dict[str, Any]:
        """Soft-delete an entity by setting is_active=False.

        The entity is hidden from list_entities and find_entity by default,
        but can still be retrieved with get_entity or list_entities(include_inactive=True).
        Relationships are preserved. Use update_entity(is_active=True) to reactivate.

        Args:
            entity_id: VaultEntity primary key.

        Returns:
            {id, name, is_active, deactivated} or {error}.
        """
        result = update_entity(entity_id=entity_id, is_active=False)
        if "error" in result:
            return result
        return {
            "id": result["id"],
            "name": result["name"],
            "is_active": result["is_active"],
            "deactivated": True,
        }

    # ───────────────────────────────── unlink_entities ─────────────────────────────
    @mcp.tool()
    def unlink_entities(
        from_entity_id: int,
        to_entity_id: int,
        relationship_type: str,
    ) -> dict[str, Any]:
        """Delete a relationship edge between two entities.

        Args:
            from_entity_id, to_entity_id: VaultEntity PKs.
            relationship_type: The relationship type code to remove.

        Returns:
            {deleted: True} or {error}.
        """
        from apps.the_volt.entities.models import EntityRelationship, RelationshipTypeCatalogue, VaultEntity

        ctx = get_context()

        try:
            rel_type = RelationshipTypeCatalogue.objects.get(code=relationship_type, is_active=True)
        except RelationshipTypeCatalogue.DoesNotExist:
            return {"error": f"Unknown relationship_type '{relationship_type}'."}

        # Verify both entities belong to this vault
        vault_entity_ids = set(
            VaultEntity.objects.filter(
                pk__in=[from_entity_id, to_entity_id], vault=ctx.vault_owner
            ).values_list("pk", flat=True)
        )
        if from_entity_id not in vault_entity_ids or to_entity_id not in vault_entity_ids:
            return {"error": "One or both entities not found in this vault."}

        try:
            rel = EntityRelationship.objects.get(
                from_entity_id=from_entity_id,
                to_entity_id=to_entity_id,
                relationship_type=rel_type,
            )
        except EntityRelationship.DoesNotExist:
            return {"error": "Relationship not found."}

        rel_id = rel.pk
        before = {
            "from_entity_id": from_entity_id,
            "to_entity_id": to_entity_id,
            "relationship_type": relationship_type,
            "metadata": rel.metadata,
        }
        rel.delete()

        write_audit(
            ctx,
            operation="unlink_entities",
            target_model="EntityRelationship",
            target_id=rel_id,
            before=before,
            after={},
            tool_name="unlink_entities",
        )

        return {"deleted": True, "relationship_id": rel_id}

    # ───────────────────────────────── link_entities ────────────────────────────────
    @mcp.tool()
    def link_entities(
        from_entity_id: int,
        to_entity_id: int,
        relationship_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a directed relationship edge between two entities in the vault.

        Idempotent: calling with the same (from, to, relationship_type) triple
        updates the metadata instead of creating a duplicate.

        Args:
            from_entity_id, to_entity_id: VaultEntity PKs. Both must belong to
                this vault.
            relationship_type: One of the RelationshipType codes — e.g.
                'director_of', 'trustee_of', 'shareholder_of', 'holds_asset',
                'beneficial_owner_of', 'member_of', 'operates_as', 'guarantor_for',
                'leases_from', 'parent_of'.
            metadata: Optional dict (e.g. {share_pct: 25, effective_date: ...}).

        Returns:
            {id, from_entity_id, to_entity_id, relationship_type, metadata, created}
        """
        from apps.the_volt.entities.models import EntityRelationship, RelationshipTypeCatalogue, VaultEntity

        ctx = get_context()

        # Resolve relationship type code → catalogue entry
        try:
            rel_type = RelationshipTypeCatalogue.objects.get(code=relationship_type, is_active=True)
        except RelationshipTypeCatalogue.DoesNotExist:
            return {
                "error": (
                    f"Unknown relationship_type '{relationship_type}'. "
                    "Call list_relationship_types() to see valid codes, or create a new type "
                    "via POST /api/v1/the-volt/relationship-types/ first."
                )
            }

        # Both must be in this vault
        entities = {
            e.pk: e
            for e in VaultEntity.objects.filter(
                pk__in=[from_entity_id, to_entity_id], vault=ctx.vault_owner
            )
        }
        if from_entity_id not in entities or to_entity_id not in entities:
            return {
                "error": "One or both entities not found in this vault",
                "from_entity_id": from_entity_id,
                "to_entity_id": to_entity_id,
            }

        with transaction.atomic():
            rel, created = EntityRelationship.objects.update_or_create(
                from_entity_id=from_entity_id,
                to_entity_id=to_entity_id,
                relationship_type=rel_type,
                defaults={"vault": ctx.vault_owner, "metadata": metadata or {}},
            )

        write_audit(
            ctx,
            operation="link_entities",
            target_model="EntityRelationship",
            target_id=rel.pk,
            before={} if created else {"metadata": rel.metadata},
            after={
                "from_entity_id": from_entity_id,
                "to_entity_id": to_entity_id,
                "relationship_type": relationship_type,
                "metadata": metadata or {},
            },
            tool_name="link_entities",
        )

        return {
            "id": rel.pk,
            "from_entity_id": from_entity_id,
            "to_entity_id": to_entity_id,
            "relationship_type": rel_type.code,
            "relationship_type_label": rel_type.label,
            "metadata": rel.metadata,
            "created": created,
        }

    # ───────────────────────────────── attach_document ──────────────────────────────
    @mcp.tool()
    def attach_document(
        entity_id: int,
        document_type: str,
        label: str,
        file_base64: str,
        original_filename: str,
        mime_type: str = "application/octet-stream",
        extracted_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Upload a document for an entity. Creates a new VaultDocument (if
        (entity, document_type, label) doesn't exist yet) and appends a fresh
        DocumentVersion. File bytes are Fernet-encrypted at rest using the
        owner's key.

        Args:
            entity_id: VaultEntity PK.
            document_type: Code matching DocumentType or DocumentTypeCatalogue.code
                (e.g. 'id_document', 'cipc_certificate', 'title_deed').
            label: Human label for this document, e.g. "John's SA ID".
            file_base64: Raw file plaintext, base64-encoded.
            original_filename: Original filename, e.g. "john_id.pdf".
            mime_type: MIME type, e.g. "application/pdf".
            extracted_data: Optional client-side OCR output — stored on the
                DocumentVersion for RAG indexing.

        Returns:
            {document_id, version_id, version_number, sha256_hash}
        """
        from apps.the_volt.documents.models import DocumentVersion, VaultDocument
        from apps.the_volt.encryption.utils import encrypt_bytes
        from apps.the_volt.entities.models import VaultEntity

        ctx = get_context()
        try:
            entity = VaultEntity.objects.get(pk=entity_id, vault=ctx.vault_owner)
        except VaultEntity.DoesNotExist:
            return {"error": "Entity not found in this vault", "entity_id": entity_id}

        try:
            plaintext = base64.b64decode(file_base64, validate=True)
        except Exception as exc:
            return {"error": f"file_base64 is not valid base64: {exc}"}

        sha256_hash = hashlib.sha256(plaintext).hexdigest()
        file_size = len(plaintext)
        encrypted = encrypt_bytes(plaintext, ctx.vault_owner.pk)

        with transaction.atomic():
            doc, doc_created = VaultDocument.objects.get_or_create(
                entity=entity,
                document_type=document_type,
                label=label,
            )
            version = DocumentVersion(
                document=doc,
                original_filename=original_filename,
                file_size_bytes=file_size,
                sha256_hash=sha256_hash,
                mime_type=mime_type,
                extracted_data=extracted_data or {},
            )
            # DocumentVersion.save() auto-increments version_number
            version.save()
            version.file.save(
                f"{version.version_number}.enc",
                ContentFile(encrypted),
                save=True,
            )
            doc.current_version = version
            doc.save(update_fields=["current_version", "updated_at"])

        write_audit(
            ctx,
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
            },
            tool_name="attach_document",
        )

        return {
            "document_id": doc.pk,
            "version_id": version.pk,
            "version_number": version.version_number,
            "sha256_hash": sha256_hash,
            "file_size_bytes": file_size,
            "document_created": doc_created,
        }


# ──────────────────────────────── internal helpers ──────────────────────────────


def _upsert_entity(entity_type: str, name: str, fields: dict[str, Any], op: str) -> dict[str, Any]:
    """Shared body for upsert_owner / upsert_property / upsert_tenant / upsert_entity.

    Identity-key matching strategy (prevents duplicates from name variations):
      1. If an identity key is present in `fields`, try to find an existing entity
         by that key first (e.g. id_number for personal, reg_number for company).
      2. Fall back to (entity_type + name) matching if no identity key is provided
         or no identity-key match is found.
      3. On match, MERGE the data dict — existing keys preserved unless overwritten.
         Name is updated to the latest value (handles "MC Dippenaar" → "Michael Christiaan Dippenaar").
    """
    from apps.the_volt.entities.models import VaultEntity

    ctx = get_context()
    clean_fields = {k: v for k, v in fields.items() if v is not None}

    # Identity key per entity type — the field in `data` that uniquely identifies
    IDENTITY_KEYS = {
        "personal": "id_number",
        "company": "reg_number",
        "trust": "trust_number",
        "close_corporation": "reg_number",
        "sole_proprietary": "id_number",
        "asset": "registration_number",
    }

    identity_key = IDENTITY_KEYS.get(entity_type)
    identity_value = clean_fields.get(identity_key) if identity_key else None

    with transaction.atomic():
        entity = None
        created = False

        # Pass 1: try identity-key lookup (most reliable)
        if identity_value:
            entity = (
                VaultEntity.objects
                .filter(vault=ctx.vault_owner, entity_type=entity_type)
                .extra(where=[f"data->>'{identity_key}' = %s"], params=[str(identity_value)])
                .first()
            )

        # Pass 2: fall back to name match
        if entity is None:
            entity, created = VaultEntity.objects.get_or_create(
                vault=ctx.vault_owner,
                entity_type=entity_type,
                name=name,
                defaults={"data": clean_fields},
            )

        if not created:
            before = {"data": dict(entity.data)}
            merged = {**(entity.data or {}), **clean_fields}
            entity.data = merged
            # Update name to latest (handles variations: "MC Dippenaar" → full legal name)
            if entity.name != name:
                entity.name = name
                entity.save(update_fields=["data", "name", "updated_at"])
            else:
                entity.save(update_fields=["data", "updated_at"])
        else:
            before = {}

    write_audit(
        ctx,
        operation=op,
        target_model="VaultEntity",
        target_id=entity.pk,
        before=before,
        after={"data": entity.data, "entity_type": entity_type, "name": name},
        tool_name=op,
    )

    return {
        "id": entity.pk,
        "entity_type": entity.entity_type,
        "name": entity.name,
        "data": entity.data,
        "created": created,
    }
