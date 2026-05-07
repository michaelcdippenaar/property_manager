from django.conf import settings
from django.db import models
from apps.accounts.tenancy import TenantManager

from apps.popia.choices import LawfulBasis, RetentionPolicy


class NotificationChannel(models.TextChoices):
    EMAIL = "email", "Email"
    SMS = "sms", "SMS"
    WHATSAPP = "whatsapp", "WhatsApp"


class NotificationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"


class NotificationLog(models.Model):
    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="notification_logs",
        help_text="Owning agency / tenant. Backfilled null where recipient cannot be resolved.",
    )
    lawful_basis = models.CharField(
        max_length=32,
        choices=LawfulBasis.choices,
        default=LawfulBasis.OPERATOR_INSTRUCTION,
        help_text="POPIA s11 basis. Klikk dispatches on agency instruction (s21).",
    )
    retention_policy = models.CharField(
        max_length=32,
        choices=RetentionPolicy.choices,
        default=RetentionPolicy.NONE,
        help_text="POPIA s14 retention. Operational dispatch log; review at audit time.",
    )

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
            models.Index(fields=["agency", "created_at"], name="notif_log_agency_ts_idx"),
        ]

    def __str__(self):
        return f"{self.channel} → {self.to_address} ({self.status})"

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


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

    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="push_preferences",
        help_text="Owning agency / tenant. Denormalised from user.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32,
        choices=LawfulBasis.choices,
        default=LawfulBasis.CONSENT,
        help_text="POPIA s11 basis. Push opt-in is consent (s11(1)(a)).",
    )
    retention_policy = models.CharField(
        max_length=32,
        choices=RetentionPolicy.choices,
        default=RetentionPolicy.NONE,
        help_text="POPIA s14 retention. Preference rows live with the user account.",
    )

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
        indexes = [
            models.Index(fields=["agency", "category"], name="push_pref_agency_cat_idx"),
        ]

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

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()
