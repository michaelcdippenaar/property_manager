"""
CheckoutService — orchestrates the full external data checkout flow.

Called after the owner has approved a DataRequest. Steps:
  1. Verify request status == APPROVED
  2. Fetch matching VaultEntity objects (filtered by requested_entity_types/fields)
  3. Fetch matching DocumentVersion objects (current versions only)
  4. Decrypt each document
  5. Build canonical data package dict
  6. Hash + sign the package
  7. Write immutable DataCheckout audit record
  8. Mark DataRequest.status = FULFILLED
  9. Return the package
"""
from __future__ import annotations

import base64
import json
import logging
from typing import Optional

from django.utils import timezone

from apps.the_volt.encryption.utils import decrypt_bytes, hash_bytes, sign_package, package_to_bytes
from apps.the_volt.gateway.models import DataRequest, DataCheckout, RequestStatus, DeliveryMethod, AuthMethod

logger = logging.getLogger(__name__)


class CheckoutError(Exception):
    pass


class CheckoutService:
    def __init__(
        self,
        data_request: DataRequest,
        delivery_method: str = DeliveryMethod.REST,
        ip_address: Optional[str] = None,
    ):
        self.request = data_request
        self.delivery_method = delivery_method
        self.ip_address = ip_address

    def execute(self) -> dict:
        """Run the full checkout. Returns the signed data package."""
        if self.request.status != RequestStatus.APPROVED:
            raise CheckoutError(
                f"DataRequest {self.request.access_token} is not APPROVED (status={self.request.status})."
            )
        if self.request.is_expired:
            raise CheckoutError("DataRequest has expired.")

        owner_id = self.request.vault_id
        vault = self.request.vault

        # 1. Collect entities
        entities_data, entities_snapshot = self._collect_entities(vault)

        # 2. Collect documents
        documents_data, documents_snapshot = self._collect_documents(vault, owner_id)

        # 3. Build package
        package = {
            "request_token": str(self.request.access_token),
            "vault_owner": str(vault.user.email),
            "subscriber": self.request.subscriber.org_name,
            "purpose": self.request.purpose,
            "checkout_at": timezone.now().isoformat(),
            "entities": entities_data,
            "documents": documents_data,
        }

        # 4. Hash + sign
        package_bytes = package_to_bytes(package)
        data_hash = hash_bytes(package_bytes)
        signature = sign_package(package_bytes, owner_id)

        # 5. Audit record (immutable)
        checkout = DataCheckout.objects.create(
            request=self.request,
            entities_shared=entities_snapshot,
            documents_shared=documents_snapshot,
            data_hash=data_hash,
            package_signature=signature,
            delivery_method=self.delivery_method,
            authorisation_method=AuthMethod.OWNER_APPROVED,
            ip_address=self.ip_address,
        )

        # 6. Mark fulfilled
        DataRequest.objects.filter(pk=self.request.pk).update(status=RequestStatus.FULFILLED)
        self.request.status = RequestStatus.FULFILLED

        logger.info(
            "Volt checkout completed: request=%s checkout=%s entities=%d documents=%d",
            self.request.access_token,
            checkout.checkout_token,
            len(entities_data),
            len(documents_data),
        )

        return {
            "checkout_token": str(checkout.checkout_token),
            "data_hash": data_hash,
            "signature": signature,
            "package": package,
        }

    def _collect_entities(self, vault) -> tuple[list[dict], list[dict]]:
        from apps.the_volt.entities.models import VaultEntity

        requested_types = self.request.requested_entity_types
        requested_fields = self.request.requested_fields  # {entity_type: [fields]} or {"*": ["*"]}

        qs = VaultEntity.objects.filter(vault=vault, is_active=True)
        if requested_types:
            qs = qs.filter(entity_type__in=requested_types)

        entities_data = []
        entities_snapshot = []

        for entity in qs:
            # Filter fields
            fields_spec = requested_fields.get(entity.entity_type) or requested_fields.get("*", ["*"])
            if fields_spec == ["*"] or fields_spec == "*":
                data = entity.data
            else:
                data = {k: v for k, v in entity.data.items() if k in fields_spec}

            entities_data.append({
                "id": entity.pk,
                "entity_type": entity.entity_type,
                "name": entity.name,
                "data": data,
            })
            entities_snapshot.append({
                "entity_id": entity.pk,
                "entity_type": entity.entity_type,
                "name": entity.name,
            })

        return entities_data, entities_snapshot

    def _collect_documents(self, vault, owner_id: int) -> tuple[list[dict], list[dict]]:
        from apps.the_volt.documents.models import VaultDocument

        requested_doc_types = self.request.requested_document_types

        qs = VaultDocument.objects.filter(
            entity__vault=vault,
        ).select_related("current_version", "entity")

        if requested_doc_types:
            qs = qs.filter(document_type__in=requested_doc_types)

        documents_data = []
        documents_snapshot = []

        for doc in qs:
            version = doc.current_version
            if not version:
                continue
            try:
                version.file.seek(0)
                encrypted = version.file.read()
                plaintext = decrypt_bytes(encrypted, owner_id)
                content_b64 = base64.b64encode(plaintext).decode()
            except Exception:
                logger.exception(
                    "Vault checkout: failed to decrypt version_id=%s for document_id=%s",
                    version.pk, doc.pk,
                )
                content_b64 = None

            documents_data.append({
                "document_id": doc.pk,
                "document_type": doc.document_type,
                "label": doc.label,
                "entity_id": doc.entity_id,
                "version_number": version.version_number,
                "original_filename": version.original_filename,
                "mime_type": version.mime_type,
                "sha256_hash": version.sha256_hash,
                "content_base64": content_b64,
            })
            documents_snapshot.append({
                "version_id": version.pk,
                "document_type": doc.document_type,
                "filename": version.original_filename,
            })

        return documents_data, documents_snapshot
