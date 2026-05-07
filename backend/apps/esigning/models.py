import uuid

from django.conf import settings
from django.db import models
from apps.accounts.tenancy import TenantManager
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.popia.choices import LawfulBasis, RetentionPolicy


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

    class SigningBackend(models.TextChoices):
        NATIVE = "native", "Native"

    # Owning agency / tenant. Denormalised — outlives the originating
    # lease, and the audit trail needs direct scoping (4-hop chain via
    # submission → lease → unit → property → agency is too brittle for
    # POPIA-required audit queries).
    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="esigning_submissions",
        help_text="Owning agency / tenant. Denormalised from lease/mandate chain.",
    )
    # POPIA s11 — signing a lease is performance of contract.
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.CONTRACT,
        help_text="POPIA s11 basis. Lease signing = performance of contract.",
    )
    # POPIA s14 — keep submission for the lease lifetime; the signed PDF
    # itself is then governed by the lease's RHA_3YR / FICA_5YR retention.
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.LEASE_LIFETIME,
        help_text="POPIA s14 retention. Signed PDF inherits lease retention.",
    )

    lease = models.ForeignKey(
        "leases.Lease", on_delete=models.CASCADE, related_name="signing_submissions",
        null=True, blank=True,
    )
    mandate = models.ForeignKey(
        "properties.RentalMandate", on_delete=models.CASCADE, related_name="signing_submissions",
        null=True, blank=True,
    )
    signing_backend = models.CharField(
        max_length=10,
        choices=SigningBackend.choices,
        default=SigningBackend.NATIVE,
        help_text="Which signing engine handles this submission.",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    signing_mode = models.CharField(
        max_length=12,
        choices=SigningMode.choices,
        default=SigningMode.SEQUENTIAL,
        help_text="Sequential: signers proceed in order. Parallel: all sign at once.",
    )
    signers = models.JSONField(default=list)
    document_html = models.TextField(
        blank=True,
        help_text="Snapshot of filled lease HTML at submission time (native signing).",
    )
    document_hash = models.CharField(
        max_length=100,
        blank=True,
        help_text="SHA-256 hash of document_html for tamper detection.",
    )
    signed_pdf_file = models.FileField(
        upload_to="esigning/signed_pdfs/",
        blank=True,
        help_text="Locally generated signed PDF (native signing).",
    )
    signed_pdf_hash = models.CharField(
        max_length=100,
        blank=True,
        help_text="SHA-256 hash of the signed PDF for tamper detection.",
    )
    captured_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Merge field data manually entered by signers during signing.",
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    webhook_payload = models.JSONField(default=dict)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agency", "status"], name="esign_sub_agency_status_idx"),
        ]

    def __str__(self):
        return f"Submission {self.pk} ({self.status})"

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


class ESigningAuditEvent(models.Model):
    """Immutable audit trail for e-signing events (ECTA Section 13 compliance)."""
    class EventType(models.TextChoices):
        LINK_CREATED = "link_created", "Link Created"
        DOCUMENT_VIEWED = "document_viewed", "Document Viewed"
        CONSENT_GIVEN = "consent_given", "Consent Given"
        SIGNATURE_APPLIED = "signature_applied", "Signature Applied"
        SIGNING_COMPLETED = "signing_completed", "Signing Completed"
        DOCUMENT_COMPLETED = "document_completed", "Document Completed"
        LINK_EXPIRED = "link_expired", "Link Expired"
        DRAFT_SAVED = "draft_saved", "Draft Saved"
        SUPPORTING_DOC_UPLOADED = "supporting_doc_uploaded", "Supporting Document Uploaded"
        SUPPORTING_DOC_DELETED = "supporting_doc_deleted", "Supporting Document Deleted"

    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="esigning_audit_events",
        help_text="Owning agency / tenant. Inherited from submission.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.CONTRACT,
        help_text="POPIA s11 basis. Contractual signing audit trail.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.LEASE_LIFETIME,
        help_text="POPIA s14 retention. ECTA s13 evidence — keep with lease.",
    )

    submission = models.ForeignKey(ESigningSubmission, on_delete=models.CASCADE, related_name="audit_events")
    signer_role = models.CharField(max_length=100, blank=True)
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    user = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["submission", "event_type"]),
            models.Index(fields=["agency", "event_type"], name="esign_evt_agency_type_idx"),
        ]

    def __str__(self):
        return f"{self.event_type} — {self.submission_id} at {self.created_at}"

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


class ESigningPublicLink(models.Model):
    """Unguessable link (UUID) for passwordless signing in the admin SPA."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="esigning_public_links",
        help_text="Owning agency / tenant. Inherited from submission.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.OPERATOR_INSTRUCTION,
        help_text="POPIA s11 basis. Short-lived signing token (operator instruction).",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.NONE,
        help_text="POPIA s14 retention. Tokens auto-expire on submission/timeout.",
    )

    submission = models.ForeignKey(
        ESigningSubmission, on_delete=models.CASCADE, related_name="public_links"
    )
    signer_role = models.CharField(
        max_length=50,
        blank=True,
        help_text="Signer role (e.g. 'tenant_1', 'landlord').",
    )
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["expires_at"]),
            models.Index(fields=["agency", "expires_at"], name="esign_link_agency_exp_idx"),
        ]

    def is_expired(self):
        return timezone.now() >= self.expires_at

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


class SigningDraft(models.Model):
    """
    Persists a tenant's partial signing progress between sessions.
    Created/overwritten whenever the tenant clicks "Save & Continue Later".
    Keyed 1-to-1 on the ESigningPublicLink so each signer has their own draft.
    """

    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="esigning_drafts",
        help_text="Owning agency / tenant. Inherited from public_link.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.CONTRACT,
        help_text="POPIA s11 basis. Partial-signing state for contract performance.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.LEASE_LIFETIME,
        help_text="POPIA s14 retention. Discarded once submission completes.",
    )

    public_link = models.OneToOneField(
        ESigningPublicLink,
        on_delete=models.CASCADE,
        related_name="draft",
    )
    # Serialised signature state: {fieldName: {imageData: str, signedAt: ISO}}
    signed_fields_data = models.JSONField(
        default=dict,
        help_text="Partially captured signature fields keyed by field name.",
    )
    # Serialised merge-field state: {fieldName: value}
    captured_fields_data = models.JSONField(
        default=dict,
        help_text="Partially captured merge-field (text) values.",
    )
    saved_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Signing Draft"
        indexes = [
            models.Index(fields=["agency", "saved_at"], name="esign_draft_agency_saved_idx"),
        ]

    def __str__(self):
        return f"Draft for link {self.public_link_id} (saved {self.saved_at:%Y-%m-%d %H:%M})"

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


class SupportingDocument(models.Model):
    """
    Supporting documents uploaded by a tenant during the signing flow.
    Examples: 3-month bank statement, copy of ID, proof of address.
    Scoped to both the public link (who uploaded) and the submission (what lease).
    """

    class DocumentType(models.TextChoices):
        BANK_STATEMENT = "bank_statement", "Bank Statement (3 months)"
        ID_COPY = "id_copy", "Copy of ID"
        PROOF_OF_ADDRESS = "proof_of_address", "Proof of Address"
        OTHER = "other", "Other"

    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="esigning_supporting_documents",
        help_text="Owning agency / tenant. Inherited from submission.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.LEGAL_OBLIGATION,
        help_text="POPIA s11 basis. FICA/KYC docs = legal obligation.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.FICA_5YR,
        help_text="POPIA s14 retention. FICA s42/s43 5-year minimum.",
    )

    public_link = models.ForeignKey(
        ESigningPublicLink,
        on_delete=models.CASCADE,
        related_name="supporting_documents",
    )
    submission = models.ForeignKey(
        ESigningSubmission,
        on_delete=models.CASCADE,
        related_name="supporting_documents",
    )
    document_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
    )
    file = models.FileField(
        upload_to="esigning/supporting_docs/%Y/%m/",
        help_text="Accepted: PDF, JPEG, PNG — max 10 MB.",
    )
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0, help_text="File size in bytes.")
    notes = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by_role = models.CharField(
        max_length=50,
        blank=True,
        help_text="Signer role from ESigningPublicLink (e.g. 'tenant_1').",
    )

    class Meta:
        ordering = ["document_type", "uploaded_at"]
        verbose_name = "Supporting Document"
        indexes = [
            models.Index(fields=["agency", "document_type"], name="esign_supdoc_agency_typ_idx"),
        ]

    def __str__(self):
        return f"{self.get_document_type_display()} — {self.original_filename}"

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

@receiver(post_save, sender=ESigningSubmission)
def sync_mandate_status(sender, instance, **kwargs):
    """
    Keep RentalMandate.status in sync with ESigningSubmission.status.
    Fires whenever a submission is saved — guards against no-mandate submissions cheaply.
    """
    if not instance.mandate_id:
        return

    _status_map = {
        ESigningSubmission.Status.COMPLETED:   "active",
        ESigningSubmission.Status.DECLINED:    "cancelled",
        ESigningSubmission.Status.IN_PROGRESS: "partially_signed",
    }
    new_status = _status_map.get(instance.status)
    if not new_status:
        return

    mandate = instance.mandate
    update_fields = ["status", "updated_at"]
    mandate.status = new_status

    if new_status == "active" and instance.signed_pdf_file:
        mandate.signed_document = instance.signed_pdf_file
        update_fields.append("signed_document")

    mandate.save(update_fields=update_fields)
