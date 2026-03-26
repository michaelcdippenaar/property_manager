"""
Maintenance app signals.

AgentQuestion post_save: when an AgentQuestion is answered and marked
`added_to_context=True`, automatically ingest the Q&A pair into the
RAG vector store so future AI queries can reference staff answers.
"""
from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.maintenance.models import AgentQuestion

logger = logging.getLogger(__name__)


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
