from django.conf import settings
from django.db import models
from apps.accounts.models import Person
from apps.properties.models import Unit


class Lease(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        TERMINATED = "terminated", "Terminated"
        PENDING = "pending", "Pending"

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="leases")

    # Primary signatory — financially responsible, may or may not have a portal login
    primary_tenant = models.ForeignKey(
        Person, on_delete=models.CASCADE, related_name="leases_as_primary",
        null=True, blank=True  # nullable during migration; tighten once data is clean
    )

    start_date = models.DateField()
    end_date = models.DateField()
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    deposit = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)

    # Utility terms
    max_occupants = models.PositiveSmallIntegerField(default=1)
    water_included = models.BooleanField(default=True)
    water_limit_litres = models.PositiveIntegerField(default=4000)
    electricity_prepaid = models.BooleanField(default=True)

    # Termination terms
    notice_period_days = models.PositiveSmallIntegerField(default=20)
    early_termination_penalty_months = models.PositiveSmallIntegerField(default=3)

    # Human-readable lease reference, e.g. L-202601-0001 (auto-generated on import)
    lease_number = models.CharField(max_length=50, blank=True)

    # Payment reference (e.g. "18 Irene - Smith")
    payment_reference = models.CharField(max_length=100, blank=True)

    # Raw AI extraction result stored for audit / re-use
    ai_parse_result = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        name = self.primary_tenant.full_name if self.primary_tenant else "Unknown"
        return f"Lease: {name} @ {self.unit}"


class LeaseTemplate(models.Model):
    """Reusable DOCX template for generating lease agreements."""
    name = models.CharField(max_length=200)
    version = models.CharField(max_length=20, default="1.0")
    province = models.CharField(max_length=100, blank=True, help_text="Leave blank for national template")
    docx_file = models.FileField(upload_to="lease_templates/")
    fields_schema = models.JSONField(default=list, help_text="List of merge field names in the template")
    content_html = models.TextField(blank=True, default="", help_text="Manually edited HTML content (overrides DOCX render)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} v{self.version}"


class LeaseBuilderSession(models.Model):
    """Tracks an in-progress AI-assisted lease building conversation."""

    class Status(models.TextChoices):
        DRAFTING = "drafting", "Drafting"
        REVIEW = "review", "Review"
        FINALIZED = "finalized", "Finalized"

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lease_builder_sessions"
    )
    template = models.ForeignKey(
        LeaseTemplate, null=True, blank=True, on_delete=models.SET_NULL
    )
    lease = models.OneToOneField(
        "Lease", null=True, blank=True, on_delete=models.SET_NULL, related_name="builder_session"
    )
    messages = models.JSONField(default=list, help_text="[{role, content}] conversation history")
    current_state = models.JSONField(default=dict, help_text="Extracted lease field values")
    rha_flags = models.JSONField(default=list, help_text="RHA compliance issues found")
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFTING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"BuilderSession #{self.id} by {self.created_by} ({self.status})"


class LeaseTenant(models.Model):
    """
    Additional legal signatories on a lease (jointly and severally liable).
    The primary signatory is Lease.primary_tenant.
    Up to 3 additional co-tenants (4 total per unit).
    A Person can appear on multiple leases over time (renewals, different units).
    """
    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="co_tenants")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="co_tenancies")

    class Meta:
        unique_together = [("lease", "person")]

    def __str__(self):
        return f"Co-tenant: {self.person.full_name} on Lease {self.lease_id}"


class LeaseOccupant(models.Model):
    """
    Person physically residing in the unit.
    May differ from the tenants (e.g. student whose parent signs, or employee
    whose company signs). A person can be an occupant across multiple lease periods.
    """
    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="occupants")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="occupancies")
    relationship_to_tenant = models.CharField(
        max_length=50, blank=True,
        help_text="e.g. self, spouse, child, employee, student"
    )

    class Meta:
        unique_together = [("lease", "person")]

    def __str__(self):
        return f"Occupant: {self.person.full_name} on Lease {self.lease_id}"


class LeaseGuarantor(models.Model):
    """
    Surety / guarantor covering a specific signatory's obligations on a lease.
    """
    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="guarantors")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="guarantees")
    covers_tenant = models.ForeignKey(
        Person, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="covered_by_guarantors",
        help_text="Which tenant's obligations this guarantor covers"
    )

    def __str__(self):
        return f"Guarantor: {self.person.full_name} for Lease {self.lease_id}"


class LeaseDocument(models.Model):
    class DocumentType(models.TextChoices):
        SIGNED_LEASE = "signed_lease", "Signed Lease"
        ID_COPY = "id_copy", "ID Copy"
        OTHER = "other", "Other"

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    file = models.FileField(upload_to="lease_documents/")
    description = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey("accounts.Person", on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.get_document_type_display()} — Lease {self.lease_id}"


class LeaseEvent(models.Model):
    """Calendar events auto-generated from lease dates."""

    class EventType(models.TextChoices):
        CONTRACT_START = "contract_start", "Contract Start"
        CONTRACT_END = "contract_end", "Contract End"
        DEPOSIT_DUE = "deposit_due", "Deposit Due"
        FIRST_RENT = "first_rent", "First Rent Due"
        RENT_DUE = "rent_due", "Rent Due"
        INSPECTION_IN = "inspection_in", "Move-in Inspection"
        INSPECTION_OUT = "inspection_out", "Move-out Inspection"
        INSPECTION_ROUTINE = "inspection_routine", "Routine Inspection"
        NOTICE_DEADLINE = "notice_deadline", "Notice Period Deadline"
        RENEWAL_REVIEW = "renewal_review", "Renewal Review"
        CUSTOM = "custom", "Custom"

    class Status(models.TextChoices):
        UPCOMING = "upcoming", "Upcoming"
        DUE = "due", "Due"
        COMPLETED = "completed", "Completed"
        OVERDUE = "overdue", "Overdue"
        CANCELLED = "cancelled", "Cancelled"

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=25, choices=EventType.choices)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateField()
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.UPCOMING)
    is_recurring = models.BooleanField(default=False)
    recurrence_day = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Day of month for recurring events",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.title} — {self.date}"


class OnboardingStep(models.Model):
    """Checklist steps auto-generated when a lease is created."""

    class StepType(models.TextChoices):
        DEPOSIT_PAYMENT = "deposit_payment", "Deposit Payment"
        LEASE_SIGNED = "lease_signed", "Lease Signed"
        ID_VERIFIED = "id_verified", "ID Verified"
        MOVE_IN_INSPECTION = "move_in_inspection", "Move-in Inspection"
        KEY_HANDOVER = "key_handover", "Key Handover"
        INVOICING_SETUP = "invoicing_setup", "Invoicing Setup"
        TENANT_APP_SETUP = "tenant_app_setup", "Tenant App Setup"
        WELCOME_SENT = "welcome_sent", "Welcome Message Sent"

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="onboarding_steps")
    step_type = models.CharField(max_length=25, choices=StepType.choices)
    title = models.CharField(max_length=200)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="completed_onboarding_steps",
    )
    notes = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        status = "Done" if self.is_completed else "Pending"
        return f"{self.title} [{status}]"
