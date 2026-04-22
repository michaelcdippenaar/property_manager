from datetime import timedelta

from django.db import models
from django.utils import timezone
from apps.accounts.models import User
from apps.properties.models import Property, Unit


# ── Default SLA hours per priority ─────────────────────────────────────────────
# Keys match MaintenanceRequest.Priority values.
# Tuple: (ack_hours, resolve_hours)
DEFAULT_SLA_HOURS: dict[str, tuple[int, int]] = {
    "urgent":  (4,   24),
    "high":    (24,  72),
    "medium":  (72,  336),   # 72h ack / 14d resolve
    "low":     (72,  336),
}


class AgencySLAConfig(models.Model):
    """
    Per-agency SLA overrides for maintenance ticket priorities.
    Falls back to DEFAULT_SLA_HOURS when no record exists for a priority.
    """
    agency = models.ForeignKey(
        "accounts.Agency", on_delete=models.CASCADE, related_name="sla_configs",
    )
    priority = models.CharField(
        max_length=10,
        choices=[
            ("urgent", "Urgent (emergency)"),
            ("high",   "High (urgent)"),
            ("medium", "Medium (routine)"),
            ("low",    "Low (routine)"),
        ],
    )
    ack_hours = models.PositiveIntegerField(help_text="Hours to first acknowledgement")
    resolve_hours = models.PositiveIntegerField(help_text="Hours to full resolution")

    class Meta:
        unique_together = [("agency", "priority")]
        ordering = ["agency", "priority"]

    def __str__(self):
        return f"{self.agency} — {self.priority}: {self.ack_hours}h/{self.resolve_hours}h"

    @classmethod
    def get_hours(cls, agency, priority: str) -> tuple[int, int]:
        """Return (ack_hours, resolve_hours) for the given agency + priority."""
        if agency:
            record = cls.objects.filter(agency=agency, priority=priority).first()
            if record:
                return record.ack_hours, record.resolve_hours
        return DEFAULT_SLA_HOURS.get(priority, (72, 336))


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

    # Login link
    linked_user = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="supplier_profile",
        help_text="System login account for supplier portal access",
    )

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

    class Category(models.TextChoices):
        PLUMBING = "plumbing", "Plumbing"
        ELECTRICAL = "electrical", "Electrical"
        ROOF = "roof", "Roof / Ceiling"
        APPLIANCE = "appliance", "Appliance"
        SECURITY = "security", "Security"
        PEST = "pest", "Pest Control"
        GARDEN = "garden", "Garden / Exterior"
        OTHER = "other", "Other"

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="maintenance_requests")
    tenant = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="maintenance_requests")
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_requests",
    )
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_maintenance_requests",
    )
    merged_into = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="merged_requests",
    )
    conversation_id_legacy = models.IntegerField(null=True, blank=True, db_column="conversation_id")
    title = models.CharField(max_length=200)
    description = models.TextField()
    ticket_reference = models.CharField(max_length=50, blank=True, default="")
    supplier_name = models.CharField(max_length=200, blank=True, default="")
    supplier_phone = models.CharField(max_length=50, blank=True, default="")
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.OPEN)
    image = models.ImageField(upload_to="maintenance/", null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    sla_ack_deadline = models.DateTimeField(
        null=True, blank=True,
        help_text="Computed: created_at + ack SLA hours for this priority",
    )
    sla_resolve_deadline = models.DateTimeField(
        null=True, blank=True,
        help_text="Computed: created_at + resolve SLA hours for this priority",
    )
    # Set True after agency admin has been alerted for >48h overdue escalation
    sla_escalated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} — {self.unit}"

    # ── SLA helpers ────────────────────────────────────────────────────────────

    def compute_sla_deadlines(self, agency=None):
        """
        Recompute and store sla_ack_deadline + sla_resolve_deadline.
        Call after priority or created_at changes.
        """
        ack_h, res_h = AgencySLAConfig.get_hours(agency, self.priority)
        base = self.created_at or timezone.now()
        self.sla_ack_deadline = base + timedelta(hours=ack_h)
        self.sla_resolve_deadline = base + timedelta(hours=res_h)

    @property
    def sla_ack_pct(self) -> float | None:
        """
        Percentage of ack SLA window remaining (0–100).
        Returns None when no deadline set or ticket already acknowledged.
        Negative values indicate overdue.
        """
        if not self.sla_ack_deadline or self.acknowledged_at:
            return None
        total = (self.sla_ack_deadline - self.created_at).total_seconds()
        if total <= 0:
            return None
        remaining = (self.sla_ack_deadline - timezone.now()).total_seconds()
        return round(remaining / total * 100, 1)

    @property
    def sla_resolve_pct(self) -> float | None:
        """
        Percentage of resolve SLA window remaining (0–100).
        Returns None when no deadline set or ticket already resolved/closed.
        Negative values indicate overdue.
        """
        if not self.sla_resolve_deadline or self.status in (self.Status.RESOLVED, self.Status.CLOSED):
            return None
        total = (self.sla_resolve_deadline - self.created_at).total_seconds()
        if total <= 0:
            return None
        remaining = (self.sla_resolve_deadline - timezone.now()).total_seconds()
        return round(remaining / total * 100, 1)

    @property
    def is_sla_overdue(self) -> bool:
        """True when resolve deadline has passed and ticket is still open/in-progress."""
        if self.status in (self.Status.RESOLVED, self.Status.CLOSED):
            return False
        if self.sla_resolve_deadline and timezone.now() > self.sla_resolve_deadline:
            return True
        return False


class MaintenanceSkill(models.Model):
    class Trade(models.TextChoices):
        PLUMBING = "plumbing", "Plumbing"
        ELECTRICAL = "electrical", "Electrical"
        CARPENTRY = "carpentry", "Carpentry"
        PAINTING = "painting", "Painting"
        HVAC = "hvac", "HVAC / Air Con"
        ROOFING = "roofing", "Roofing"
        GENERAL = "general", "General Maintenance"
        APPLIANCE = "appliance", "Appliance Repair"
        PEST = "pest", "Pest Control"
        OTHER = "other", "Other"

    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    name = models.CharField(max_length=200)
    trade = models.CharField(max_length=20, choices=Trade.choices, default=Trade.GENERAL)
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices, default=Difficulty.MEDIUM)
    symptom_phrases = models.JSONField(default=list, help_text="List of phrases that indicate this issue, used for AI matching")
    steps = models.JSONField(default=list, help_text="Ordered list of resolution steps")
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["trade", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_trade_display()})"


class AgentQuestion(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ANSWERED = "answered", "Answered"
        DISMISSED = "dismissed", "Dismissed"

    class Category(models.TextChoices):
        PROPERTY = "property", "Property Info"
        LEASE = "lease", "Lease / Contract"
        MAINTENANCE = "maintenance", "Maintenance"
        TENANT = "tenant", "Tenant"
        SUPPLIER = "supplier", "Supplier"
        POLICY = "policy", "Policy / Rules"
        OTHER = "other", "Other"

    question = models.TextField(help_text="The question the AI agent needs answered")
    answer = models.TextField(blank=True, help_text="Human-provided answer")
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    context_source = models.CharField(max_length=200, blank=True, help_text="What triggered this question, e.g. maintenance request #123")
    property = models.ForeignKey('properties.Property', on_delete=models.SET_NULL, null=True, blank=True, related_name="agent_questions")
    answered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    added_to_context = models.BooleanField(default=False, help_text="Whether the answer was synced to agent knowledge")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_status_display()}] {self.question[:80]}"


class MaintenanceActivity(models.Model):
    class ActivityType(models.TextChoices):
        NOTE = "note", "Note"
        STATUS_CHANGE = "status_change", "Status Change"
        SUPPLIER_ASSIGNED = "supplier_assigned", "Supplier Assigned"
        DISPATCH_SENT = "dispatch_sent", "Dispatch Sent"
        QUOTE_RECEIVED = "quote_received", "Quote Received"
        JOB_AWARDED = "job_awarded", "Job Awarded"
        SYSTEM = "system", "System"

    request = models.ForeignKey(
        MaintenanceRequest, on_delete=models.CASCADE, related_name="activities",
    )
    activity_type = models.CharField(max_length=30, choices=ActivityType.choices, default=ActivityType.NOTE)
    message = models.TextField(blank=True, default="")
    file = models.FileField(upload_to="maintenance/activity_files/", null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="maintenance_activities",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        db_table = "maintenance_maintenanceactivity"

    def __str__(self):
        return f"[{self.activity_type}] {self.message[:60]}"


class AgentTokenLog(models.Model):
    """
    Log every LLM API call for token usage monitoring and cost analysis.

    Tracks input/output tokens, latency, endpoint, model, and optional
    metadata (e.g. maintenance_request_id, session_id).
    """
    endpoint = models.CharField(max_length=100, db_index=True)
    model = models.CharField(max_length=80, default="claude-sonnet-4-6")
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    latency_ms = models.IntegerField(default=0, help_text="Round-trip latency in ms")
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="token_logs",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["endpoint", "created_at"]),
        ]

    def __str__(self):
        return f"TokenLog({self.endpoint}, in={self.input_tokens}, out={self.output_tokens})"

    @classmethod
    def log_call(
        cls,
        endpoint: str,
        response,
        user=None,
        latency_ms: int = 0,
        metadata: dict | None = None,
    ):
        """
        Log an Anthropic API response's token usage.

        Args:
            endpoint: identifier like "tenant_chat" or "agent_assist"
            response: Anthropic message response with .usage
            user: Django user who triggered the call
            latency_ms: measured round-trip time
            metadata: extra context (request_id, session_id, etc.)
        """
        try:
            usage = getattr(response, "usage", None)
            input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
            output_tokens = getattr(usage, "output_tokens", 0) if usage else 0
            model_name = getattr(response, "model", "unknown")

            cls.objects.create(
                endpoint=endpoint,
                model=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                user=user,
                metadata=metadata or {},
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Failed to log token usage: %s", e)


class SupplierJobAssignment(models.Model):
    """
    Scopes a supplier's access to a specific maintenance job.
    Address and tenant contact are copied at assignment time (POPIA data minimisation).
    The supplier sees this snapshot, not live access to Property/Tenant models.
    """

    class Status(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    supplier = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="job_assignments",
    )
    maintenance_request = models.ForeignKey(
        MaintenanceRequest, on_delete=models.CASCADE, related_name="supplier_assignments",
    )
    property_address = models.CharField(
        max_length=500,
        help_text="Copied at assignment time — POPIA data minimisation",
    )
    tenant_contact_name = models.CharField(max_length=200, blank=True)
    tenant_contact_phone = models.CharField(max_length=20, blank=True)
    scope_of_work = models.TextField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ASSIGNED,
    )
    assigned_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["supplier", "status"]),
        ]

    def __str__(self):
        return f"Job #{self.maintenance_request_id} → {self.supplier} ({self.status})"
