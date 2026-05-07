from django.conf import settings
from django.db import models
from apps.accounts.tenancy import TenantManager
from apps.accounts.models import Person
from apps.popia.choices import LawfulBasis, RetentionPolicy
from apps.properties.models import Unit


class Lease(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        TERMINATED = "terminated", "Terminated"
        PENDING = "pending", "Pending"

    # Owning agency / tenant — denormalised from unit.property.agency for query speed.
    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="leases",
        help_text="Owning agency / tenant. Lease records never cross agencies.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.CONTRACT,
        help_text="POPIA s11 basis. Lease = performance of contract.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.LEASE_LIFETIME,
        help_text="POPIA s14 retention obligation.",
    )

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="leases")

    # Primary signatory — financially responsible, may or may not have a portal login
    primary_tenant = models.ForeignKey(
        Person, on_delete=models.CASCADE, related_name="leases_as_primary",
        null=True, blank=True  # nullable during migration; tighten once data is clean
    )

    start_date = models.DateField()
    end_date = models.DateField()
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    deposit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)

    # Utility terms
    max_occupants = models.PositiveSmallIntegerField(default=1)
    water_included = models.BooleanField(default=True)
    water_limit_litres = models.PositiveIntegerField(default=4000)
    electricity_prepaid = models.BooleanField(default=True)

    # Termination terms
    notice_period_days = models.PositiveSmallIntegerField(default=20)
    early_termination_penalty_months = models.PositiveSmallIntegerField(default=3)

    # Renewal tracking — set when a renewal addendum is created
    renewal_start_date = models.DateField(null=True, blank=True, help_text="Start of renewed period; dots after this date shown as unsigned/pending")

    # Succession chain — links a newly drafted lease back to the one it follows
    previous_lease = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="successor_lease",
    )

    # Human-readable lease reference, e.g. L-202601-0001 (auto-generated on import)
    lease_number = models.CharField(max_length=50, blank=True)

    # RHA s5(3) mandatory clause fields
    escalation_clause = models.TextField(
        blank=True,
        default="",
        help_text="RHA s5(3)(f): describes the annual rent escalation provision (e.g. CPI-linked or fixed %)",
    )
    renewal_clause = models.TextField(
        blank=True,
        default="",
        help_text="RHA s5(3)(f): describes renewal terms and options at lease expiry",
    )
    domicilium_address = models.TextField(
        blank=True,
        default="",
        help_text="RHA s5(3): domicilium citandi et executandi — address for formal legal notices to the tenant",
    )

    # Payment terms
    rent_due_day = models.PositiveSmallIntegerField(default=1, help_text="Day of month rent is due (1–28)")
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text=(
            "Payment reference for the primary tenant's rent EFT. "
            "Co-tenants have their own payment_reference on LeaseTenant."
        ),
    )

    # Raw AI extraction result stored for audit / re-use
    ai_parse_result = models.JSONField(null=True, blank=True)

    # RHA compliance gate — populated by refresh_rha_flags()
    rha_flags = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "List of RHA compliance flags. Each flag: "
            "{code, section, severity ('blocking'|'advisory'), message, field}. "
            "Blocking flags prevent finalize / send-for-signing."
        ),
    )
    # Set when blocking flags are overridden by an authorised user
    rha_override = models.JSONField(
        null=True,
        blank=True,
        help_text=(
            "If blocking flags were overridden, stores "
            "{user_id, user_email, reason, overridden_at, flags_at_override}."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agency", "status"], name="lease_agency_status_idx"),
            models.Index(fields=["agency", "end_date"], name="lease_agency_end_date_idx"),
        ]

    def __str__(self):
        name = self.primary_tenant.full_name if self.primary_tenant else "Unknown"
        return f"Lease: {name} @ {self.unit}"

    # ── RHA compliance helpers ─────────────────────────────────────────── #

    def refresh_rha_flags(self) -> list:
        """
        Re-run all RHA compliance checks against this lease, persist the results
        to ``rha_flags``, and return the new flag list.

        Clears any existing ``rha_override`` if the flag set has changed since
        the override was recorded (i.e. the operator must re-override after fixing
        some but not all issues).
        """
        from apps.leases.rha_check import run_rha_checks

        new_flags = run_rha_checks(self)

        # If override exists, check whether the blocking flag set has changed.
        # Any change (more or fewer blocking codes) invalidates the override so
        # the operator must explicitly re-confirm.
        if self.rha_override:
            old_blocking_codes = {
                f["code"]
                for f in (self.rha_override.get("flags_at_override") or [])
                if f.get("severity") == "blocking"
            }
            new_blocking_codes = {
                f["code"] for f in new_flags if f.get("severity") == "blocking"
            }
            if old_blocking_codes != new_blocking_codes:
                self.rha_override = None

        self.rha_flags = new_flags
        self.save(update_fields=["rha_flags", "rha_override"])
        return new_flags

    def blocking_rha_flags(self) -> list:
        """Return only the blocking flags from the cached ``rha_flags`` list."""
        return [f for f in (self.rha_flags or []) if f.get("severity") == "blocking"]

    def assert_rha_ready(self) -> None:
        """
        Raise ``ValueError`` if this lease has unresolved blocking RHA flags
        and no active override.

        Call this before finalise / send-for-signing.
        """
        if self.rha_override:
            return
        blocking = self.blocking_rha_flags()
        if blocking:
            codes = ", ".join(f["code"] for f in blocking)
            raise ValueError(
                f"Lease has {len(blocking)} blocking RHA compliance flag(s): {codes}. "
                "Resolve these issues or record an authorised override before proceeding."
            )

    def record_rha_override(self, user, reason: str) -> None:
        """
        Record a staff-authorised override for the current blocking flags.

        Only ``is_staff``, ``is_superuser``, or ``role == 'agency_admin'`` users
        may call this.  A non-empty *reason* is required for audit purposes.

        Raises:
            PermissionError: if *user* lacks the required role/flag.
            ValueError: if *reason* is empty or there are no blocking flags to override.
        """
        from django.utils import timezone

        # Permission check
        allowed_roles = {"agency_admin", "admin"}
        is_authorised = (
            getattr(user, "is_staff", False)
            or getattr(user, "is_superuser", False)
            or getattr(user, "role", None) in allowed_roles
        )
        if not is_authorised:
            raise PermissionError(
                "Only staff or agency_admin users may override RHA compliance flags."
            )

        if not reason or not reason.strip():
            raise ValueError("A non-empty reason is required to override RHA flags.")

        blocking = self.blocking_rha_flags()
        if not blocking:
            raise ValueError("No blocking RHA flags are present — nothing to override.")

        self.rha_override = {
            "user_id": user.pk,
            "user_email": getattr(user, "email", str(user)),
            "reason": reason.strip(),
            "overridden_at": timezone.now().isoformat(),
            "flags_at_override": list(self.rha_flags or []),
        }
        self.save(update_fields=["rha_override"])

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


class MoveInChecklistItem(models.Model):
    """
    Tracks completion of a single move-in prep task per lease.
    Items are created automatically when a lease becomes active.
    """

    class ItemKey(models.TextChoices):
        KEYS_HANDOVER = "keys_handover", "Keys handed over"
        UTILITIES_NOTIFIED = "utilities_notified", "Utilities notified"
        TENANT_APP_INVITE = "tenant_app_invite", "Tenant app invite sent"
        WELCOME_PACK = "welcome_pack", "Welcome pack delivered"

    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="move_in_checklist_items",
        help_text="Owning agency / tenant. Inherited from lease.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.CONTRACT,
        help_text="POPIA s11 basis.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.LEASE_LIFETIME,
        help_text="POPIA s14 retention obligation.",
    )

    lease = models.ForeignKey(
        Lease, on_delete=models.CASCADE, related_name="move_in_checklist"
    )
    key = models.CharField(max_length=30, choices=ItemKey.choices)
    is_completed = models.BooleanField(default=False)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="move_in_items_completed",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("lease", "key")]
        ordering = ["key"]
        indexes = [
            models.Index(fields=["agency", "is_completed"], name="movein_agency_done_idx"),
        ]

    def __str__(self):
        status = "Done" if self.is_completed else "Pending"
        return f"{self.get_key_display()} [{status}] — Lease {self.lease_id}"

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


# Default ordered list of move-in checklist items to seed on activation.
MOVE_IN_CHECKLIST_DEFAULTS = [
    MoveInChecklistItem.ItemKey.KEYS_HANDOVER,
    MoveInChecklistItem.ItemKey.UTILITIES_NOTIFIED,
    MoveInChecklistItem.ItemKey.TENANT_APP_INVITE,
    MoveInChecklistItem.ItemKey.WELCOME_PACK,
]


class LeaseTemplate(models.Model):
    """Reusable DOCX template for generating lease agreements."""
    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="lease_templates",
        help_text="Owning agency / tenant. Templates never cross agencies.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.CONTRACT,
        help_text="POPIA s11 basis.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.LEASE_LIFETIME,
        help_text="POPIA s14 retention obligation.",
    )
    name = models.CharField(max_length=200)
    version = models.CharField(max_length=20, default="1.0")
    province = models.CharField(max_length=100, blank=True, help_text="Leave blank for national template")
    docx_file = models.FileField(upload_to="lease_templates/")
    fields_schema = models.JSONField(default=list, help_text="List of merge field names in the template")
    content_html = models.TextField(blank=True, default="", help_text="Manually edited HTML content (overrides DOCX render)")
    header_html  = models.TextField(blank=True, default="", help_text="HTML shown at the top of every page (logo, title, etc.)")
    footer_html  = models.TextField(blank=True, default="", help_text="HTML shown at the bottom of every page (company name, page number)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["agency", "name"], name="leasetmpl_agency_name_idx"),
        ]

    def __str__(self):
        return f"{self.name} v{self.version}"

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


class LeaseBuilderSession(models.Model):
    """Tracks an in-progress AI-assisted lease building conversation."""

    class Status(models.TextChoices):
        DRAFTING = "drafting", "Drafting"
        REVIEW = "review", "Review"
        FINALIZED = "finalized", "Finalized"

    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="lease_builder_sessions",
        help_text="Owning agency / tenant.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.CONTRACT,
        help_text="POPIA s11 basis.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.LEASE_LIFETIME,
        help_text="POPIA s14 retention obligation.",
    )

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
        indexes = [
            models.Index(fields=["agency", "status"], name="builder_agency_status_idx"),
        ]

    def __str__(self):
        return f"BuilderSession #{self.id} by {self.created_by} ({self.status})"

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


class LeaseTenant(models.Model):
    """
    Additional legal signatories on a lease (jointly and severally liable).
    The primary signatory is Lease.primary_tenant.
    Up to 3 additional co-tenants (4 total per unit).
    A Person can appear on multiple leases over time (renewals, different units).
    """
    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="lease_co_tenants",
        help_text="Owning agency / tenant. Inherited from lease.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.CONTRACT,
        help_text="POPIA s11 basis.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.LEASE_LIFETIME,
        help_text="POPIA s14 retention obligation.",
    )

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="co_tenants")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="co_tenancies")
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Payment reference for this lessee's rent EFT.",
    )

    class Meta:
        unique_together = [("lease", "person")]
        indexes = [
            models.Index(fields=["agency", "lease"], name="cotenant_agency_lease_idx"),
        ]

    def __str__(self):
        return f"Co-tenant: {self.person.full_name} on Lease {self.lease_id}"

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


class LeaseOccupant(models.Model):
    """
    Person physically residing in the unit.
    May differ from the tenants (e.g. student whose parent signs, or employee
    whose company signs). A person can be an occupant across multiple lease periods.
    """
    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="lease_occupants",
        help_text="Owning agency / tenant. Inherited from lease.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.CONTRACT,
        help_text="POPIA s11 basis.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.LEASE_LIFETIME,
        help_text="POPIA s14 retention obligation.",
    )

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="occupants")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="occupancies")
    relationship_to_tenant = models.CharField(
        max_length=50, blank=True,
        help_text="e.g. self, spouse, child, employee, student"
    )

    class Meta:
        unique_together = [("lease", "person")]
        indexes = [
            models.Index(fields=["agency", "lease"], name="occupant_agency_lease_idx"),
        ]

    def __str__(self):
        return f"Occupant: {self.person.full_name} on Lease {self.lease_id}"

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


class LeaseGuarantor(models.Model):
    """
    Surety / guarantor covering a specific signatory's obligations on a lease.
    """
    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="lease_guarantors",
        help_text="Owning agency / tenant. Inherited from lease.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.CONTRACT,
        help_text="POPIA s11 basis.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.LEASE_LIFETIME,
        help_text="POPIA s14 retention obligation.",
    )

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="guarantors")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="guarantees")
    covers_tenant = models.ForeignKey(
        Person, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="covered_by_guarantors",
        help_text="Which tenant's obligations this guarantor covers"
    )

    class Meta:
        indexes = [
            models.Index(fields=["agency", "lease"], name="guarantor_agency_lease_idx"),
        ]

    def __str__(self):
        return f"Guarantor: {self.person.full_name} for Lease {self.lease_id}"

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


class ReusableClause(models.Model):
    """A saved paragraph or clause that can be inserted into any lease template."""

    CATEGORIES = [
        ("parties",    "Parties"),
        ("premises",   "Premises"),
        ("financial",  "Financial"),
        ("utilities",  "Utilities"),
        ("legal",      "Legal / Compliance"),
        ("signatures", "Signatures"),
        ("general",    "General"),
    ]

    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="reusable_clauses",
        help_text="Owning agency / tenant. Clauses never cross agencies.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.CONTRACT,
        help_text="POPIA s11 basis.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.LEASE_LIFETIME,
        help_text="POPIA s14 retention obligation.",
    )

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=CATEGORIES, default="general")
    html = models.TextField(help_text="HTML content using allowed Tiptap tags")
    tags = models.JSONField(default=list, blank=True)
    source_templates = models.ManyToManyField(
        LeaseTemplate, blank=True, related_name="clauses",
        help_text="Templates this clause was sourced from or used in"
    )
    use_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="clauses"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-use_count", "-created_at"]
        indexes = [
            models.Index(fields=["agency", "category"], name="clause_agency_category_idx"),
        ]

    def __str__(self):
        return self.title

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


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

    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="lease_events",
        help_text="Owning agency / tenant. Inherited from lease.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.CONTRACT,
        help_text="POPIA s11 basis.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.LEASE_LIFETIME,
        help_text="POPIA s14 retention obligation.",
    )

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
        indexes = [
            models.Index(fields=["agency", "date"], name="leaseevent_agency_date_idx"),
        ]

    def __str__(self):
        return f"{self.title} — {self.date}"

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


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

    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="onboarding_steps",
        help_text="Owning agency / tenant. Inherited from lease.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.CONTRACT,
        help_text="POPIA s11 basis.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.LEASE_LIFETIME,
        help_text="POPIA s14 retention obligation.",
    )

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="onboarding_steps")
    step_type = models.CharField(max_length=25, choices=StepType.choices)
    title = models.CharField(max_length=200)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    notes = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order"]
        indexes = [
            models.Index(fields=["agency", "is_completed"], name="onboard_agency_done_idx"),
        ]

    def __str__(self):
        status = "Done" if self.is_completed else "Pending"
        return f"{self.title} [{status}]"

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


class InventoryTemplate(models.Model):
    """Reusable preset list of items to copy into a new lease inventory."""
    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="inventory_templates",
        help_text="Owning agency / tenant.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.CONTRACT,
        help_text="POPIA s11 basis.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.LEASE_LIFETIME,
        help_text="POPIA s14 retention obligation.",
    )

    name = models.CharField(max_length=200, help_text="e.g. 'Furnished flat', 'Unfurnished house'")
    items = models.JSONField(
        default=list,
        help_text='[{"name": "Fridge", "category": "appliance", "qty": 1, "notes": "Samsung 350L"}]',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="inventory_templates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["agency", "name"], name="invtmpl_agency_name_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({len(self.items)} items)"

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


class InventoryItem(models.Model):
    """Individual item tracked per lease period — condition at move-in vs move-out."""

    class Category(models.TextChoices):
        APPLIANCE   = "appliance",   "Appliance"
        FURNITURE   = "furniture",   "Furniture"
        FIXTURE     = "fixture",     "Fixture"
        ELECTRONICS = "electronics", "Electronics"
        LINEN       = "linen",       "Linen / Bedding"
        KITCHEN     = "kitchen",     "Kitchenware"
        KEYS        = "keys",        "Keys / Remotes"
        OTHER       = "other",       "Other"

    class Condition(models.TextChoices):
        NEW       = "new",       "New"
        GOOD      = "good",      "Good"
        FAIR      = "fair",      "Fair"
        POOR      = "poor",      "Poor"
        DAMAGED   = "damaged",   "Damaged"
        MISSING   = "missing",   "Missing"

    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="inventory_items",
        help_text="Owning agency / tenant. Inherited from lease.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.CONTRACT,
        help_text="POPIA s11 basis.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.LEASE_LIFETIME,
        help_text="POPIA s14 retention obligation.",
    )

    lease       = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="inventory_items")
    name        = models.CharField(max_length=200)
    category    = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    quantity    = models.PositiveSmallIntegerField(default=1)
    barcode     = models.CharField(max_length=100, blank=True, help_text="Barcode / serial / asset tag")
    notes       = models.TextField(blank=True, help_text="Description, brand, model, serial number")
    condition_in  = models.CharField(max_length=10, choices=Condition.choices, default=Condition.GOOD, help_text="Condition at move-in")
    condition_out = models.CharField(max_length=10, choices=Condition.choices, blank=True, help_text="Condition at move-out")
    photo_in    = models.ImageField(upload_to="inventory/in/", null=True, blank=True)
    photo_out   = models.ImageField(upload_to="inventory/out/", null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "name"]
        indexes = [
            models.Index(fields=["agency", "lease"], name="invitem_agency_lease_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_condition_in_display()})"

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


class PdfRenderJob(models.Model):
    """
    Tracks async PDF render requests that could not be completed synchronously
    (e.g. because Gotenberg was unavailable).

    A background thread retries the render up to MAX_ATTEMPTS times with
    exponential back-off.  Once the PDF is ready the operator can download it
    from the admin UI; if all retries fail the status is set to FAILED.
    """

    class Status(models.TextChoices):
        PENDING  = "pending",   "Pending"
        RUNNING  = "running",   "Running"
        DONE     = "done",      "Done"
        FAILED   = "failed",    "Failed"

    MAX_ATTEMPTS = 3

    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="pdf_render_jobs",
        help_text="Owning agency / tenant. Inherited from template.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.OPERATOR_INSTRUCTION,
        help_text="POPIA s21 — Klikk processes on agency operator instruction.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.NONE,
        help_text="System-internal render job — no automated retention.",
    )

    # Which template was being exported (nullable — future-proof for other callers)
    template = models.ForeignKey(
        LeaseTemplate,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="render_jobs",
    )

    # The full HTML payload so the retry worker can attempt without re-rendering
    html_payload = models.TextField(help_text="Full HTML sent to Gotenberg")

    status   = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    error    = models.TextField(blank=True)

    # Set by the background worker once the PDF is ready
    result_pdf = models.FileField(upload_to="render_jobs/", null=True, blank=True)

    # Who triggered this render (for the admin UI)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="pdf_render_jobs",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agency", "status"], name="pdfjob_agency_status_idx"),
        ]

    def __str__(self):
        tmpl = self.template.name if self.template else "unknown"
        return f"PdfRenderJob #{self.id} [{self.status}] — {tmpl}"

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()


class LeaseDocument(models.Model):
    class DocumentType(models.TextChoices):
        SIGNED_LEASE = "signed_lease", "Signed Lease"
        ID_COPY = "id_copy", "ID Copy"
        OTHER = "other", "Other"

    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="lease_documents",
        help_text="Owning agency / tenant. Inherited from lease.agency.",
    )
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.CONTRACT,
        help_text="POPIA s11 basis.",
    )
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.LEASE_LIFETIME,
        help_text="POPIA s14 retention obligation.",
    )

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    file = models.FileField(upload_to="lease_documents/")
    description = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey("accounts.Person", on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["agency", "document_type"], name="leasedoc_agency_type_idx"),
        ]

    def __str__(self):
        return f"{self.get_document_type_display()} — Lease {self.lease_id}"

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()
