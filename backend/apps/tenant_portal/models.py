from django.conf import settings
from django.db import models


class TenantAiConversation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_conversations",
    )
    title = models.CharField(max_length=200, default="AI Assistant")
    maintenance_report_suggested = models.BooleanField(
        default=False,
        help_text="True once this chat has identified a maintenance issue (show structured report CTA).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.user_id})"


class TenantAiMessage(models.Model):
    conversation = models.ForeignKey(
        TenantAiConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20)
    content = models.TextField()
    attachment = models.FileField(
        upload_to="tenant_ai/%Y/%m/",
        blank=True,
        null=True,
        help_text="Optional photo or video from the tenant.",
    )
    attachment_kind = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="image, video, or empty",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
