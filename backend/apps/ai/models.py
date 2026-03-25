from __future__ import annotations

from django.conf import settings
from django.db import models


class TenantChatSession(models.Model):
    """
    One row per tenant↔AI thread. The full transcript lives in `messages` (JSON array).
    Optional links to a maintenance request and/or an agent question for staff workflows.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tenant_chat_sessions",
    )
    title = models.CharField(max_length=200, default="AI Assistant")
    maintenance_report_suggested = models.BooleanField(
        default=False,
        help_text="True once this chat has identified a maintenance issue (show structured report CTA).",
    )
    messages = models.JSONField(
        default=list,
        help_text='Ordered list of {"id", "role", "content", "created_at", "attachment_kind", "attachment_storage"?}',
    )
    maintenance_request = models.ForeignKey(
        "maintenance.MaintenanceRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_chat_sessions",
        help_text="Set when a maintenance request is created from this chat.",
    )
    agent_question = models.ForeignKey(
        "maintenance.AgentQuestion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_chat_sessions",
        help_text="Optional link to an open agent question tied to this thread.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.user_id})"


class TenantIntelligence(models.Model):
    """
    Accumulated profile built from chat interactions.  Updated after every
    AI response so external agents (via MCP) have cross-chat context.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tenant_intel",
    )
    property_ref = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_intel_profiles",
    )
    unit_ref = models.ForeignKey(
        "properties.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_intel_profiles",
    )

    facts = models.JSONField(
        default=dict,
        help_text="Key-value pairs extracted from chats: contact_preference, known_issues, notes, etc.",
    )
    question_categories = models.JSONField(
        default=dict,
        help_text='Category → count, e.g. {"maintenance_ticket": 4, "general_enquiry": 12}',
    )
    total_chats = models.PositiveIntegerField(default=0)
    total_messages = models.PositiveIntegerField(default=0)
    complaint_score = models.FloatField(
        default=0.0,
        help_text="0-1 ratio of complaint/maintenance chats to total chats.",
    )

    last_chat_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Tenant intelligence profiles"

    def __str__(self) -> str:
        return f"TenantIntel({self.user_id})"
