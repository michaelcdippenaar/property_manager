from django.db import models

from apps.the_volt.entities.models import VaultEntity


class DocumentType(models.TextChoices):
    ID_DOCUMENT = "id_document", "ID Document"
    PASSPORT = "passport", "Passport"
    PROOF_OF_ADDRESS = "proof_of_address", "Proof of Address"
    TRUST_DEED = "trust_deed", "Trust Deed"
    MOI = "moi", "Memorandum of Incorporation"
    CIPC_CERTIFICATE = "cipc_certificate", "CIPC Certificate"
    TAX_CLEARANCE = "tax_clearance", "Tax Clearance"
    FINANCIAL_STATEMENT = "financial_statement", "Financial Statement"
    TITLE_DEED = "title_deed", "Title Deed"
    INSURANCE_POLICY = "insurance_policy", "Insurance Policy"
    FICA_DOCUMENT = "fica_document", "FICA Document"
    BANKING_DETAIL = "banking_detail", "Banking Detail"
    RESOLUTION = "resolution", "Resolution"
    POWER_OF_ATTORNEY = "power_of_attorney", "Power of Attorney"
    OTHER = "other", "Other"


def vault_upload_path(instance, filename):
    """Upload path: vault/{owner_id}/entities/{entity_id}/docs/{doc_id}/{version}.enc"""
    owner_id = instance.document.entity.vault_id
    entity_id = instance.document.entity_id
    doc_id = instance.document_id
    return f"vault/{owner_id}/entities/{entity_id}/docs/{doc_id}/{instance.version_number}.enc"


class VaultDocument(models.Model):
    """Groups all versions of one logical document for an entity.

    Think of VaultDocument as a folder: "John's ID Document".
    Each upload creates a new DocumentVersion. current_version always points
    to the latest, but all prior versions are retained (never deleted).

    upload a new ID → version 2 becomes current, version 1 is archived.
    """

    entity = models.ForeignKey(
        VaultEntity,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(max_length=50, choices=DocumentType.choices)
    label = models.CharField(max_length=255, help_text="e.g. \"John's SA ID\"")
    current_version = models.ForeignKey(
        "DocumentVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Pointer to the latest DocumentVersion, updated atomically by signal",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Vault Document"
        verbose_name_plural = "Vault Documents"
        unique_together = [("entity", "document_type", "label")]

    def __str__(self):
        return f"{self.label} ({self.get_document_type_display()})"


class DocumentVersion(models.Model):
    """One physical file upload — the actual encrypted bytes on disk.

    Files are encrypted at rest using the owner's Fernet key (see encryption/utils.py).
    The .enc extension signals "do not serve raw — decrypt via download endpoint".
    sha256_hash is the hash of the PLAINTEXT bytes for tamper detection.

    version_number is auto-incremented in save() before the file is written,
    so the upload path is stable at creation time.
    """

    document = models.ForeignKey(
        VaultDocument,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version_number = models.PositiveIntegerField()
    file = models.FileField(upload_to=vault_upload_path, help_text="Encrypted .enc bytes")
    original_filename = models.CharField(max_length=255)
    file_size_bytes = models.PositiveIntegerField(help_text="Pre-encryption plaintext size in bytes")
    sha256_hash = models.CharField(max_length=64, help_text="SHA-256 of plaintext bytes")
    mime_type = models.CharField(max_length=100, blank=True)
    chroma_id = models.CharField(max_length=128, blank=True, help_text="ChromaDB base chunk ID in volt_documents")
    extracted_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Client-supplied OCR / structured extraction of this document "
            "(e.g. parsed Memorandum of Incorporation fields). Used directly "
            "for ChromaDB indexing — no server-side re-extraction."
        ),
    )
    notes = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version_number"]
        verbose_name = "Document Version"
        verbose_name_plural = "Document Versions"
        unique_together = [("document", "version_number")]

    def __str__(self):
        return f"{self.document.label} v{self.version_number}"

    def save(self, *args, **kwargs):
        if not self.pk and not self.version_number:
            # Auto-increment: count existing versions + 1
            self.version_number = self.document.versions.count() + 1
        super().save(*args, **kwargs)


class VerificationStatus(models.TextChoices):
    UNVERIFIED = "unverified", "Unverified"
    SELF_ATTESTED = "self_attested", "Self-attested"
    COMMISSIONER_SIGNED = "commissioner_signed", "Commissioner of Oaths Signed"
    THIRD_PARTY_VERIFIED = "third_party_verified", "Third-party Verified"
    OFFICIAL_SOURCE = "official_source", "Verified against Official Source"
    REJECTED = "rejected", "Rejected"


def certified_copy_upload_path(instance, filename):
    """Upload path for the commissioner-signed / certified copy file."""
    version = instance.document_version
    owner_id = version.document.entity.vault_id
    entity_id = version.document.entity_id
    doc_id = version.document_id
    return (
        f"vault/{owner_id}/entities/{entity_id}/docs/{doc_id}/"
        f"certified/{version.version_number}.enc"
    )


class DocumentVerification(models.Model):
    """Verification metadata attached to a specific DocumentVersion.

    Tracks whether the document is legitimate (self-attested, commissioner signed,
    official source, etc.), who verified it, when it expires, and stores the
    commissioner-signed certified copy as a separate encrypted file.

    The `certified_copy_file` is the Commissioner of Oaths stamped version —
    stored encrypted alongside the original.
    """

    document_version = models.OneToOneField(
        DocumentVersion,
        on_delete=models.CASCADE,
        related_name="verification",
    )
    verification_status = models.CharField(
        max_length=30,
        choices=VerificationStatus.choices,
        default=VerificationStatus.UNVERIFIED,
    )
    verification_source = models.CharField(
        max_length=255,
        blank=True,
        help_text="Free-text source (e.g. 'Home Affairs HANIS', 'CIPC BizPortal', commissioner's office)",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.CharField(
        max_length=255,
        blank=True,
        help_text="Name or identifier of the verifier (user, commissioner, integration)",
    )

    # Commissioner of Oaths specifics
    commissioner_name = models.CharField(max_length=255, blank=True)
    commissioner_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Commissioner ID / registration / stamp reference",
    )
    commissioner_signed_at = models.DateTimeField(null=True, blank=True)

    # Certified / signed copy — encrypted separate file
    certified_copy_file = models.FileField(
        upload_to=certified_copy_upload_path,
        null=True,
        blank=True,
        help_text="Encrypted bytes of the commissioner-signed / certified copy",
    )
    certified_copy_sha256 = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA-256 of the certified copy plaintext bytes",
    )
    certified_copy_original_filename = models.CharField(max_length=255, blank=True)

    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text="When the document itself expires (e.g. passport expiry)",
    )

    verification_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Free-form extras: OCR confidence, API response, notes, etc.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Document Verification"
        verbose_name_plural = "Document Verifications"

    def __str__(self):
        return f"Verification({self.document_version} — {self.get_verification_status_display()})"

    @property
    def is_expired(self):
        if not self.expiry_date:
            return False
        from django.utils import timezone
        return self.expiry_date < timezone.now().date()


class OwnershipScope(models.TextChoices):
    """Who retains the document when an asset is transferred.

    - asset_bound: follows the asset on sale (title deed, COC, building plans, rates clearance)
    - owner_bound: stays with the original owner (OTP, bond statement, rental agreement)
    - shared: both parties retain their own encrypted copy (joint custody docs)
    """

    ASSET_BOUND = "asset_bound", "Asset-bound (transfers with asset)"
    OWNER_BOUND = "owner_bound", "Owner-bound (stays with owner)"
    SHARED = "shared", "Shared (dual-vaulted)"


class DocumentTypeCatalogue(models.Model):
    """Data-driven catalogue of document types recognised by the Volt.

    Replaces the static DocumentType TextChoices as the authoritative list.
    Seeded via migration with ~85 SA documents spanning Personal, Trust, Company,
    CC, Sole Proprietary, and Asset (Property / Vehicle / Financial / Movable).

    Designed to feed:
      - The MCP import flow (email pattern classification → catalogue lookup)
      - Client-side OCR (extraction_schema tells the client which fields to parse)
      - Resource packages (required_documents reference these codes)
      - Regulatory references (FICA / POPIA / CIPC / Master rule citations)

    Regulatory changes are data migrations, not schema migrations.
    """

    code = models.CharField(
        max_length=100,
        unique=True,
        help_text="Stable machine code, e.g. 'cipc_cor14_3', 'sa_id_document'",
    )
    label = models.CharField(max_length=255, help_text="Human label, e.g. 'CIPC CoR14.3 Registration Certificate'")

    external_reference_codes = models.JSONField(
        default=list,
        blank=True,
        help_text="Alternative names / regulatory form numbers, e.g. ['CoR14.3', 'Registration Certificate']",
    )

    applies_to_entity_types = models.JSONField(
        default=list,
        help_text="EntityType codes this document can attach to, e.g. ['company'] or ['personal', 'sole_proprietary']",
    )
    ownership_scope = models.CharField(
        max_length=20,
        choices=OwnershipScope.choices,
        default=OwnershipScope.OWNER_BOUND,
        help_text="Asset-bound docs transfer on sale; owner-bound stay with the owner",
    )

    issuing_authority = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. 'CIPC', 'DHA', 'SARS', 'Master of the High Court', 'Deeds Office'",
    )
    default_validity_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Typical validity window (e.g. 90 for proof of address, 365 for tax clearance). Null = no expiry",
    )

    # Classification signals for inbound import (Gmail / Drive scanning)
    email_sender_patterns = models.JSONField(
        default=list,
        blank=True,
        help_text="Sender email patterns, e.g. ['*@cipc.co.za', 'noreply@sarsefiling.co.za']",
    )
    email_subject_patterns = models.JSONField(
        default=list,
        blank=True,
        help_text="Subject substrings that indicate this doc type",
    )
    classification_signals = models.TextField(
        blank=True,
        help_text="Free-text hints for an AI classifier: distinguishing phrases, layout cues, stamps",
    )

    # Structured extraction schema — keys the client-side OCR should attempt to populate
    extraction_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text="Expected extraction fields: {field_key: {type, label, required}}",
    )

    is_primary_identity_doc = models.BooleanField(
        default=False,
        help_text="True for SA ID, passport, CIPC registration — docs that establish identity",
    )
    regulatory_reference = models.CharField(
        max_length=255,
        blank=True,
        help_text="Legal basis, e.g. 'FICA s.21', 'Companies Act s.14', 'Trust Property Control Act'",
    )

    sort_order = models.PositiveIntegerField(default=0, help_text="Display order within an entity type")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "label"]
        verbose_name = "Document Type (Catalogue)"
        verbose_name_plural = "Document Type Catalogue"
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["ownership_scope"]),
        ]

    def __str__(self):
        return f"{self.label} ({self.code})"
