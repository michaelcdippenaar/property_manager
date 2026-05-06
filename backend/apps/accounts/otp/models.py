"""
OTP persistence models.

OTPCode  — active/pending OTP codes (hashed at rest).
OTPAuditLog — POPIA-required immutable audit trail for every OTP event.
"""
from django.db import models
from django.conf import settings

from apps.popia.choices import LawfulBasis, RetentionPolicy


class OTPCodeV1(models.Model):
    """
    A single issued OTP code (v1 service — hashed, purpose-scoped).

    The plaintext code is NEVER persisted — only the HMAC-SHA256 hash.
    This is the successor to the legacy OTPCode placeholder in accounts/models.py.
    Use via OTPService.send() / OTPService.verify() — never instantiate directly.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="otp_v2_codes",
    )
    purpose = models.CharField(
        max_length=64,
        help_text="Scopes the code — e.g. 'registration', 'password_reset', 'sensitive_change'.",
    )
    code_hash = models.CharField(
        max_length=128,
        help_text="HMAC-SHA256 hex digest of the plaintext code. Never store plaintext.",
    )
    channel_used = models.CharField(
        max_length=20,
        help_text="Channel that delivered this code, e.g. 'email' or 'sms'.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Set when the code is successfully verified and consumed.",
    )
    attempt_count = models.PositiveSmallIntegerField(
        default=0,
        help_text="Number of failed verify attempts against this code.",
    )

    # ── Multi-tenant + POPIA (Phase 1.8) — inherited from user.agency ────
    agency = models.ForeignKey(
        "accounts.Agency", on_delete=models.PROTECT,
        null=True, blank=True, related_name="otp_v1_codes",
        help_text="Owning agency / tenant. Inherited from user.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.OPERATOR_INSTRUCTION,
        help_text="POPIA s11 basis. OTP = security operator-instruction.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.NONE,
        help_text="POPIA s14 retention. Short-lived; expiry-driven cleanup.",
    )

    class Meta:
        # Use a distinct table name so this coexists with the legacy OTPCode
        # placeholder in apps/accounts/models.py without a naming collision.
        db_table = "accounts_otp_code"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "purpose", "created_at"]),
            models.Index(fields=["expires_at"]),
        ]
        verbose_name = "OTP Code"
        verbose_name_plural = "OTP Codes"

    def __str__(self) -> str:
        return f"OTPCodeV1({self.user_id}, {self.purpose}, {'consumed' if self.consumed_at else 'active'})"

    @property
    def is_consumed(self) -> bool:
        return self.consumed_at is not None

    @property
    def is_locked(self) -> bool:
        """True when max verify attempts exceeded — code is effectively dead."""
        from django.conf import settings as _s
        max_attempts = getattr(_s, "OTP_MAX_ATTEMPTS", 3)
        return self.attempt_count >= max_attempts


class OTPAuditLog(models.Model):
    """
    Immutable POPIA audit trail for OTP events.
    Written on every issue / verify-success / verify-fail.
    """

    class EventType(models.TextChoices):
        ISSUED = "issued", "OTP Issued"
        VERIFY_SUCCESS = "verify_success", "Verify Success"
        VERIFY_FAIL = "verify_fail", "Verify Fail"
        RATE_LIMITED = "rate_limited", "Rate Limited"
        EXPIRED = "expired", "Expired"
        LOCKED = "locked", "Locked (max attempts)"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="otp_audit_logs",
    )
    purpose = models.CharField(max_length=64)
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    channel = models.CharField(max_length=20, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # ── Multi-tenant + POPIA (Phase 1.8) — inherited from user.agency ────
    agency = models.ForeignKey(
        "accounts.Agency", on_delete=models.PROTECT,
        null=True, blank=True, related_name="otp_audit_logs",
        help_text="Owning agency / tenant. Inherited from user.agency when present.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.LEGAL_OBLIGATION,
        help_text="POPIA s11 basis. OTP audit = legal obligation.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.AUDIT_PERMANENT,
        help_text="POPIA s14 retention. Append-only audit; anonymise references when subject expires.",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "event_type"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["agency", "event_type"], name="otpaudit_agency_event_idx"),
        ]
        verbose_name = "OTP Audit Log"
        verbose_name_plural = "OTP Audit Logs"

    def __str__(self) -> str:
        return f"OTPAuditLog({self.event_type}, user={self.user_id}, {self.created_at})"
