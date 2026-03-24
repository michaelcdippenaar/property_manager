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
