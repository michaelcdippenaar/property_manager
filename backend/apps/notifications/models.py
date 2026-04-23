from django.conf import settings
from django.db import models


class NotificationChannel(models.TextChoices):
    EMAIL = "email", "Email"
    SMS = "sms", "SMS"
    WHATSAPP = "whatsapp", "WhatsApp"


class NotificationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"


class NotificationLog(models.Model):
    channel = models.CharField(max_length=16, choices=NotificationChannel.choices)
    to_address = models.CharField(max_length=320)
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    status = models.CharField(
        max_length=16,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
    )
    provider_message_id = models.CharField(max_length=128, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["channel", "status"]),
        ]

    def __str__(self):
        return f"{self.channel} → {self.to_address} ({self.status})"


class PushPreference(models.Model):
    """
    Per-user push notification opt-in/out by category.

    Categories mirror the event categories dispatched by push signals:
      lease, mandate, rent, maintenance, chat

    A missing row means the user has not expressed a preference; the service
    defaults to *enabled* for all categories.

    POPIA: only stored once the user explicitly interacts with the POPIA
    opt-in banner (UI responsibility).
    """

    class Category(models.TextChoices):
        LEASE = "lease", "Lease updates"
        MANDATE = "mandate", "Mandate updates"
        RENT = "rent", "Rent & payments"
        MAINTENANCE = "maintenance", "Maintenance updates"
        CHAT = "chat", "Chat messages"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_preferences",
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "category")
        ordering = ["user", "category"]

    def __str__(self):
        flag = "on" if self.enabled else "off"
        return f"{self.user_id} | {self.category} = {flag}"

    @classmethod
    def is_enabled(cls, user, category: str) -> bool:
        """Return True if the user has push enabled for *category* (default True)."""
        try:
            return cls.objects.get(user=user, category=category).enabled
        except cls.DoesNotExist:
            return True
