"""
InternalGatewayService — lightweight vault data fetcher for internal app modules.

Used by the existing app modules (leases, tenant, maintenance, etc.) to fetch
vault data without triggering the full owner-approval flow. The internal caller
is already acting on behalf of the vault owner, so no consent is required.

A DataCheckout record is still written (delivery_method=INTERNAL) for full
audit trail — the owner can always see what internal modules accessed their data.

Usage:
    from apps.the_volt.gateway.internal import InternalGatewayService
    from apps.the_volt.owners.models import VaultOwner

    vault = VaultOwner.get_or_create_for_user(user)
    svc = InternalGatewayService(vault, caller_module="leases")
    entity = svc.get_entity(vault_entity_id)  # {"id": ..., "name": ..., "data": {...}}
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class InternalGatewayService:
    def __init__(self, vault_owner, caller_module: str = "internal"):
        self.vault = vault_owner
        self.caller_module = caller_module

    # -----------------------------------------------------------------------
    # Entity access
    # -----------------------------------------------------------------------

    def get_entity(self, entity_id: int) -> Optional[dict]:
        """Fetch a single entity's data dict. Returns None if not found."""
        from apps.the_volt.entities.models import VaultEntity
        try:
            entity = VaultEntity.objects.get(pk=entity_id, vault=self.vault, is_active=True)
        except VaultEntity.DoesNotExist:
            return None

        self._write_audit(
            entities_shared=[{"entity_id": entity.pk, "entity_type": entity.entity_type, "name": entity.name}],
            documents_shared=[],
        )
        return {
            "id": entity.pk,
            "entity_type": entity.entity_type,
            "name": entity.name,
            "data": entity.data,
        }

    def get_entity_by_type(self, entity_type: str) -> list[dict]:
        """All active entities of a given type in this vault."""
        from apps.the_volt.entities.models import VaultEntity
        entities = VaultEntity.objects.filter(
            vault=self.vault,
            entity_type=entity_type,
            is_active=True,
        )
        result = [
            {"id": e.pk, "entity_type": e.entity_type, "name": e.name, "data": e.data}
            for e in entities
        ]
        if result:
            self._write_audit(
                entities_shared=[{"entity_id": e["id"], "entity_type": e["entity_type"], "name": e["name"]} for e in result],
                documents_shared=[],
            )
        return result

    # -----------------------------------------------------------------------
    # Document access
    # -----------------------------------------------------------------------

    def get_entity_documents(
        self,
        entity_id: int,
        document_types: Optional[list[str]] = None,
        versions: str = "current",
    ) -> list[dict]:
        """Fetch and decrypt documents for an entity.

        Args:
            entity_id:      VaultEntity pk.
            document_types: Optional filter (e.g. ["id_document", "proof_of_address"]).
            versions:       "current" (default) = only latest; "all" = all versions.

        Returns:
            List of dicts with metadata + plaintext_bytes (bytes).
        """
        from apps.the_volt.documents.models import VaultDocument
        from apps.the_volt.encryption.utils import decrypt_bytes

        qs = VaultDocument.objects.filter(
            entity_id=entity_id,
            entity__vault=self.vault,
        ).select_related("current_version")

        if document_types:
            qs = qs.filter(document_type__in=document_types)

        result = []
        documents_snapshot = []
        owner_id = self.vault.id

        for doc in qs:
            if versions == "current":
                version_list = [doc.current_version] if doc.current_version else []
            else:
                version_list = list(doc.versions.all())

            for version in version_list:
                try:
                    version.file.seek(0)
                    encrypted = version.file.read()
                    plaintext = decrypt_bytes(encrypted, owner_id)
                except Exception:
                    logger.exception(
                        "InternalGateway: failed to decrypt version_id=%s caller=%s",
                        version.pk, self.caller_module,
                    )
                    plaintext = None

                result.append({
                    "document_id": doc.pk,
                    "document_type": doc.document_type,
                    "label": doc.label,
                    "version_number": version.version_number,
                    "original_filename": version.original_filename,
                    "mime_type": version.mime_type,
                    "sha256_hash": version.sha256_hash,
                    "plaintext_bytes": plaintext,
                })
                documents_snapshot.append({
                    "version_id": version.pk,
                    "document_type": doc.document_type,
                    "filename": version.original_filename,
                })

        if result:
            self._write_audit(entities_shared=[], documents_shared=documents_snapshot)
        return result

    # -----------------------------------------------------------------------
    # Audit
    # -----------------------------------------------------------------------

    def _write_audit(self, entities_shared: list, documents_shared: list) -> None:
        """Write a DataCheckout audit record for internal access."""
        try:
            from apps.the_volt.gateway.models import DataCheckout, DeliveryMethod, AuthMethod
            from apps.the_volt.encryption.utils import hash_bytes, package_to_bytes

            # Build minimal package for hashing
            audit_data = {
                "caller_module": self.caller_module,
                "vault_owner": str(self.vault.user.email),
                "entities_shared": entities_shared,
                "documents_shared": documents_shared,
            }
            pkg_bytes = package_to_bytes(audit_data)
            DataCheckout.objects.create(
                request=None,  # No DataRequest for internal access
                entities_shared=entities_shared,
                documents_shared=documents_shared,
                data_hash=hash_bytes(pkg_bytes),
                package_signature="internal",
                delivery_method=DeliveryMethod.INTERNAL,
                authorisation_method=AuthMethod.AUTO_GRANT,
            )
        except Exception:
            logger.exception("InternalGateway: failed to write audit record caller=%s", self.caller_module)
