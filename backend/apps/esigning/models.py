import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class ESigningSubmission(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        DECLINED = "declined", "Declined"
        EXPIRED = "expired", "Expired"

    class SigningMode(models.TextChoices):
        PARALLEL = "parallel", "Parallel — all signers at once"
        SEQUENTIAL = "sequential", "Sequential — one after the other"

    lease = models.ForeignKey(
        "leases.Lease", on_delete=models.CASCADE, related_name="signing_submissions"
    )
    docuseal_submission_id = models.CharField(max_length=100, blank=True)
    docuseal_template_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    signing_mode = models.CharField(
        max_length=12,
        choices=SigningMode.choices,
        default=SigningMode.SEQUENTIAL,
        help_text="Sequential: signers proceed in order. Parallel: all sign at once.",
    )
    signers = models.JSONField(default=list)
    signed_pdf_url = models.URLField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    webhook_payload = models.JSONField(default=dict)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Submission {self.docuseal_submission_id or self.pk} ({self.status})"

    def get_signer_by_submitter_id(self, submitter_id):
        """Return the signer dict from JSON for this DocuSeal submitter id, or None."""
        try:
            tid = int(submitter_id)
        except (TypeError, ValueError):
            return None
        for row in self.signers or []:
            rid = row.get("id")
            if rid is None:
                continue
            try:
                if int(rid) == tid:
                    return row
            except (TypeError, ValueError):
                continue
        return None


class ESigningPublicLink(models.Model):
    """
    Unguessable link (UUID) for passwordless signing in the admin SPA.
    Scoped to one DocuSeal submitter on one submission.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(
        ESigningSubmission, on_delete=models.CASCADE, related_name="public_links"
    )
    submitter_id = models.PositiveIntegerField(
        help_text="DocuSeal submitter id (matches signers[].id on the submission JSON)."
    )
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["expires_at"]),
        ]

    def is_expired(self):
        return timezone.now() >= self.expires_at
