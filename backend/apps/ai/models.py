from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.popia.choices import LawfulBasis, RetentionPolicy


class TenantChatSession(models.Model):
    """
    One row per tenant↔AI thread. The full transcript lives in `messages` (JSON array).
    Optional links to a maintenance request and/or an agent question for staff workflows.

    Retention policy (POPIA s72):
        Sessions are purged after AI_INTERACTION_RETENTION_DAYS (default 90 days)
        based on ``updated_at`` by the ``purge_old_interactions`` management command.
        User messages stored in ``messages`` contain only PII-scrubbed content
        (raw input is never persisted — see apps.ai.scrubber).
    """

    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="tenant_chat_sessions",
        help_text="Owning agency / tenant. Denormalised from user.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32,
        choices=LawfulBasis.choices,
        default=LawfulBasis.OPERATOR_INSTRUCTION,
        help_text="POPIA s11 basis. AI processing on agency instruction (s21).",
    )
    retention_policy = models.CharField(
        max_length=32,
        choices=RetentionPolicy.choices,
        default=RetentionPolicy.AI_CHAT_90D,
        help_text="POPIA s14 retention. AI chat — 90 days unless retained.",
    )

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
        indexes = [
            models.Index(fields=["agency", "updated_at"], name="tenant_chat_agency_ts_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.user_id})"


class TenantIntelligence(models.Model):
    """
    Accumulated profile built from chat interactions.  Updated after every
    AI response so external agents (via MCP) have cross-chat context.
    """

    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="tenant_intel_profiles",
        help_text="Owning agency / tenant. Denormalised from user.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32,
        choices=LawfulBasis.choices,
        default=LawfulBasis.OPERATOR_INSTRUCTION,
        help_text="POPIA s11 basis. Profile derived under operator instruction (s21).",
    )
    retention_policy = models.CharField(
        max_length=32,
        choices=RetentionPolicy.choices,
        default=RetentionPolicy.AI_CHAT_90D,
        help_text="POPIA s14 retention. Tracks chat-derived facts; aligns with chat ttl.",
    )

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
        indexes = [
            models.Index(fields=["agency", "updated_at"], name="tenant_intel_agency_ts_idx"),
        ]

    def __str__(self) -> str:
        return f"TenantIntel({self.user_id})"


class GuideInteraction(models.Model):
    """
    One row per AI Guide request — used for analytics and audit.

    Retention policy (POPIA s72):
        Records are purged after AI_INTERACTION_RETENTION_DAYS (default 90 days)
        by the ``purge_old_interactions`` management command / scheduled task.
        The ``message`` field stores the PII-scrubbed version of the user input
        (raw input is never persisted — see apps.ai.scrubber).
    """

    PORTAL_AGENT = "agent"
    PORTAL_OWNER = "owner"
    PORTAL_SUPPLIER = "supplier"
    PORTAL_CHOICES = [
        (PORTAL_AGENT, "Agent"),
        (PORTAL_OWNER, "Owner"),
        (PORTAL_SUPPLIER, "Supplier"),
    ]

    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="guide_interactions",
        help_text="Owning agency / tenant. Denormalised from user.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32,
        choices=LawfulBasis.choices,
        default=LawfulBasis.OPERATOR_INSTRUCTION,
        help_text="POPIA s11 basis. Klikk processes guide messages on agency instruction (s21).",
    )
    retention_policy = models.CharField(
        max_length=32,
        choices=RetentionPolicy.choices,
        default=RetentionPolicy.AI_CHAT_90D,
        help_text="POPIA s14 retention. Guide interactions purge after 90 days.",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="guide_interactions",
    )
    portal = models.CharField(max_length=20, choices=PORTAL_CHOICES, default=PORTAL_AGENT)
    message = models.TextField(help_text="Raw user message sent to the guide.")
    intent = models.CharField(
        max_length=80,
        blank=True,
        default="",
        help_text="Tool name resolved by the AI (blank if no tool was called).",
    )
    action_taken = models.JSONField(
        default=dict,
        help_text="GuideAction payload returned to the frontend (empty dict if none).",
    )
    completed = models.BooleanField(
        default=False,
        help_text="True when the guide resolved a navigation action.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agency", "created_at"], name="guide_int_agency_ts_idx"),
        ]

    def __str__(self) -> str:
        return f"GuideInteraction({self.user_id}, {self.portal}, {self.intent or 'no-action'})"
