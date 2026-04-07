import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


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
        AGENT = "agent", "Agent"
        ADMIN = "admin", "Admin"
        SUPPLIER = "supplier", "Supplier"
        OWNER = "owner", "Owner"

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    id_number = models.CharField(max_length=20, blank=True, help_text="SA ID or passport number")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.TENANT)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

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


class Person(models.Model):
    """
    A natural person or company involved in property transactions.
    May or may not have a system login (linked_user).
    Used for: property owners, tenants, co-tenants, occupants, guarantors.
    """
    class PersonType(models.TextChoices):
        INDIVIDUAL = "individual", "Individual"
        COMPANY = "company", "Company"

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
    # Company-specific
    company_reg = models.CharField(max_length=50, blank=True)
    vat_number = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


class OTPCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otp_codes")
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"OTP for {self.user.email}"


class PushToken(models.Model):
    """FCM/APNs device token for push notifications."""

    class Platform(models.TextChoices):
        IOS = "ios", "iOS"
        ANDROID = "android", "Android"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="push_tokens")
    token = models.TextField()
    platform = models.CharField(max_length=10, choices=Platform.choices)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "token")
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.platform} token for {self.user.email}"


class UserInvite(models.Model):
    email = models.EmailField()
    role = models.CharField(max_length=10, choices=User.Role.choices)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="invites_sent")
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invite for {self.email} ({self.role})"


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

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "event_type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.event_type} — {self.user_id} at {self.created_at}"


class Agency(models.Model):
    """
    Singleton agency record.  Stores the details that appear on
    mandates, leases and other generated documents.
    """
    name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=50, blank=True)
    eaab_ffc_number = models.CharField(
        max_length=50, blank=True,
        help_text="EAAB Fidelity Fund Certificate number",
    )
    contact_number = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    physical_address = models.TextField(blank=True)
    # Trust account
    trust_account_number = models.CharField(max_length=50, blank=True)
    trust_bank_name = models.CharField(max_length=100, blank=True)
    # Financial cycle
    statement_date = models.CharField(
        max_length=30, blank=True, default="the 5th",
        help_text='e.g. "the 5th"',
    )
    disbursement_date = models.CharField(
        max_length=30, blank=True, default="the 7th",
        help_text='e.g. "the 7th"',
    )
    information_officer_email = models.EmailField(blank=True)
    # Branding
    logo = models.ImageField(upload_to="agency/", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "agencies"

    def __str__(self):
        return self.name or "Agency"

    def save(self, *args, **kwargs):
        # Singleton: prevent creating a second record
        if not self.pk and Agency.objects.exists():
            raise ValueError("Only one Agency record is allowed.")
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        """Return the singleton instance, or None if not yet configured."""
        return cls.objects.first()


class LoginAttempt(models.Model):
    email = models.EmailField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    succeeded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "created_at"]),
        ]

    def __str__(self):
        return f"{'OK' if self.succeeded else 'FAIL'} login for {self.email}"
