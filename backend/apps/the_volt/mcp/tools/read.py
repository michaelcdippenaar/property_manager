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
                "relationship_type": r.relationship_type.code,
                "relationship_type_label": r.relationship_type.label,
                "metadata": r.metadata,
            }
            for r in e.outgoing_relationships.select_related("to_entity", "relationship_type").all()
        ]
        inc = [
            {
                "id": r.pk,
                "from_entity_id": r.from_entity_id,
                "from_entity_name": r.from_entity.name,
                "relationship_type": r.relationship_type.code,
                "relationship_type_label": r.relationship_type.label,
                "metadata": r.metadata,
            }
            for r in e.incoming_relationships.select_related("from_entity", "relationship_type").all()
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
    def list_relationship_types(
        from_entity_type: str | None = None,
        to_entity_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """List all recognised relationship types between vault entities.

        Use this before calling link_entities to pick the correct relationship_type code.
        If the relationship you need doesn't exist, create it via the REST API
        (POST /api/v1/the-volt/relationship-types/) then use its code here.

        Args:
            from_entity_type: Filter to types valid FROM this entity type
                (personal, trust, company, close_corporation, sole_proprietary, asset).
            to_entity_type: Filter to types valid TO this entity type.

        Returns:
            [{code, label, inverse_label, description, valid_from_entity_types,
              valid_to_entity_types, metadata_schema, regulatory_reference, is_system}]
        """
        from apps.the_volt.entities.models import RelationshipTypeCatalogue

        qs = RelationshipTypeCatalogue.objects.filter(is_active=True).order_by("sort_order")
        results = []
        for t in qs:
            if from_entity_type and t.valid_from_entity_types and from_entity_type not in t.valid_from_entity_types:
                continue
            if to_entity_type and t.valid_to_entity_types and to_entity_type not in t.valid_to_entity_types:
                continue
            results.append({
                "code": t.code,
                "label": t.label,
                "inverse_label": t.inverse_label,
                "description": t.description,
                "valid_from_entity_types": t.valid_from_entity_types,
                "valid_to_entity_types": t.valid_to_entity_types,
                "metadata_schema": t.metadata_schema,
                "regulatory_reference": t.regulatory_reference,
                "is_system": t.is_system,
            })
        return results

    @mcp.tool()
    def get_api_schema() -> dict[str, Any]:
        """Return the complete Volt API schema — tools, REST endpoints, entity types,
        document catalogue, and relationship catalogue.

        Use this at the start of a session to orient yourself on what's available,
        what data shapes are expected, and what codes to use for entity_type,
        document_type, and relationship_type arguments in other tools.

        Returns a structured dict with sections:
          - mcp_tools: all MCP tools with their argument signatures
          - rest_endpoints: key REST endpoints and HTTP methods
          - entity_types: DATA_SCHEMAS per entity type
          - document_types: live DocumentTypeCatalogue (code → metadata)
          - relationship_types: live RelationshipTypeCatalogue (code → metadata)
        """
        from apps.the_volt.documents.models import DocumentTypeCatalogue
        from apps.the_volt.entities.models import RelationshipTypeCatalogue, VaultEntity

        # MCP tool catalogue — static, documents the server's own surface
        mcp_tools = {
            "read": {
                "ensure_vault": {
                    "description": "Confirm vault exists. Call first in every session.",
                    "args": {},
                    "returns": "{ vault_id, user_email, api_key_label }",
                },
                "list_entities": {
                    "description": "List entities in the vault.",
                    "args": {"entity_type": "str|None", "include_inactive": "bool=False"},
                    "returns": "[{ id, entity_type, name, is_active, created_at }]",
                },
                "find_entity": {
                    "description": "Search entities by name substring.",
                    "args": {"query": "str", "entity_type": "str|None"},
                    "returns": "[{ id, entity_type, name, data }]",
                },
                "get_entity": {
                    "description": "Full entity record including relationships.",
                    "args": {"entity_id": "int"},
                    "returns": "{ id, entity_type, name, data, relationships_out, relationships_in }",
                },
                "list_documents": {
                    "description": "List document metadata (no file bytes).",
                    "args": {"entity_id": "int|None", "document_type": "str|None"},
                    "returns": "[{ id, entity_id, label, document_type, current_version }]",
                },
                "list_document_types": {
                    "description": "List DocumentTypeCatalogue — what document types the vault recognises.",
                    "args": {"entity_type": "str|None"},
                    "returns": "[{ code, label, issuing_authority, ownership_scope, applies_to_entity_types }]",
                },
                "list_relationship_types": {
                    "description": "List RelationshipTypeCatalogue — valid relationship codes for link_entities.",
                    "args": {"from_entity_type": "str|None", "to_entity_type": "str|None"},
                    "returns": "[{ code, label, inverse_label, description, valid_from_entity_types, valid_to_entity_types, metadata_schema }]",
                },
                "download_document": {
                    "description": "Download + decrypt a document's file bytes as base64.",
                    "args": {"document_id": "int (required)", "version_number": "int|None — omit for latest"},
                    "returns": "{ document_id, version_id, original_filename, mime_type, file_base64 }",
                },
                "get_api_schema": {
                    "description": "This tool. Returns full schema for self-discovery.",
                    "args": {},
                    "returns": "{ mcp_tools, rest_endpoints, entity_types, document_types, relationship_types }",
                },
            },
            "write": {
                "upsert_entity": {
                    "description": "Create/update ANY entity type. Use for company, trust, CC, sole prop.",
                    "args": {
                        "entity_type": "str (required) — personal|trust|company|close_corporation|sole_proprietary|asset",
                        "name": "str (required)",
                        "data": "dict|None — fields per DATA_SCHEMAS[entity_type]",
                    },
                    "returns": "{ id, entity_type, name, data, created }",
                },
                "upsert_owner": {
                    "description": "Create/update the owner's Personal entity. Merges data on update.",
                    "args": {
                        "name": "str (required)",
                        "id_number": "str|None",
                        "date_of_birth": "str|None (YYYY-MM-DD)",
                        "email": "str|None",
                        "phone": "str|None",
                        "address": "str|None",
                        "tax_number": "str|None",
                        "extra_data": "dict|None",
                    },
                    "returns": "{ id, entity_type, name, data, created }",
                },
                "upsert_property": {
                    "description": "Create/update a property Asset entity.",
                    "args": {
                        "name": "str (required)",
                        "address": "str|None",
                        "registration_number": "str|None",
                        "acquisition_date": "str|None",
                        "acquisition_value": "float|None",
                        "current_value": "float|None",
                        "description": "str|None",
                        "extra_data": "dict|None",
                    },
                    "returns": "{ id, entity_type, name, data, created }",
                },
                "upsert_company": {
                    "description": "Create/update a Company entity. Matches on reg_number.",
                    "args": {
                        "name": "str (required)",
                        "reg_number": "str|None — CIPC registration number (identity key)",
                        "vat_number": "str|None",
                        "company_type": "str|None",
                        "registration_date": "str|None (YYYY-MM-DD)",
                        "registered_address": "str|None",
                        "tax_number": "str|None",
                        "financial_year_end": "str|None",
                        "extra_data": "dict|None — directors[], shareholders[]",
                    },
                    "returns": "{ id, entity_type, name, data, created }",
                },
                "upsert_trust": {
                    "description": "Create/update a Trust entity. Matches on trust_number.",
                    "args": {
                        "name": "str (required)",
                        "trust_number": "str|None — Master's Office number (identity key)",
                        "trust_type": "str|None — inter_vivos or testamentary",
                        "master_reference": "str|None",
                        "deed_date": "str|None",
                        "tax_number": "str|None",
                        "extra_data": "dict|None — trustees[], beneficiaries[]",
                    },
                    "returns": "{ id, entity_type, name, data, created }",
                },
                "upsert_close_corporation": {
                    "description": "Create/update a Close Corporation entity. Matches on reg_number.",
                    "args": {
                        "name": "str (required)",
                        "reg_number": "str|None — CK number (identity key)",
                        "vat_number": "str|None",
                        "registered_address": "str|None",
                        "financial_year_end": "str|None",
                        "extra_data": "dict|None — members[], member_interest_pct{}",
                    },
                    "returns": "{ id, entity_type, name, data, created }",
                },
                "upsert_sole_proprietor": {
                    "description": "Create/update a Sole Proprietor entity. Matches on id_number.",
                    "args": {
                        "name": "str (required)",
                        "trade_name": "str|None",
                        "id_number": "str|None (identity key)",
                        "tax_number": "str|None",
                        "vat_number": "str|None",
                        "business_address": "str|None",
                        "extra_data": "dict|None",
                    },
                    "returns": "{ id, entity_type, name, data, created }",
                },
                "upsert_tenant": {
                    "description": "Create/update a tenant Personal entity, optionally linking to a property.",
                    "args": {
                        "name": "str (required)",
                        "id_number": "str|None",
                        "email": "str|None",
                        "phone": "str|None",
                        "leases_property_id": "int|None — creates LEASES_FROM relationship",
                        "extra_data": "dict|None",
                    },
                    "returns": "{ id, entity_type, name, data, created, relationship_id }",
                },
                "link_entities": {
                    "description": "Create/update a directed relationship between two entities. Idempotent.",
                    "args": {
                        "from_entity_id": "int (required)",
                        "to_entity_id": "int (required)",
                        "relationship_type": "str — code from list_relationship_types()",
                        "metadata": "dict|None",
                    },
                    "returns": "{ id, from_entity_id, to_entity_id, relationship_type, metadata, created }",
                    "note": "Call list_relationship_types() first to get valid codes.",
                },
                "update_entity": {
                    "description": "Update entity by ID — bypasses name matching. Merges data.",
                    "args": {
                        "entity_id": "int (required)",
                        "name": "str|None — new display name",
                        "data": "dict|None — fields to merge",
                        "is_active": "bool|None — False to soft-delete",
                    },
                    "returns": "{ id, entity_type, name, data, is_active, updated }",
                },
                "deactivate_entity": {
                    "description": "Soft-delete entity (is_active=False). Reactivate with update_entity.",
                    "args": {"entity_id": "int (required)"},
                    "returns": "{ id, name, is_active, deactivated }",
                },
                "unlink_entities": {
                    "description": "Delete a relationship edge between two entities.",
                    "args": {
                        "from_entity_id": "int (required)",
                        "to_entity_id": "int (required)",
                        "relationship_type": "str (required)",
                    },
                    "returns": "{ deleted, relationship_id }",
                },
                "attach_document": {
                    "description": "Upload + encrypt a document file for an entity.",
                    "args": {
                        "entity_id": "int (required)",
                        "document_type": "str — code from list_document_types()",
                        "label": "str (required)",
                        "file_base64": "str — base64-encoded plaintext file bytes",
                        "original_filename": "str (required)",
                        "mime_type": "str default 'application/octet-stream'",
                        "extracted_data": "dict|None — client OCR output for RAG indexing",
                    },
                    "returns": "{ document_id, version_id, version_number, sha256_hash, file_size_bytes }",
                    "note": "Server never re-extracts — supply extracted_data for RAG indexing.",
                },
            },
        }

        # REST endpoint reference
        rest_endpoints = {
            "base_url": "/api/v1/the-volt/",
            "auth": "JWT (Bearer token) for owner endpoints; X-Volt-API-Key for subscriber endpoints",
            "endpoints": [
                {"path": "vault/me/", "methods": ["GET"], "description": "Get or create the owner's vault"},
                {"path": "entities/", "methods": ["GET", "POST"], "description": "List / create vault entities"},
                {"path": "entities/{id}/", "methods": ["GET", "PUT", "PATCH", "DELETE"], "description": "Get / update / soft-delete entity"},
                {"path": "entities/{id}/relationships/", "methods": ["GET", "POST"], "description": "List or create relationships for an entity"},
                {"path": "entities/query/", "methods": ["POST"], "description": "Hybrid graph+vector query", "body": "{from_entity_id, relationship_types[], query, hops, collection}"},
                {"path": "entities/schemas/", "methods": ["GET"], "description": "DATA_SCHEMAS per entity type"},
                {"path": "relationship-types/", "methods": ["GET", "POST"], "description": "List / create relationship type catalogue entries"},
                {"path": "relationship-types/{id}/", "methods": ["GET", "PUT", "PATCH", "DELETE"], "description": "Manage one relationship type (system types cannot be deleted)"},
                {"path": "documents/", "methods": ["GET", "POST"], "description": "List / create vault document records"},
                {"path": "documents/{id}/versions/", "methods": ["GET", "POST"], "description": "List versions or upload new file (multipart + extracted_data)"},
                {"path": "documents/{id}/versions/{vid}/download/", "methods": ["GET"], "description": "Decrypt and download a document version"},
                {"path": "gateway/request/", "methods": ["POST"], "description": "Subscriber: create a data access request"},
                {"path": "gateway/checkout/", "methods": ["POST"], "description": "Subscriber: checkout approved request data"},
                {"path": "gateway/requests/", "methods": ["GET"], "description": "Owner: list incoming requests"},
                {"path": "gateway/requests/{token}/approve/", "methods": ["POST"], "description": "Owner: approve a request"},
                {"path": "gateway/requests/{token}/deny/", "methods": ["POST"], "description": "Owner: deny a request"},
                {"path": "gateway/requests/{token}/status/", "methods": ["GET"], "description": "Poll request status"},
                {"path": "gateway/requests/{token}/approval-info/", "methods": ["GET"], "description": "Public: fetch request details for approval page"},
                {"path": "gateway/requests/{token}/approve-public/", "methods": ["POST"], "description": "Public: submit OTP + decision"},
            ],
        }

        # Entity type schemas
        entity_types = VaultEntity.DATA_SCHEMAS

        # Live document type catalogue (codes + key metadata)
        document_types = {
            t.code: {
                "label": t.label,
                "issuing_authority": t.issuing_authority,
                "ownership_scope": t.ownership_scope,
                "applies_to_entity_types": t.applies_to_entity_types,
                "default_validity_days": t.default_validity_days,
                "is_primary_identity_doc": t.is_primary_identity_doc,
                "regulatory_reference": t.regulatory_reference,
                "extraction_schema": t.extraction_schema,
            }
            for t in DocumentTypeCatalogue.objects.filter(is_active=True).order_by("sort_order")
        }

        # Live relationship type catalogue
        relationship_types = {
            t.code: {
                "label": t.label,
                "inverse_label": t.inverse_label,
                "description": t.description,
                "valid_from_entity_types": t.valid_from_entity_types,
                "valid_to_entity_types": t.valid_to_entity_types,
                "metadata_schema": t.metadata_schema,
                "regulatory_reference": t.regulatory_reference,
                "is_system": t.is_system,
            }
            for t in RelationshipTypeCatalogue.objects.filter(is_active=True).order_by("sort_order")
        }

        return {
            "mcp_tools": mcp_tools,
            "rest_endpoints": rest_endpoints,
            "entity_types": entity_types,
            "document_types": document_types,
            "relationship_types": relationship_types,
        }

    @mcp.tool()
    def download_document(
        document_id: int,
        version_number: int | None = None,
    ) -> dict[str, Any]:
        """Download and decrypt a document's file bytes.

        Returns the decrypted file as base64 — the inverse of attach_document.
        If version_number is omitted, downloads the current (latest) version.

        Args:
            document_id: VaultDocument primary key.
            version_number: Specific version to download. Omit for latest.

        Returns:
            {document_id, version_id, version_number, original_filename, mime_type,
             file_size_bytes, sha256_hash, file_base64} or {error}.
        """
        import base64

        from apps.the_volt.documents.models import DocumentVersion, VaultDocument
        from apps.the_volt.encryption.utils import decrypt_bytes

        ctx = get_context()
        try:
            doc = VaultDocument.objects.get(pk=document_id, entity__vault=ctx.vault_owner)
        except VaultDocument.DoesNotExist:
            return {"error": "Document not found in this vault", "document_id": document_id}

        if version_number is not None:
            try:
                version = doc.versions.get(version_number=version_number)
            except DocumentVersion.DoesNotExist:
                return {"error": f"Version {version_number} not found", "document_id": document_id}
        else:
            version = doc.current_version
            if version is None:
                return {"error": "Document has no versions", "document_id": document_id}

        try:
            encrypted = version.file.read()
            plaintext = decrypt_bytes(encrypted, ctx.vault_owner.pk)
        except Exception as exc:
            return {"error": f"Failed to decrypt: {exc}"}

        return {
            "document_id": doc.pk,
            "version_id": version.pk,
            "version_number": version.version_number,
            "original_filename": version.original_filename,
            "mime_type": version.mime_type,
            "file_size_bytes": version.file_size_bytes,
            "sha256_hash": version.sha256_hash,
            "file_base64": base64.b64encode(plaintext).decode("ascii"),
        }

    @mcp.tool()
    def list_document_types(entity_type: str | None = None) -> list[dict[str, Any]]:
        """List document types the vault recognises — including what to extract from each.

        Call this BEFORE attach_document to know:
          1. The correct document_type code to use
          2. Exactly which fields to extract into extracted_data (extraction_schema)
          3. Whether the document travels with the asset on sale (ownership_scope)

        Args:
            entity_type: Filter to types for this entity type
                (personal, trust, company, close_corporation, sole_proprietary, asset).

        Returns:
            List of document type descriptors. Key fields:
              code                    — use as document_type in attach_document()
              label                   — human name
              issuing_authority       — who issues this document
              ownership_scope         — asset_bound (travels on sale) | owner_bound | shared
              default_validity_days   — None means no expiry
              extraction_schema       — dict of fields to extract: {field_key: {type, label, required}}
              classification_signals  — text hints to identify this document from email/file content
        """
        from apps.the_volt.documents.models import DocumentTypeCatalogue

        qs = DocumentTypeCatalogue.objects.filter(is_active=True).order_by("sort_order")
        results = []
        for t in qs:
            if entity_type and entity_type not in (t.applies_to_entity_types or []):
                continue
            results.append({
                "code": t.code,
                "label": t.label,
                "issuing_authority": t.issuing_authority,
                "ownership_scope": t.ownership_scope,
                "applies_to_entity_types": t.applies_to_entity_types,
                "default_validity_days": t.default_validity_days,
                "regulatory_reference": t.regulatory_reference,
                "extraction_schema": t.extraction_schema,
                "classification_signals": t.classification_signals,
                "email_sender_patterns": t.email_sender_patterns,
                "email_subject_patterns": t.email_subject_patterns,
            })
        return results

    @mcp.tool()
    def get_document_type(code: str) -> dict[str, Any] | None:
        """Get full detail for a single document type by code.

        Use this when you have identified a document type and need the complete
        extraction guide before calling attach_document().

        Args:
            code: Document type code, e.g. 'title_deed', 'sa_id_document',
                  'trust_deed'. Get codes from list_document_types().

        Returns:
            Full catalogue entry including extraction_schema, classification_signals,
            email patterns, and upload instructions. None if code not found.

            The extraction_schema tells you exactly what to put in extracted_data:
              {
                "field_key": {
                  "type": "string|date|decimal|boolean|list|dict|integer|text",
                  "label": "Human label",
                  "required": true|false
                }
              }

            Upload checklist:
              1. Identify document type → confirm with classification_signals
              2. Extract all required fields (required=true) from the document
              3. Extract optional fields where visible
              4. Call attach_document(
                     entity_id=...,
                     document_type=<this code>,
                     label="<entity name>'s <document label>",
                     file_base64=<base64 encoded file>,
                     original_filename=<filename with extension>,
                     mime_type=<e.g. "application/pdf">,
                     extracted_data=<dict matching extraction_schema>
                 )
        """
        from apps.the_volt.documents.models import DocumentTypeCatalogue

        try:
            t = DocumentTypeCatalogue.objects.get(code=code, is_active=True)
        except DocumentTypeCatalogue.DoesNotExist:
            return None

        return {
            "code": t.code,
            "label": t.label,
            "issuing_authority": t.issuing_authority,
            "ownership_scope": t.ownership_scope,
            "applies_to_entity_types": t.applies_to_entity_types,
            "default_validity_days": t.default_validity_days,
            "regulatory_reference": t.regulatory_reference,
            "external_reference_codes": t.external_reference_codes,
            "is_primary_identity_doc": t.is_primary_identity_doc,
            "extraction_schema": t.extraction_schema,
            "classification_signals": t.classification_signals,
            "email_sender_patterns": t.email_sender_patterns,
            "email_subject_patterns": t.email_subject_patterns,
            "upload_instructions": (
                f"1. Confirm this is a '{t.label}' using classification_signals above.\n"
                f"2. Extract all required fields from extraction_schema (required=true).\n"
                f"3. Extract optional fields where visible in the document.\n"
                f"4. Call attach_document() with document_type='{t.code}' and "
                f"extracted_data matching the schema keys.\n"
                + (
                    f"5. Note: this document is {t.ownership_scope.replace('_', ' ')} — "
                    + ("it transfers with the asset on sale." if t.ownership_scope == "asset_bound"
                       else "it stays with the owner on asset sale.")
                    if t.ownership_scope != "shared" else
                    "5. Note: this is a shared document — both parties retain their own copy."
                )
            ),
        }
