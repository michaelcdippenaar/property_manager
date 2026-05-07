import hashlib
import secrets
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from apps.accounts.tenancy import TenantManager
from django.utils import timezone

# SubscriptionTier is defined in tier_service to keep pricing logic co-located.
# We import it here so Django migrations can discover it (same app_label="accounts").

# OTP v1 service models — imported here so Django migrations discover them under
# the "accounts" app label.  See apps/accounts/otp/ for the full implementation.
from apps.accounts.otp.models import OTPCodeV1, OTPAuditLog  # noqa: F401
from apps.accounts.tier_service import SubscriptionTier  # noqa: F401  re-export
from apps.popia.choices import AnonymisationReason, LawfulBasis, RetentionPolicy


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        TENANT = "tenant", "Tenant"
        AGENT = "agent", "Agent"  # Deprecated — migrate to estate_agent/managing_agent
        ADMIN = "admin", "Admin"
        SUPPLIER = "supplier", "Supplier"
        OWNER = "owner", "Owner"
        AGENCY_ADMIN = "agency_admin", "Agency Admin"
        ESTATE_AGENT = "estate_agent", "Estate Agent"
        MANAGING_AGENT = "managing_agent", "Managing Agent"
        ACCOUNTANT = "accountant", "Accountant"
        VIEWER = "viewer", "Viewer"

    class FFCCategory(models.TextChoices):
        ESTATE = "estate", "Estate Agent"
        MANAGING = "managing", "Managing Agent"

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    id_number = models.CharField(max_length=20, blank=True, help_text="SA ID or passport number")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.TENANT)
    agency = models.ForeignKey(
        "Agency", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="members",
        help_text="Agency this user belongs to (agents, agency admin, viewers)",
    )
    module_access = models.JSONField(
        default=list, blank=True,
        help_text='Module access flags for viewer role, e.g. ["inspections","maintenance","properties"]',
    )
    ffc_number = models.CharField(
        max_length=50, blank=True,
        help_text="Individual Fidelity Fund Certificate number (PPA requirement)",
    )
    ffc_category = models.CharField(
        max_length=20, choices=FFCCategory.choices, blank=True,
        help_text="FFC category — distinct from role (regulatory classification)",
    )
    class TwoFAMethod(models.TextChoices):
        TOTP = "totp", "Authenticator App (TOTP)"
        EMAIL = "email", "Email OTP"

    two_fa_method = models.CharField(
        max_length=10,
        choices=TwoFAMethod.choices,
        default=TwoFAMethod.TOTP,
        help_text="Second factor method used when 2FA is required for this account.",
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    seen_welcome_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When the tenant first dismissed the welcome screen; null = not yet seen.",
    )
    skipped_2fa_setup_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When an optional-2FA user (e.g. owner) last skipped the 2FA setup prompt. "
                  "Null means they have not been prompted yet or never skipped.",
    )

    # ── POPIA / multi-tenant (Phase 1.8) ─────────────────────────────────
    # User.agency already exists above; we only add the POPIA fields here.
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.CONTRACT,
        help_text="POPIA s11 basis. Auth users normally CONTRACT (employment / portal access).",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.LEASE_LIFETIME,
        help_text="POPIA s14 retention. Mirrors lease lifecycle for tenant users.",
    )
    vault_entity_id = models.PositiveIntegerField(
        null=True, blank=True, db_index=True,
        help_text="Vault33 VaultEntity PK once user identity is mirrored.",
    )
    is_anonymised = models.BooleanField(
        default=False,
        help_text="True after PII fields have been scrubbed per a DSAR or retention policy.",
    )
    anonymised_at = models.DateTimeField(null=True, blank=True)
    anonymisation_reason = models.CharField(
        max_length=32, choices=AnonymisationReason.choices, blank=True, default="",
        help_text="Why this record was anonymised (POPIA s23/s24 audit trail).",
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    def get_full_name(self):
        """AbstractUser-compatible display name (our model uses AbstractBaseUser only)."""
        return self.full_name

    # ── Role convenience properties ──

    @property
    def has_admin_access(self):
        """Full admin or agency principal."""
        return self.role in (self.Role.ADMIN, self.Role.AGENCY_ADMIN)

    @property
    def is_agent_role(self):
        """Any agent variant (legacy agent, estate, managing, agency admin)."""
        return self.role in (
            self.Role.AGENT, self.Role.ESTATE_AGENT,
            self.Role.MANAGING_AGENT, self.Role.AGENCY_ADMIN,
        )

    @property
    def is_managing(self):
        """Managing agent or legacy agent (both have ongoing property access)."""
        return self.role in (self.Role.AGENT, self.Role.MANAGING_AGENT)

    def has_module(self, module):
        """Check module access — admin/agency_admin get all; viewer checks module_access list."""
        if self.role in (self.Role.ADMIN, self.Role.AGENCY_ADMIN):
            return True
        if self.role == self.Role.VIEWER:
            return module in (self.module_access or [])
        return False

    # Multi-tenant manager (Phase 2.1) — auto-scopes to current_agency_id().
    tenant_objects = TenantManager()


class Person(models.Model):
    """
    A natural person or company involved in property transactions.
    May or may not have a system login (linked_user).
    Used for: property owners, tenants, co-tenants, occupants, guarantors.
    """
    class PersonType(models.TextChoices):
        INDIVIDUAL = "individual", "Individual"
        COMPANY = "company", "Company"

    # ── Multi-tenant + POPIA (Phase 1.8) ─────────────────────────────────
    # Per the locked decision in popia-klikk-rentals-brief.md: Person is
    # per-agency. Backfilled via linked_user.agency or landlord_profile.agency.
    agency = models.ForeignKey(
        "Agency", on_delete=models.PROTECT,
        null=True, blank=True, related_name="persons",
        help_text="Owning agency / tenant. Person is per-agency (full isolation).",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.CONTRACT,
        help_text="POPIA s11 basis. Person captured under lease = performance of contract.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.LEASE_LIFETIME,
        help_text="POPIA s14 retention. Mirrors the parent relationship lifecycle.",
    )
    vault_entity_id = models.PositiveIntegerField(
        null=True, blank=True, db_index=True,
        help_text="Vault33 VaultEntity PK once person identity is mirrored.",
    )
    is_anonymised = models.BooleanField(
        default=False,
        help_text="True after PII fields have been scrubbed per a DSAR or retention policy.",
    )
    anonymised_at = models.DateTimeField(null=True, blank=True)
    anonymisation_reason = models.CharField(
        max_length=32, choices=AnonymisationReason.choices, blank=True, default="",
        help_text="Why this record was anonymised (POPIA s23/s24 audit trail).",
    )

    linked_user = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="person_profile",
        help_text="System login account if this person has portal access"
    )
    person_type = models.CharField(max_length=20, choices=PersonType.choices, default=PersonType.INDIVIDUAL)
    full_name = models.CharField(max_length=200)
    id_number = models.CharField(max_length=20, blank=True, help_text="SA ID or passport number")
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    # Additional personal info (often captured during lease signing)
    address = models.TextField(blank=True, help_text="Current residential address")
    employer = models.CharField(max_length=200, blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    emergency_contact_name = models.CharField(max_length=200, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    # Financial (captured during rental applications)
    monthly_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Gross monthly income in ZAR")
    # Company-specific
    company_reg = models.CharField(max_length=50, blank=True)
    vat_number = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["phone"],
                condition=~models.Q(phone=""),
                name="unique_person_phone_when_set",
            ),
        ]
        indexes = [
            models.Index(fields=["agency", "full_name"], name="person_agency_name_idx"),
        ]

    def __str__(self):
        return self.full_name

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


class PersonDocument(models.Model):
    """Supporting documents attached to a Person (ID, proof of address, income, etc).
    Persists across leases — if the same person re-leases, their docs are already on file."""

    class DocumentType(models.TextChoices):
        ID_COPY          = 'id_copy',          'ID / Passport Copy'
        PROOF_OF_ADDRESS = 'proof_of_address', 'Proof of Address'
        PROOF_OF_INCOME  = 'proof_of_income',  'Proof of Income'
        FICA             = 'fica',             'FICA / KYC Document'
        OTHER            = 'other',            'Other'

    person        = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    file          = models.FileField(upload_to='person_documents/')
    description   = models.CharField(max_length=200, blank=True)
    uploaded_at   = models.DateTimeField(auto_now_add=True)

    # ── Multi-tenant + POPIA (Phase 1.8) — inherited from person.agency ──
    agency = models.ForeignKey(
        "Agency", on_delete=models.PROTECT,
        null=True, blank=True, related_name="person_documents",
        help_text="Owning agency / tenant. Inherited from person.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.LEGAL_OBLIGATION,
        help_text="POPIA s11 basis. FICA/ID documents = legal obligation.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.FICA_5YR,
        help_text="POPIA s14 retention. Default 5 years (FICA s42/s43).",
    )

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=["agency", "document_type"], name="persondoc_agency_type_idx"),
        ]

    def __str__(self):
        return f"{self.get_document_type_display()} — {self.person.full_name}"

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


class OTPCode(models.Model):
    """
    Legacy OTP placeholder — plaintext code stored (pre-v1 stub).
    Kept for backward-compatibility with old OTP views.
    Superseded by OTPCodeV1 in apps/accounts/otp/models.py (hashed, purpose-scoped).
    Do not use in new code — use OTPService instead.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otp_codes")
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    # ── Multi-tenant + POPIA (Phase 1.8) — inherited from user.agency ────
    agency = models.ForeignKey(
        "Agency", on_delete=models.PROTECT,
        null=True, blank=True, related_name="otp_codes",
        help_text="Owning agency / tenant. Inherited from user.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.OPERATOR_INSTRUCTION,
        help_text="POPIA s11 basis. OTP = security operator-instruction.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.LEASE_LIFETIME,
        help_text="POPIA s14 retention. Mirrors user lifecycle.",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"OTP for {self.user.email}"

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


class PushToken(models.Model):
    """FCM/APNs/Web Push device token for push notifications."""

    class Platform(models.TextChoices):
        IOS = "ios", "iOS"
        ANDROID = "android", "Android"
        WEB = "web", "Web Push"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="push_tokens")
    token = models.TextField()
    platform = models.CharField(max_length=10, choices=Platform.choices)
    updated_at = models.DateTimeField(auto_now=True)

    # ── Multi-tenant + POPIA (Phase 1.8) — inherited from user.agency ────
    agency = models.ForeignKey(
        "Agency", on_delete=models.PROTECT,
        null=True, blank=True, related_name="push_tokens",
        help_text="Owning agency / tenant. Inherited from user.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.OPERATOR_INSTRUCTION,
        help_text="POPIA s11 basis. Push tokens are operator-instruction.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.LEASE_LIFETIME,
        help_text="POPIA s14 retention. Mirrors user lifecycle.",
    )

    class Meta:
        unique_together = ("user", "token")
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.platform} token for {self.user.email}"

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


class UserInvite(models.Model):
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=User.Role.choices)
    agency = models.ForeignKey(
        "Agency", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="invites",
        help_text="Agency to assign when invite is accepted (for agent/viewer roles)",
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="invites_sent")
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    # ── POPIA (Phase 1.8) — UserInvite already has agency FK above ───────
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.OPERATOR_INSTRUCTION,
        help_text="POPIA s11 basis. Invitations are transient operator-instruction.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.NONE,
        help_text="POPIA s14 retention. Transient — no automated retention.",
    )

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_pending(self):
        return self.accepted_at is None and self.cancelled_at is None

    def __str__(self):
        return f"Invite for {self.email} ({self.role})"

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


class AuthAuditLog(models.Model):
    """Immutable audit trail for authentication events."""
    class EventType(models.TextChoices):
        LOGIN_SUCCESS = "login_success", "Login Success"
        LOGIN_FAILED = "login_failed", "Login Failed"
        LOGOUT = "logout", "Logout"
        REGISTER = "register", "Register"
        PASSWORD_RESET_REQUEST = "password_reset_request", "Password Reset Request"
        PASSWORD_RESET_CONFIRM = "password_reset_confirm", "Password Reset Confirm"
        PASSWORD_CHANGE = "password_change", "Password Change"
        OTP_SENT = "otp_sent", "OTP Sent"
        OTP_VERIFIED = "otp_verified", "OTP Verified"
        OTP_FAILED = "otp_failed", "OTP Failed"
        ROLE_CHANGE = "role_change", "Role Change"
        ACCOUNT_LOCKED = "account_locked", "Account Locked"
        GOOGLE_AUTH = "google_auth", "Google Auth"

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # ── Multi-tenant + POPIA (Phase 1.8) — inherited from user.agency ────
    agency = models.ForeignKey(
        "Agency", on_delete=models.PROTECT,
        null=True, blank=True, related_name="auth_audit_logs",
        help_text="Owning agency / tenant. Inherited from user.agency when present.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.LEGAL_OBLIGATION,
        help_text="POPIA s11 basis. Auth audit = legal obligation (security records).",
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
            models.Index(fields=["agency", "event_type"], name="auth_agency_event_idx"),
        ]

    def __str__(self):
        return f"{self.event_type} — {self.user_id} at {self.created_at}"

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


class Agency(models.Model):
    """
    Singleton agency record.  Stores the details that appear on
    mandates, leases and other generated documents.

    subscription_tier is a FK to SubscriptionTier (defined in tier_service.py
    but registered in the same app_label="accounts").  It is null by default
    so existing agencies keep working; the billing tab lets admins assign/change it.
    """

    class AccountType(models.TextChoices):
        AGENCY     = "agency",     "Estate Agency"
        INDIVIDUAL = "individual", "Individual Owner"

    # ── Account type ──
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.AGENCY,
    )

    # ── Identity ──
    name = models.CharField(max_length=200)
    trading_name = models.CharField(
        max_length=200, blank=True,
        help_text="Trading-as name shown on documents (e.g. t/a Century 21 Stellenbosch)",
    )
    registration_number = models.CharField(max_length=50, blank=True, help_text="CIPC registration number")
    vat_number = models.CharField(max_length=20, blank=True)
    eaab_ffc_number = models.CharField(
        max_length=50, blank=True,
        help_text="PPRA Fidelity Fund Certificate number",
    )

    # ── Contact ──
    contact_number = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    physical_address = models.TextField(blank=True)
    postal_address = models.TextField(blank=True)
    website = models.URLField(blank=True)

    # ── Trust account ──
    trust_account_number = models.CharField(max_length=50, blank=True)
    trust_bank_name = models.CharField(max_length=100, blank=True)
    trust_branch_code = models.CharField(max_length=20, blank=True)

    # ── Compliance ──
    principal_name = models.CharField(
        max_length=200, blank=True,
        help_text="Principal property practitioner",
    )
    principal_ppra_number = models.CharField(
        max_length=20, blank=True,
        help_text="7-digit PPRA registration number",
    )
    auditor_name = models.CharField(max_length=200, blank=True)
    auditor_irba_number = models.CharField(
        max_length=20, blank=True,
        help_text="IRBA practice number",
    )
    bee_level = models.CharField(
        max_length=20, blank=True,
        help_text="e.g. Level 1, Level 4, Exempt",
    )
    fica_registered = models.BooleanField(
        default=False,
        help_text="Registered as Accountable Institution with FIC",
    )

    # ── Financial cycle ──
    statement_date = models.CharField(
        max_length=30, blank=True, default="the 5th",
        help_text='e.g. "the 5th"',
    )
    disbursement_date = models.CharField(
        max_length=30, blank=True, default="the 7th",
        help_text='e.g. "the 7th"',
    )
    information_officer_email = models.EmailField(blank=True)

    # ── Branding ──
    logo = models.ImageField(upload_to="agency/", null=True, blank=True)

    # ── Subscription ──
    subscription_tier = models.ForeignKey(
        "SubscriptionTier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agencies",
        help_text="Pricing tier — null means all features are accessible (backwards compat).",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ── Onboarding ──
    onboarding_completed_at = models.DateTimeField(
        null=True, blank=True,
        help_text=(
            "When the AGENCY_ADMIN finished the agency setup wizard. "
            "Used by the router guard to redirect first-time users to /onboarding."
        ),
    )

    class Meta:
        verbose_name_plural = "agencies"

    def __str__(self):
        return self.name or "Agency"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        """Backwards-compat: return the first active agency, or None."""
        return cls.objects.filter(is_active=True).first()

    @classmethod
    def for_user(cls, user):
        """Return the agency this user belongs to, or fall back to get_solo()."""
        if user and hasattr(user, "agency_id") and user.agency_id:
            return cls.objects.filter(pk=user.agency_id).first()
        return cls.get_solo()

    def has_feature(self, slug: str) -> bool:
        """
        Convenience proxy: returns True when the agency's subscription tier
        includes the named feature slug, or True when no tier is set
        (backwards-compatible — existing agencies without a tier get full access).
        """
        from apps.accounts.tier_service import TierService
        return TierService(self).has_feature(slug)


class LoginAttempt(models.Model):
    email = models.EmailField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    succeeded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # ── Multi-tenant + POPIA (Phase 1.8) ─────────────────────────────────
    # LoginAttempt is keyed by email and may be created before any user
    # exists; cannot always resolve to an agency. Stay null when unknown.
    agency = models.ForeignKey(
        "Agency", on_delete=models.PROTECT,
        null=True, blank=True, related_name="login_attempts",
        help_text="Owning agency / tenant. Resolved from matching user.agency when known.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.LEGAL_OBLIGATION,
        help_text="POPIA s11 basis. Brute-force protection = legal obligation.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.AUDIT_PERMANENT,
        help_text="POPIA s14 retention. Security log; anonymise references when subject expires.",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "created_at"]),
            models.Index(fields=["agency", "succeeded"], name="loginatt_agency_ok_idx"),
        ]

    def __str__(self):
        return f"{'OK' if self.succeeded else 'FAIL'} login for {self.email}"

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


# ── 2FA / TOTP ────────────────────────────────────────────────────────────────

# Roles that MUST enroll in TOTP before full access is granted (DEC-018).
# ACCOUNTANT and VIEWER are excluded for v1.0.
# OWNER is in TOTP_OPTIONAL_ROLES — prompted but not blocked.
TOTP_REQUIRED_ROLES = {
    User.Role.ADMIN,
    User.Role.AGENCY_ADMIN,
    User.Role.AGENT,
    User.Role.MANAGING_AGENT,
    User.Role.ESTATE_AGENT,
}

# Roles for which 2FA is recommended but skippable (DEC-018).
# These users receive a one-time suggestion prompt; skipping is persisted via
# User.skipped_2fa_setup_at so they are not nagged on every subsequent login.
TOTP_OPTIONAL_ROLES = {
    User.Role.OWNER,
}

# Grace period before a required-2FA user is hard-blocked (days).
TOTP_GRACE_PERIOD_DAYS = 7


class UserTOTP(models.Model):
    """
    Stores the TOTP secret for a user's authenticator app.
    One active record per user at most.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="totp")
    secret = models.CharField(max_length=64)          # base32-encoded pyotp secret
    enrolled_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)    # True once first code verified
    # When a required-role user first logs in, we stamp this so the grace period
    # can be checked without needing a separate query.
    grace_deadline = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    # ── Multi-tenant + POPIA (Phase 1.8) — inherited from user.agency ────
    agency = models.ForeignKey(
        "Agency", on_delete=models.PROTECT,
        null=True, blank=True, related_name="user_totps",
        help_text="Owning agency / tenant. Inherited from user.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.OPERATOR_INSTRUCTION,
        help_text="POPIA s11 basis. TOTP secrets = security operator-instruction.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.LEASE_LIFETIME,
        help_text="POPIA s14 retention. Mirrors user lifecycle.",
    )

    class Meta:
        verbose_name = "User TOTP"

    def __str__(self):
        return f"TOTP for {self.user.email} ({'active' if self.is_active else 'pending'})"

    @classmethod
    def for_user(cls, user):
        """Return the active TOTP record for a user, or None."""
        try:
            t = cls.objects.get(user=user)
            return t if t.is_active else None
        except cls.DoesNotExist:
            return None

    def verify(self, code: str, valid_window: int = 1) -> bool:
        """Verify a TOTP code against this secret (±1 window = ±30 s)."""
        import pyotp
        totp = pyotp.TOTP(self.secret)
        return totp.verify(code, valid_window=valid_window)

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


class TOTPRecoveryCode(models.Model):
    """
    Single-use recovery codes issued during TOTP enrollment.
    Codes are stored as SHA-256 hashes so the plaintext is never persisted.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recovery_codes")
    code_hash = models.CharField(max_length=64)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # ── Multi-tenant + POPIA (Phase 1.8) — inherited from user.agency ────
    agency = models.ForeignKey(
        "Agency", on_delete=models.PROTECT,
        null=True, blank=True, related_name="totp_recovery_codes",
        help_text="Owning agency / tenant. Inherited from user.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.OPERATOR_INSTRUCTION,
        help_text="POPIA s11 basis. Recovery codes = security operator-instruction.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.LEASE_LIFETIME,
        help_text="POPIA s14 retention. Mirrors user lifecycle.",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Recovery code for {self.user.email} ({'used' if self.used_at else 'available'})"

    @property
    def is_used(self):
        return self.used_at is not None

    @classmethod
    def generate_for_user(cls, user, count: int = 10):
        """
        Delete existing codes for this user and issue `count` fresh ones.
        Returns the list of plaintext codes (shown once, then discarded).
        """
        cls.objects.filter(user=user).delete()
        plaintext_codes = []
        for _ in range(count):
            code = cls._make_code()
            plaintext_codes.append(code)
            cls.objects.create(user=user, code_hash=cls._hash(code))
        return plaintext_codes

    @staticmethod
    def _make_code() -> str:
        """Return a human-readable recovery code: XXXX-XXXX-XXXX (hex groups)."""
        raw = secrets.token_hex(6)   # 12 hex chars
        return f"{raw[:4].upper()}-{raw[4:8].upper()}-{raw[8:12].upper()}"

    @staticmethod
    def _hash(code: str) -> str:
        return hashlib.sha256(code.encode()).hexdigest()

    @classmethod
    def redeem(cls, user, code: str):
        """
        Attempt to redeem a recovery code.  Returns the record if valid,
        None otherwise.  Marks the code as used on success.
        """
        code_hash = cls._hash(code.strip().upper())
        try:
            rec = cls.objects.get(user=user, code_hash=code_hash, used_at__isnull=True)
        except cls.DoesNotExist:
            return None
        rec.used_at = timezone.now()
        rec.save(update_fields=["used_at"])
        return rec

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()
