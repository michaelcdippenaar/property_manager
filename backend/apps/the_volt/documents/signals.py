"""
The Volt — document signals.

post_save on DocumentVersion:
  1. Updates document.current_version pointer (atomic)
  2. Decrypts file bytes and ingests into ChromaDB (volt_documents collection)
  3. Stores the ChromaDB chunk base ID on the DocumentVersion instance
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender="the_volt.DocumentVersion")
def on_document_version_created(sender, instance, created, **kwargs):
    if not created:
        return

    from apps.the_volt.documents.models import VaultDocument

    # 1. Point document.current_version to this new version (atomic update)
    VaultDocument.objects.filter(pk=instance.document_id).update(current_version=instance)

    # 2. Ingest into ChromaDB using the client-supplied OCR JSON.
    #    The server does NOT re-OCR the file — the client is the source of truth
    #    for the document's structured content. If no extracted_data was supplied
    #    we skip indexing (the file is still safely encrypted at rest).
    try:
        from core.volt_rag import ingest_document_version

        owner_id = instance.document.entity.vault_id
        extracted_data = instance.extracted_data or {}

        if not extracted_data:
            logger.info(
                "Volt: no extracted_data supplied for DocumentVersion pk=%s — "
                "skipping ChromaDB indexing", instance.pk,
            )
            return

        chroma_id = ingest_document_version(
            owner_id=owner_id,
            entity_id=instance.document.entity_id,
            document_id=instance.document_id,
            version_id=instance.pk,
            filename=instance.original_filename,
            document_type=instance.document.document_type,
            entity_type=instance.document.entity.entity_type,
            extracted_data=extracted_data,
        )

        if chroma_id:
            # Store chroma_id without triggering the signal again (update, not save)
            from apps.the_volt.documents.models import DocumentVersion
            DocumentVersion.objects.filter(pk=instance.pk).update(chroma_id=chroma_id)

    except Exception:
        logger.exception(
            "Volt: failed to vectorize DocumentVersion pk=%s (document_id=%s)",
            instance.pk,
            instance.document_id,
        )
