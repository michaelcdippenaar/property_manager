"""
Volt MCP — read tools.

All reads scoped to the calling owner's vault. No external consent flow is
triggered here: the owner is reading their own data. Reads do NOT write a
VaultWriteAudit row (that model tracks mutations). External-subscriber reads
go through the gateway and produce DataCheckout records instead.
"""
from __future__ import annotations

from typing import Any

from ..auth import get_context


def register(mcp) -> None:
    @mcp.tool()
    def list_entities(entity_type: str | None = None, include_inactive: bool = False) -> list[dict[str, Any]]:
        """List entities in the owner's vault.

        Args:
            entity_type: Filter by type. One of: personal, trust, company,
                close_corporation, sole_proprietary, asset. Omit for all.
            include_inactive: Include is_active=False rows. Defaults to False.

        Returns:
            List of {id, entity_type, name, is_active, created_at} dicts.
        """
        from apps.the_volt.entities.models import VaultEntity

        ctx = get_context()
        qs = VaultEntity.objects.filter(vault=ctx.vault_owner)
        if entity_type:
            qs = qs.filter(entity_type=entity_type)
        if not include_inactive:
            qs = qs.filter(is_active=True)
        return [
            {
                "id": e.pk,
                "entity_type": e.entity_type,
                "name": e.name,
                "is_active": e.is_active,
                "created_at": e.created_at.isoformat(),
            }
            for e in qs
        ]

    @mcp.tool()
    def find_entity(query: str, entity_type: str | None = None) -> list[dict[str, Any]]:
        """Search entities by name (case-insensitive substring match).

        Args:
            query: Substring of the entity name to find.
            entity_type: Optional type filter.

        Returns:
            Up to 25 matches with {id, entity_type, name, data} payloads.
        """
        from apps.the_volt.entities.models import VaultEntity

        ctx = get_context()
        qs = VaultEntity.objects.filter(
            vault=ctx.vault_owner,
            is_active=True,
            name__icontains=query,
        )
        if entity_type:
            qs = qs.filter(entity_type=entity_type)
        return [
            {"id": e.pk, "entity_type": e.entity_type, "name": e.name, "data": e.data}
            for e in qs[:25]
        ]

    @mcp.tool()
    def get_entity(entity_id: int) -> dict[str, Any] | None:
        """Fetch a single entity's full record including data payload and relationships.

        Args:
            entity_id: VaultEntity primary key.

        Returns:
            {id, entity_type, name, data, relationships_out, relationships_in}
            or None if the entity is not in this owner's vault.
        """
        from apps.the_volt.entities.models import VaultEntity

        ctx = get_context()
        try:
            e = VaultEntity.objects.get(pk=entity_id, vault=ctx.vault_owner)
        except VaultEntity.DoesNotExist:
            return None

        out = [
            {
                "id": r.pk,
                "to_entity_id": r.to_entity_id,
                "to_entity_name": r.to_entity.name,
                "relationship_type": r.relationship_type,
                "metadata": r.metadata,
            }
            for r in e.outgoing_relationships.select_related("to_entity").all()
        ]
        inc = [
            {
                "id": r.pk,
                "from_entity_id": r.from_entity_id,
                "from_entity_name": r.from_entity.name,
                "relationship_type": r.relationship_type,
                "metadata": r.metadata,
            }
            for r in e.incoming_relationships.select_related("from_entity").all()
        ]
        return {
            "id": e.pk,
            "entity_type": e.entity_type,
            "name": e.name,
            "data": e.data,
            "is_active": e.is_active,
            "created_at": e.created_at.isoformat(),
            "relationships_out": out,
            "relationships_in": inc,
        }

    @mcp.tool()
    def list_documents(entity_id: int | None = None, document_type: str | None = None) -> list[dict[str, Any]]:
        """List document metadata (no file bytes) for the owner's vault.

        Args:
            entity_id: Restrict to one entity. Omit for whole vault.
            document_type: Filter by document type code.

        Returns:
            List of {id, entity_id, label, document_type, current_version} dicts.
        """
        from apps.the_volt.documents.models import VaultDocument

        ctx = get_context()
        qs = VaultDocument.objects.filter(entity__vault=ctx.vault_owner).select_related("current_version")
        if entity_id is not None:
            qs = qs.filter(entity_id=entity_id)
        if document_type:
            qs = qs.filter(document_type=document_type)
        return [
            {
                "id": d.pk,
                "entity_id": d.entity_id,
                "label": d.label,
                "document_type": d.document_type,
                "current_version": (
                    {
                        "id": d.current_version.pk,
                        "version_number": d.current_version.version_number,
                        "uploaded_at": d.current_version.uploaded_at.isoformat(),
                        "sha256_hash": d.current_version.sha256_hash,
                    }
                    if d.current_version else None
                ),
                "created_at": d.created_at.isoformat(),
            }
            for d in qs
        ]

    @mcp.tool()
    def list_document_types(entity_type: str | None = None) -> list[dict[str, Any]]:
        """List the DocumentTypeCatalogue — what document types the vault recognises.

        Args:
            entity_type: Filter to types that apply to this entity type.

        Returns:
            [{code, label, issuing_authority, ownership_scope, applies_to_entity_types}]
        """
        from apps.the_volt.documents.models import DocumentTypeCatalogue

        qs = DocumentTypeCatalogue.objects.filter(is_active=True)
        results = []
        for t in qs:
            if entity_type and entity_type not in (t.applies_to_entity_types or []):
                continue
            results.append(
                {
                    "code": t.code,
                    "label": t.label,
                    "issuing_authority": t.issuing_authority,
                    "ownership_scope": t.ownership_scope,
                    "applies_to_entity_types": t.applies_to_entity_types,
                    "regulatory_reference": t.regulatory_reference,
                }
            )
        return results
