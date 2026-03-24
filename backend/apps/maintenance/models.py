from django.db import models
from apps.accounts.models import User
from apps.properties.models import Unit


class Supplier(models.Model):
    class Trade(models.TextChoices):
        PLUMBING = "plumbing", "Plumbing"
        ELECTRICAL = "electrical", "Electrical"
        CARPENTRY = "carpentry", "Carpentry"
        PAINTING = "painting", "Painting"
        ROOFING = "roofing", "Roofing"
        HVAC = "hvac", "HVAC"
        LOCKSMITH = "locksmith", "Locksmith"
        PEST_CONTROL = "pest_control", "Pest Control"
        LANDSCAPING = "landscaping", "Landscaping"
        APPLIANCE = "appliance", "Appliance Repair"
        GENERAL = "general", "General Maintenance"
        SECURITY = "security", "Security"
        CLEANING = "cleaning", "Cleaning"
        OTHER = "other", "Other"

    # Core
    name = models.CharField(max_length=200, help_text="Contact person name")
    company_name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    # Address
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=50, blank=True)

    # Geolocation — for map display and proximity matching
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
    )
    service_radius_km = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="How far this supplier is willing to travel (km)",
    )

    # Compliance
    bee_level = models.CharField(max_length=10, blank=True, help_text="e.g. Level 1")
    cidb_grading = models.CharField(max_length=20, blank=True, help_text="e.g. 3CE")
    insurance_expiry = models.DateField(null=True, blank=True)
    insurance_details = models.TextField(blank=True)

    # Banking
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=30, blank=True)
    branch_code = models.CharField(max_length=10, blank=True)
    account_type = models.CharField(max_length=20, blank=True, help_text="savings / cheque")

    # Performance
    rating = models.DecimalField(
        max_digits=2, decimal_places=1, null=True, blank=True,
        help_text="1.0–5.0 average rating",
    )

    # AI enrichment — stores indexed profile data for smart supplier-job matching
    ai_profile = models.JSONField(
        null=True, blank=True,
        help_text="AI-enriched profile: specialities, past job summaries, strengths, availability patterns",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        if self.company_name:
            return f"{self.company_name} ({self.name})"
        return self.name

    @property
    def display_name(self):
        return self.company_name or self.name

    @property
    def trade_list(self):
        return list(self.trades.values_list("trade", flat=True))


class SupplierTrade(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="trades")
    trade = models.CharField(max_length=30, choices=Supplier.Trade.choices)

    class Meta:
        unique_together = [("supplier", "trade")]
        ordering = ["trade"]

    def __str__(self):
        return f"{self.supplier} — {self.get_trade_display()}"


class MaintenanceRequest(models.Model):
    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="maintenance_requests")
    tenant = models.ForeignKey(User, on_delete=models.CASCADE, related_name="maintenance_requests")
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_requests",
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.OPEN)
    image = models.ImageField(upload_to="maintenance/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} — {self.unit}"
