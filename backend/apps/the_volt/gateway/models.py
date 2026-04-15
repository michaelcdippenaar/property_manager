import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.the_volt.owners.models import VaultOwner


class DataSubscriber(models.Model):
    """A registered third-party organisation that can request access to vault data.

    API keys are generated once and stored as SHA-256 hashes (never plaintext).
    The raw key is returned ONCE at creation time — the caller must save it.
    """

    org_name = models.CharField(max_length=255)
    org_contact_email = models.EmailField(blank=True)
    api_key_hash = models.CharField(max_length=128, help_text="SHA-256 of the raw API key")
    api_key_prefix = models.CharField(max_length=16, help_text="First chars of raw key (display only)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Data Subscriber"
        verbose_name_plural = "Data Subscribers"

    def __str__(self):
        return f"{self.org_name} ({self.api_key_prefix}…)"


class RequestStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    DENIED = "denied", "Denied"
    EXPIRED = "expired", "Expired"
    FULFILLED = "fulfilled", "Fulfilled"


class DataRequest(models.Model):
    """The Request Container — created when a subscriber requests vault data.

    Flow:
      1. Subscriber posts to /gateway/request/ → DataRequest(PENDING) created
      2. Owner receives OTP link → reviews → Approves or Denies
      3. On APPROVE → CheckoutService decrypts, signs, audits → FULFILLED
    """

    subscriber = models.ForeignKey(
        DataSubscriber,
        on_delete=models.CASCADE,
        related_name="requests",
    )
    vault = models.ForeignKey(
        VaultOwner,
        on_delete=models.CASCADE,
        related_name="incoming_requests",
    )
    access_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(max_length=20, choices=RequestStatus.choices, default=RequestStatus.PENDING)

    # What the subscriber is asking for
    requested_entity_types = models.JSONField(default=list, help_text="e.g. ['personal', 'company']")
    requested_fields = models.JSONField(
        default=dict,
        help_text="e.g. {'personal': ['id_number', 'address']} or {'*': ['*']} for all",
    )
    requested_document_types = models.JSONField(default=list, help_text="e.g. ['id_document', 'proof_of_address']")
    purpose = models.TextField(help_text="Human-readable reason shown to the owner for consent")

    expires_at = models.DateTimeField(help_text="Auto: 48h from creation")
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Data Request"
        verbose_name_plural = "Data Requests"

    def __str__(self):
        return f"DataRequest({self.subscriber.org_name} → {self.vault.user}, {self.status})"

    def save(self, *args, **kwargs):
        if not self.pk and not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=48)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at


class DataRequestApprovalLink(models.Model):
    """Passwordless URL for owners who don't have the mobile app.

    Security model (mirrors ESigningPublicLink):
      - UUID token = unguessable URL (shared via SMS)
      - 6-digit OTP = second factor (also sent via SMS, separately)
      - Max 3 OTP attempts before lockout
      - Expires at same time as the DataRequest (48h)
    """

    token = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.OneToOneField(
        DataRequest,
        on_delete=models.CASCADE,
        related_name="approval_link",
    )
    otp_hash = models.CharField(max_length=64, help_text="SHA-256 of the 6-digit OTP")
    otp_attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Approval Link"
        verbose_name_plural = "Approval Links"

    def __str__(self):
        return f"ApprovalLink({self.request})"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_locked(self):
        return self.otp_attempts >= 3

    @property
    def is_used(self):
        return self.used_at is not None


class DeliveryMethod(models.TextChoices):
    REST = "rest", "REST API"
    MCP = "mcp", "MCP"
    GRAPHQL = "graphql", "GraphQL"
    INTERNAL = "internal", "Internal (app module)"


class AuthMethod(models.TextChoices):
    OWNER_APPROVED = "owner_approved", "Owner Approved"
    AUTO_GRANT = "auto_grant", "Auto Grant (internal)"


class DataCheckout(models.Model):
    """Immutable audit record — written once when data is delivered, never updated.

    Records exactly what was shared, with whom, when, how it was authorised,
    and provides a cryptographic signature for the data package.
    Append-only: never call .save() after creation, never .delete().
    """

    request = models.ForeignKey(
        DataRequest,
        on_delete=models.CASCADE,
        related_name="checkouts",
        null=True,
        blank=True,
        help_text="Null for internal gateway access (no external DataRequest)",
    )
    checkout_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # Snapshot of what was shared (IDs only — actual data was delivered)
    entities_shared = models.JSONField(help_text="[{entity_id, entity_type, name}, ...]")
    documents_shared = models.JSONField(help_text="[{version_id, document_type, filename}, ...]")

    # Cryptographic proof
    data_hash = models.CharField(max_length=64, help_text="SHA-256 of the full data package bytes")
    package_signature = models.CharField(max_length=128, help_text="HMAC-SHA256 signature of package")

    # Audit fields
    delivery_method = models.CharField(max_length=20, choices=DeliveryMethod.choices)
    authorisation_method = models.CharField(max_length=20, choices=AuthMethod.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    checked_out_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-checked_out_at"]
        verbose_name = "Data Checkout"
        verbose_name_plural = "Data Checkouts"

    def __str__(self):
        return f"Checkout({self.request.subscriber.org_name}, {self.checked_out_at:%Y-%m-%d %H:%M})"


class VaultWriteAudit(models.Model):
    """One row per mutation performed against the vault via the owner MCP surface.

    Complements DataCheckout (which audits READS). Together they form the
    complete POPIA §17 processing log: who read what, who wrote what.

    Append-only: never updated, never deleted. The before/after snapshots
    contain only the fields that changed — not the full record — so the log
    itself stays compact and doesn't duplicate the vault.
    """

    class Operation(models.TextChoices):
        ENSURE_VAULT = "ensure_vault", "Ensure vault exists"
        UPSERT_OWNER = "upsert_owner", "Upsert owner entity"
        UPSERT_PROPERTY = "upsert_property", "Upsert property asset"
        UPSERT_TENANT = "upsert_tenant", "Upsert tenant entity"
        UPSERT_ENTITY = "upsert_entity", "Upsert generic entity"
        ATTACH_DOCUMENT = "attach_document", "Attach document version"
        LINK_ENTITIES = "link_entities", "Link two entities"
        UNLINK_ENTITIES = "unlink_entities", "Unlink two entities"

    vault = models.ForeignKey(
        VaultOwner,
        on_delete=models.CASCADE,
        related_name="write_audits",
    )
    api_key = models.ForeignKey(
        "the_volt.VaultOwnerAPIKey",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audits",
        help_text="Which owner API key performed the write (null = internal caller)",
    )
    operation = models.CharField(max_length=40, choices=Operation.choices)
    target_model = models.CharField(
        max_length=60,
        help_text="e.g. 'VaultEntity', 'VaultDocument', 'EntityRelationship'",
    )
    target_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="PK of the affected row. Null if multiple or pre-create",
    )
    before = models.JSONField(
        default=dict,
        blank=True,
        help_text="Changed fields, pre-mutation. Empty on create.",
    )
    after = models.JSONField(
        default=dict,
        blank=True,
        help_text="Changed fields, post-mutation. Empty on delete.",
    )
    client_info = models.JSONField(
        default=dict,
        blank=True,
        help_text="Free-form metadata: MCP client name, tool name, args hash, ip",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Vault Write Audit"
        verbose_name_plural = "Vault Write Audits"
        indexes = [
            models.Index(fields=["vault", "-created_at"]),
            models.Index(fields=["api_key", "-created_at"]),
            models.Index(fields=["operation"]),
            models.Index(fields=["target_model", "target_id"]),
        ]

    def __str__(self):
        return f"Audit({self.get_operation_display()} {self.target_model}:{self.target_id})"
