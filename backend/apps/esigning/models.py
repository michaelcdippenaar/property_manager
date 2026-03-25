from django.conf import settings
from django.db import models


class ESigningSubmission(models.Model):
    class Status(models.TextChoices):
        PENDING     = 'pending',     'Pending'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED   = 'completed',   'Completed'
        DECLINED    = 'declined',    'Declined'
        EXPIRED     = 'expired',     'Expired'

    lease = models.ForeignKey(
        'leases.Lease', on_delete=models.CASCADE, related_name='signing_submissions'
    )
    docuseal_submission_id = models.CharField(max_length=100, blank=True)
    docuseal_template_id   = models.CharField(max_length=100, blank=True)
    status   = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    signers  = models.JSONField(default=list)
    signed_pdf_url = models.URLField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    webhook_payload = models.JSONField(default=dict)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Submission {self.docuseal_submission_id or self.pk} ({self.status})"
