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
        from apps.the_volt.entities.models import EntityRelationship, VaultEntity

        ctx = get_context()

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
                relationship_type=relationship_type,
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
            "relationship_type": relationship_type,
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
    """Shared body for upsert_owner / upsert_property / upsert_tenant."""
    from apps.the_volt.entities.models import VaultEntity

    ctx = get_context()
    clean_fields = {k: v for k, v in fields.items() if v is not None}

    with transaction.atomic():
        entity, created = VaultEntity.objects.get_or_create(
            vault=ctx.vault_owner,
            entity_type=entity_type,
            name=name,
            defaults={"data": clean_fields},
        )
        before = {}
        if not created:
            before = {"data": dict(entity.data)}
            merged = {**(entity.data or {}), **clean_fields}
            entity.data = merged
            entity.save(update_fields=["data", "updated_at"])

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
