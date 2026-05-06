"""
apps/popia/models.py

POPIA s23 (Data Subject Access Request) and s24 (Right to Erasure) models.

DSARRequest  — covers both export (SAR) and deletion (RTBF) requests.
ExportJob    — tracks the background job that compiles and zips a data export.

Retention rules (enforced by the deletion service):
  - User profile / PII: anonymise on approval
  - Lease records: preserve structural row, hash / blank PII (FICA 5-year, RHA 3-year)
  - Payment records: preserve (tax/SARS 7-year)
  - Audit events: preserve (append-only, hash-chain, RHA/FICA min 5-year)
  - Maintenance tickets: anonymise actor name / contact fields; preserve structural data
"""
from __future__ import annotations

import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.popia.choices import LawfulBasis, RetentionPolicy


class DSARRequest(models.Model):
    """
    A single Data Subject Access or Erasure request.

    Request types:
      SAR   — Subject Access Request (s23 POPIA): compile and deliver a copy of all
              personal information held about the data subject.
      RTBF  — Right to Be Forgotten / erasure request (s24 POPIA): operator reviews,
              then either approves (tombstone) or denies (with stated reason) within
              30 days.  Auto-delete is NOT performed — operator must explicitly approve.

    Lifecycle:
      pending → in_review → approved / denied / completed
    """

    class RequestType(models.TextChoices):
        SAR = "sar", "Subject Access Request (s23)"
        RTBF = "rtbf", "Right to Erasure (s24)"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_REVIEW = "in_review", "In Review"
        APPROVED = "approved", "Approved"
        DENIED = "denied", "Denied"
        COMPLETED = "completed", "Completed"

    # ── Multi-tenant + POPIA scaffolding ─────────────────────────────────────
    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="dsar_requests",
        help_text="Owning agency / tenant. Denormalised from requester.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32,
        choices=LawfulBasis.choices,
        default=LawfulBasis.LEGAL_OBLIGATION,
        help_text="POPIA s11 basis. DSAR handling = legal obligation (s23/s24).",
    )
    retention_policy = models.CharField(
        max_length=32,
        choices=RetentionPolicy.choices,
        default=RetentionPolicy.AUDIT_PERMANENT,
        help_text="POPIA s14 retention. DSAR records preserved for compliance audit.",
    )

    # ── Requester ────────────────────────────────────────────────────────────
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dsar_requests",
        help_text="User who submitted this request (null if account was deleted before processing)",
    )
    requester_email = models.EmailField(
        help_text="Denormalised email at submission time — preserved even after account deletion",
    )

    # ── Request details ───────────────────────────────────────────────────────
    request_type = models.CharField(max_length=10, choices=RequestType.choices)
    reason = models.TextField(
        blank=True,
        help_text="Optional reason or additional context provided by the data subject",
    )

    # ── Status ────────────────────────────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    operator_notes = models.TextField(
        blank=True,
        help_text="Internal notes by the reviewing operator (not shared with the data subject)",
    )
    denial_reason = models.TextField(
        blank=True,
        help_text="Public-facing reason for denial (communicated to the data subject)",
    )

    # ── Operator (reviewer) ───────────────────────────────────────────────────
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dsar_reviews",
        help_text="Operator who approved/denied the request",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # ── SLA tracking ─────────────────────────────────────────────────────────
    sla_deadline = models.DateTimeField(
        help_text="30-day statutory deadline (POPIA s23/s24)",
    )

    # ── Timestamps ───────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "sla_deadline"]),
            models.Index(fields=["requester", "request_type"]),
            models.Index(fields=["agency", "created_at"], name="dsar_req_agency_ts_idx"),
        ]
        verbose_name = "DSAR Request"
        verbose_name_plural = "DSAR Requests"

    def __str__(self) -> str:
        return f"{self.get_request_type_display()} — {self.requester_email} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.sla_deadline:
            self.sla_deadline = (self.created_at or timezone.now()) + timedelta(days=30)
        super().save(*args, **kwargs)

    @property
    def days_remaining(self) -> int:
        """Calendar days remaining until SLA deadline (negative = overdue)."""
        delta = self.sla_deadline - timezone.now()
        return delta.days

    @property
    def is_overdue(self) -> bool:
        return timezone.now() > self.sla_deadline and self.status in (
            self.Status.PENDING, self.Status.IN_REVIEW
        )


class ExportJob(models.Model):
    """
    Background job that compiles a user's full data into a ZIP archive for a SAR.

    The download token is a signed, time-limited secret:
      - 64-byte hex token stored in the DB
      - expires_at = created_at + 7 days (configurable via POPIA_EXPORT_TTL_DAYS)
      - on expiry the file and token are invalidated; data subject must request again

    File path is relative to MEDIA_ROOT (e.g. popia_exports/<uuid>.zip).
    """

    class JobStatus(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CONSUMED = "consumed", "Consumed (downloaded)"

    # ── Multi-tenant + POPIA scaffolding ─────────────────────────────────────
    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="export_jobs",
        help_text="Owning agency / tenant. Denormalised from dsar_request.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32,
        choices=LawfulBasis.choices,
        default=LawfulBasis.OPERATOR_INSTRUCTION,
        help_text="POPIA s11 basis. Klikk-as-operator compiles the export under s21.",
    )
    retention_policy = models.CharField(
        max_length=32,
        choices=RetentionPolicy.choices,
        default=RetentionPolicy.AI_CHAT_90D,
        help_text="POPIA s14 retention. Export archives purge after delivery (90d ceiling).",
    )

    dsar_request = models.OneToOneField(
        DSARRequest,
        on_delete=models.CASCADE,
        related_name="export_job",
    )

    status = models.CharField(
        max_length=20,
        choices=JobStatus.choices,
        default=JobStatus.QUEUED,
    )

    # ── Output ───────────────────────────────────────────────────────────────
    archive_path = models.CharField(
        max_length=512,
        blank=True,
        help_text="Path relative to MEDIA_ROOT — set by the export service on completion",
    )
    download_token = models.CharField(
        max_length=128,
        unique=True,
        default=secrets.token_urlsafe,
        help_text="Signed download token (URL-safe base64, 128 chars)",
    )
    expires_at = models.DateTimeField(
        help_text="Token/file expiry (7-day TTL by default)",
    )

    # ── Error tracking ───────────────────────────────────────────────────────
    error_detail = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Export Job"
        verbose_name_plural = "Export Jobs"
        indexes = [
            models.Index(fields=["agency", "created_at"], name="export_job_agency_ts_idx"),
        ]

    def __str__(self) -> str:
        return f"ExportJob #{self.pk} for {self.dsar_request.requester_email} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            ttl_days = getattr(settings, "POPIA_EXPORT_TTL_DAYS", 7)
            self.expires_at = timezone.now() + timedelta(days=ttl_days)
        super().save(*args, **kwargs)

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @property
    def is_downloadable(self) -> bool:
        return (
            self.status == self.JobStatus.COMPLETED
            and not self.is_expired
            and bool(self.archive_path)
        )

    @property
    def is_consumed(self) -> bool:
        """True once the file has been downloaded (single-use enforcement)."""
        return self.status == self.JobStatus.CONSUMED
