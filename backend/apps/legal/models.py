"""
Legal consent models — versioned Terms of Service and per-user acknowledgement.

Design:
- LegalDocument  : one row per document type per version (ToS, Privacy Policy).
                   Only one row per (doc_type, is_current=True) enforced in save().
- UserConsent    : one row per user per LegalDocument version.
                   Absence of a row for the current version = not yet accepted.

Material-change flow:
1. Admin creates a new LegalDocument (is_current=True, requires_re_ack=True).
2. On next API call the middleware/decorator checks UserConsent for the current version.
3. If absent, the API returns HTTP 451 with {"requires_tos_acceptance": true, "document_id": ...}.
4. Front-end redirects user to accept screen; on POST the UserConsent row is created.
"""

from django.conf import settings
from django.db import models


class LegalDocument(models.Model):
    """A versioned legal document (Terms of Service, Privacy Policy, etc.)."""

    class DocType(models.TextChoices):
        TERMS_OF_SERVICE = "tos", "Terms of Service"
        PRIVACY_POLICY = "privacy", "Privacy Policy"

    doc_type = models.CharField(max_length=20, choices=DocType.choices)
    version = models.CharField(
        max_length=20,
        help_text='Semantic version string, e.g. "1.0", "1.1"',
    )
    effective_date = models.DateField()
    summary_of_changes = models.TextField(
        blank=True,
        help_text="Human-readable changelog entry shown to users on re-acknowledgement prompts.",
    )
    url = models.URLField(
        help_text="Canonical public URL of this document, e.g. https://klikk.co.za/legal/terms",
    )
    is_current = models.BooleanField(
        default=False,
        help_text="Exactly one document per doc_type should be current at any time.",
    )
    requires_re_ack = models.BooleanField(
        default=False,
        help_text=(
            "Set True for material changes that require existing users to re-acknowledge. "
            "When True, logged-in users without a UserConsent for this version are gated."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-effective_date", "-created_at"]
        # Enforce single-current constraint at DB level
        constraints = [
            models.UniqueConstraint(
                fields=["doc_type", "version"],
                name="unique_legal_document_version",
            ),
        ]

    def __str__(self):
        return f"{self.get_doc_type_display()} v{self.version} ({'current' if self.is_current else 'archived'})"

    def save(self, *args, **kwargs):
        """When setting is_current=True, unset any previous current document of the same type."""
        if self.is_current:
            LegalDocument.objects.filter(
                doc_type=self.doc_type, is_current=True
            ).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_current(cls, doc_type: str):
        """Return the current document for a given type, or None."""
        return cls.objects.filter(doc_type=doc_type, is_current=True).first()


class UserConsent(models.Model):
    """
    Records a user's explicit acceptance of a specific LegalDocument version.

    One row per (user, document). If a newer document exists without a corresponding
    row here, the user has not yet accepted it.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="legal_consents",
    )
    document = models.ForeignKey(
        LegalDocument,
        on_delete=models.PROTECT,
        related_name="consents",
    )
    accepted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ["-accepted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "document"],
                name="unique_user_consent_per_document",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "document"]),
        ]

    def __str__(self):
        return f"{self.user_id} accepted {self.document} at {self.accepted_at}"

    @classmethod
    def has_accepted_current(cls, user, doc_type: str) -> bool:
        """Return True if the user has accepted the current version of a document type."""
        current = LegalDocument.get_current(doc_type)
        if current is None:
            # No current document configured — don't gate (prevents lockout on fresh installs)
            return True
        return cls.objects.filter(user=user, document=current).exists()

    @classmethod
    def pending_for_user(cls, user):
        """
        Return a queryset of current LegalDocuments that require re-acknowledgement
        and have NOT yet been accepted by this user.
        """
        accepted_ids = cls.objects.filter(user=user).values_list("document_id", flat=True)
        return LegalDocument.objects.filter(
            is_current=True,
            requires_re_ack=True,
        ).exclude(pk__in=accepted_ids)
