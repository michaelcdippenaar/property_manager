"""
Maintenance app signals.

1. AgentQuestion post_save: when an AgentQuestion is answered and marked
   `added_to_context=True`, automatically ingest the Q&A pair into the
   RAG vector store so future AI queries can reference staff answers.

2. MaintenanceActivity post_save: log all chat messages to a JSONL file
   for review, training data extraction, and audit trail.
"""
from __future__ import annotations

import json
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.maintenance.models import AgentQuestion, MaintenanceActivity, MaintenanceRequest

logger = logging.getLogger(__name__)
chat_logger = logging.getLogger("maintenance_chat")


@receiver(post_save, sender=AgentQuestion)
def broadcast_question_update(sender, instance: AgentQuestion, created: bool, **kwargs):
    """Broadcast question changes to admin WebSocket clients for live updates."""
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "maintenance_updates",
                {
                    "type": "maintenance.update",
                    "payload": {
                        "event": "question_created" if created else "question_updated",
                        "question_id": instance.pk,
                        "status": instance.status,
                    },
                },
            )
    except Exception:
        logger.exception("Failed to broadcast question update for #%s", instance.pk)


@receiver(post_save, sender=AgentQuestion)
def ingest_answered_question(sender, instance: AgentQuestion, **kwargs):
    """
    When an AgentQuestion is answered, automatically ingest the Q&A pair
    into the agent_qa RAG collection.

    This closes the knowledge loop: staff answers become part of the
    AI's knowledge base for future queries.

    Also auto-sets added_to_context=True when an answer is provided,
    so staff don't need to remember to tick the checkbox.
    """
    if instance.status != AgentQuestion.Status.ANSWERED or not instance.answer:
        return

    # Auto-flag as added_to_context so staff don't have to tick the checkbox.
    # Use update() to avoid re-triggering this signal.
    if not instance.added_to_context:
        AgentQuestion.objects.filter(pk=instance.pk).update(added_to_context=True)

    try:
        from core.contract_rag import ingest_agent_question
        success = ingest_agent_question(
            question_id=instance.pk,
            question=instance.question,
            answer=instance.answer,
            category=instance.category,
            property_id=instance.property_id,
        )
        if success:
            logger.info(
                "Ingested AgentQuestion #%s into RAG Q&A collection", instance.pk
            )
        else:
            logger.warning(
                "Failed to ingest AgentQuestion #%s into RAG", instance.pk
            )
    except Exception:
        logger.exception(
            "Error ingesting AgentQuestion #%s into RAG", instance.pk
        )


@receiver(post_save, sender=MaintenanceActivity)
def log_chat_message(sender, instance: MaintenanceActivity, created: bool, **kwargs):
    """
    Log every new maintenance chat message to a JSONL file.

    This creates an audit trail and provides training data for AI improvement.
    The log file path is configured via MAINTENANCE_CHAT_LOG in settings.
    Each line is a JSON object with: request_id, activity_id, type, message,
    author, role, source, timestamp.
    """
    if not created:
        return

    try:
        entry = {
            "request_id": instance.request_id,
            "activity_id": instance.pk,
            "type": instance.activity_type,
            "message": instance.message,
            "author": instance.created_by.full_name if instance.created_by else "AI Agent",
            "role": instance.created_by.role if instance.created_by else "ai",
            "source": (instance.metadata or {}).get("source", "user"),
            "timestamp": instance.created_at.isoformat() if instance.created_at else None,
        }
        chat_logger.info(json.dumps(entry, ensure_ascii=False))
    except Exception:
        logger.exception(
            "Failed to log chat message for activity #%s", instance.pk
        )


@receiver(post_save, sender=MaintenanceRequest)
def broadcast_issue_update(sender, instance: MaintenanceRequest, created: bool, **kwargs):
    """Broadcast issue list change to admin WebSocket clients."""
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        logger.warning(
            "SIGNAL broadcast_issue_update fired: pk=%s created=%s channel_layer=%s",
            instance.pk, created, type(channel_layer).__name__,
        )
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "maintenance_updates",
                {
                    "type": "maintenance.update",
                    "payload": {
                        "event": "issue_created" if created else "issue_updated",
                        "request_id": instance.pk,
                        "status": instance.status,
                        "title": instance.title,
                    },
                },
            )
            logger.warning("SIGNAL broadcast_issue_update: group_send completed for pk=%s", instance.pk)
    except Exception:
        logger.exception("Failed to broadcast issue update for #%s", instance.pk)


@receiver(post_save, sender=MaintenanceActivity)
def broadcast_activity_update(sender, instance: MaintenanceActivity, created: bool, **kwargs):
    """Broadcast new activity to admin WebSocket clients for live chat updates."""
    if not created:
        return
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "maintenance_updates",
                {
                    "type": "maintenance.update",
                    "payload": {
                        "event": "activity_created",
                        "request_id": instance.request_id,
                        "activity_type": instance.activity_type,
                        "message": instance.message[:200],
                    },
                },
            )
    except Exception:
        logger.exception("Failed to broadcast activity for #%s", instance.pk)


@receiver(post_save, sender=MaintenanceRequest)
def vectorize_maintenance_issue(sender, instance: MaintenanceRequest, **kwargs):
    """
    Auto-vectorize maintenance issues into RAG when created or updated.

    This ensures the AI can find similar past issues via vector search.
    The issue is indexed with its title, description, category, priority,
    and property_id for scoped queries.
    """
    try:
        from core.contract_rag import ingest_maintenance_issue

        property_id = instance.unit.property_id if instance.unit_id else None
        success = ingest_maintenance_issue(
            request_id=instance.pk,
            title=instance.title,
            description=instance.description,
            category=instance.category,
            priority=instance.priority,
            status=instance.status,
            property_id=property_id,
        )
        if success:
            logger.info("Vectorized maintenance issue #%s", instance.pk)
    except Exception:
        logger.exception("Error vectorizing maintenance issue #%s", instance.pk)
