"""
Properties app signals.

Landlord post_save: when classification_data changes (the AI document
classifier has produced a fresh owner_classification.json), enqueue a
background RAG ingestion so the owner chat can cite specific clauses.
"""
from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.properties.models import Landlord, LandlordDocument
from apps.properties.tasks import enqueue_owner_ingestion

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Landlord)
def enqueue_owner_rag_ingestion_on_landlord_save(
    sender, instance: Landlord, created: bool, update_fields=None, **kwargs
):
    """Re-ingest when classification_data is (re)written.

    We trigger on:
      - explicit `update_fields={'classification_data'}` saves from the
        classifier endpoint
      - newly-created landlords with classification_data already populated
        (bulk imports / tests)

    We deliberately do NOT trigger on every Landlord save — most saves are
    name/email edits that don't affect document retrieval.
    """
    uf = set(update_fields or [])
    should_ingest = (
        "classification_data" in uf
        or (created and instance.classification_data)
    )
    if not should_ingest:
        return
    try:
        enqueue_owner_ingestion(instance.pk)
    except Exception:
        logger.exception(
            "owner_rag: failed to enqueue ingestion for landlord %s", instance.pk
        )


@receiver(post_save, sender=LandlordDocument)
def enqueue_owner_rag_ingestion_on_document_save(
    sender, instance: LandlordDocument, created: bool, **kwargs
):
    """Re-ingest when a new document is uploaded.

    A new upload means the next gap analysis may shift — re-embedding keeps
    the chat's retrieval aligned with what's actually on file. We only fire
    on `created`; plain metadata edits don't need re-ingestion.
    """
    if not created:
        return
    try:
        enqueue_owner_ingestion(instance.landlord_id)
    except Exception:
        logger.exception(
            "owner_rag: failed to enqueue ingestion for landlord %s (doc %s)",
            instance.landlord_id, instance.pk,
        )
