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

from apps.maintenance.models import AgentQuestion, MaintenanceActivity

logger = logging.getLogger(__name__)
chat_logger = logging.getLogger("maintenance_chat")


@receiver(post_save, sender=AgentQuestion)
def ingest_answered_question(sender, instance: AgentQuestion, **kwargs):
    """
    When an AgentQuestion is answered and added_to_context is True,
    ingest the Q&A pair into the agent_qa RAG collection.

    This closes the knowledge loop: staff answers become part of the
    AI's knowledge base for future queries.
    """
    if (
        instance.status != AgentQuestion.Status.ANSWERED
        or not instance.added_to_context
        or not instance.answer
    ):
        return

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
