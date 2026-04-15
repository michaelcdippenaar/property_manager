import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


class VaultOwner(models.Model):
    """One row per user vault. Created lazily on first access via get_or_create_for_user().

    The VaultOwner is the anchor for all vault data. No other app may hold a
    ForeignKey to this model — external references use vault_entity_id (plain int)
    and fetch through InternalGatewayService or the external checkout flow.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vault",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Vault Owner"
        verbose_name_plural = "Vault Owners"

    def __str__(self):
        return f"Vault({self.user})"

    @classmethod
    def get_or_create_for_user(cls, user):
        owner, _ = cls.objects.get_or_create(user=user)
        return owner


class VaultOwnerAPIKey(models.Model):
    """Owner-scoped API key for authenticating the owner's own agents (MCP, CLI, scripts).

    Distinct from DataSubscriber keys (which authenticate third-party orgs on the
    external gateway). Owner keys authorise the owner's own Claude CoWork / Desktop
    MCP session to read and write into the owner's vault — full scope, no consent
    flow, every mutation written to VaultWriteAudit.

    Keys are shown ONCE at creation. Only the SHA-256 hash is stored. Prefix
    (first 8 chars of raw key) is stored for display so the owner can recognise
    which key is which in the admin UI.
    """

    KEY_PREFIX = "volt_owner_"

    vault_owner = models.ForeignKey(
        VaultOwner,
        on_delete=models.CASCADE,
        related_name="api_keys",
    )
    label = models.CharField(
        max_length=100,
        help_text="Human label, e.g. 'Claude Desktop — MacBook', 'Gmail importer'",
    )
    api_key_hash = models.CharField(
        max_length=64,
        unique=True,
        help_text="SHA-256 of the raw API key (hex)",
    )
    api_key_prefix = models.CharField(
        max_length=20,
        help_text="First chars of raw key for display, e.g. 'volt_owner_abc12…'",
    )
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Vault Owner API Key"
        verbose_name_plural = "Vault Owner API Keys"
        indexes = [
            models.Index(fields=["api_key_hash"]),
            models.Index(fields=["vault_owner", "is_active"]),
        ]

    def __str__(self):
        return f"{self.label} ({self.api_key_prefix}…)"

    @classmethod
    def generate_raw_key(cls) -> str:
        """Generate a fresh raw API key. Call hash_raw_key on it to store."""
        return f"{cls.KEY_PREFIX}{secrets.token_urlsafe(32)}"

    @staticmethod
    def hash_raw_key(raw_key: str) -> str:
        import hashlib
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @classmethod
    def create_for_owner(cls, vault_owner: "VaultOwner", label: str) -> tuple["VaultOwnerAPIKey", str]:
        """Create a new key. Returns (model instance, raw key shown once)."""
        raw = cls.generate_raw_key()
        key = cls.objects.create(
            vault_owner=vault_owner,
            label=label,
            api_key_hash=cls.hash_raw_key(raw),
            api_key_prefix=raw[: len(cls.KEY_PREFIX) + 5],
        )
        return key, raw

    @classmethod
    def resolve(cls, raw_key: str) -> "VaultOwnerAPIKey | None":
        """Look up an active key by its raw value. Returns None if not found/revoked."""
        if not raw_key or not raw_key.startswith(cls.KEY_PREFIX):
            return None
        try:
            key = cls.objects.select_related("vault_owner__user").get(
                api_key_hash=cls.hash_raw_key(raw_key),
                is_active=True,
                revoked_at__isnull=True,
            )
        except cls.DoesNotExist:
            return None
        return key

    def touch(self) -> None:
        """Stamp last_used_at. Cheap call; no audit written here (done by caller)."""
        type(self).objects.filter(pk=self.pk).update(last_used_at=timezone.now())

    def revoke(self) -> None:
        self.is_active = False
        self.revoked_at = timezone.now()
        self.save(update_fields=["is_active", "revoked_at"])
