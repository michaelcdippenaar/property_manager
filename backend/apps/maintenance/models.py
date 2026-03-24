from django.db import models
from apps.accounts.models import User
from apps.properties.models import Property, Unit


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
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    # Address
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=50, blank=True)

    # Geolocation
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
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

    # AI enrichment
    ai_profile = models.JSONField(
        null=True, blank=True,
        help_text="AI-enriched profile for smart supplier-job matching",
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


class SupplierDocument(models.Model):
    class DocumentType(models.TextChoices):
        BANK_CONFIRMATION = "bank_confirmation", "Bank Confirmation"
        BEE_CERTIFICATE = "bee_certificate", "BEE Certificate"
        INSURANCE = "insurance", "Insurance Certificate"
        CIDB = "cidb", "CIDB Registration"
        COMPANY_REG = "company_reg", "Company Registration"
        TAX_CLEARANCE = "tax_clearance", "Tax Clearance"
        OTHER = "other", "Other"

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    file = models.FileField(upload_to="supplier_documents/")
    description = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.supplier} — {self.get_document_type_display()}"


class SupplierProperty(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="property_links")
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="supplier_links")
    is_preferred = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("supplier", "property")]
        ordering = ["property__name"]

    def __str__(self):
        return f"{self.supplier} → {self.property}"


class JobDispatch(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        QUOTING = "quoting", "Quoting"
        AWARDED = "awarded", "Awarded"
        CANCELLED = "cancelled", "Cancelled"

    maintenance_request = models.OneToOneField(
        "MaintenanceRequest", on_delete=models.CASCADE, related_name="dispatch",
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFT)
    dispatched_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, help_text="Notes sent to suppliers with the job")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Dispatch for {self.maintenance_request}"


class JobQuoteRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        VIEWED = "viewed", "Viewed"
        QUOTED = "quoted", "Quoted"
        DECLINED = "declined", "Declined"
        AWARDED = "awarded", "Awarded"
        EXPIRED = "expired", "Expired"

    dispatch = models.ForeignKey(JobDispatch, on_delete=models.CASCADE, related_name="quote_requests")
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="quote_requests")
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    token = models.UUIDField(unique=True, editable=False)
    notified_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    match_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    match_reasons = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("dispatch", "supplier")]
        ordering = ["-match_score"]

    def __str__(self):
        return f"Quote request → {self.supplier} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.token:
            import uuid
            self.token = uuid.uuid4()
        super().save(*args, **kwargs)


class JobQuote(models.Model):
    quote_request = models.OneToOneField(JobQuoteRequest, on_delete=models.CASCADE, related_name="quote")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, help_text="Scope of work / notes")
    estimated_days = models.PositiveIntegerField(null=True, blank=True)
    available_from = models.DateField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["amount"]

    def __str__(self):
        return f"R{self.amount} — {self.quote_request.supplier}"


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
