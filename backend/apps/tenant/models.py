from datetime import date

from django.conf import settings
from django.db import models

from apps.accounts.models import Person
from apps.leases.models import Lease
from apps.properties.models import Property, Unit


class TenantOnboarding(models.Model):
    """
    Tracks the onboarding checklist for a tenant after their lease is signed.

    Created automatically when a Lease moves to `active` status (via signal)
    or created manually by an agent. Each boolean flag represents one step
    the agent must complete to fully onboard the tenant.

    When all v1 items are ticked, the lease is set to `active` and the unit
    to `occupied` via the signal in leases/signals.py (already wired).

    v2 items (incoming inspection, trust account deposit banking) are stored
    but not included in the completion calculation.
    """

    lease = models.OneToOneField(
        Lease,
        on_delete=models.CASCADE,
        related_name="onboarding",
        help_text="The lease this onboarding checklist belongs to.",
    )

    # ── v1 checklist items ────────────────────────────────────────────────────
    welcome_pack_sent = models.BooleanField(
        default=False,
        help_text="Welcome pack / house rules document sent to tenant.",
    )
    welcome_pack_sent_at = models.DateTimeField(null=True, blank=True)

    deposit_received = models.BooleanField(
        default=False,
        help_text="Deposit payment received from tenant.",
    )
    deposit_received_at = models.DateTimeField(null=True, blank=True)
    deposit_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Actual amount received (may differ from lease deposit).",
    )

    first_rent_scheduled = models.BooleanField(
        default=False,
        help_text="First rent payment scheduled / confirmed.",
    )
    first_rent_scheduled_at = models.DateTimeField(null=True, blank=True)

    keys_handed_over = models.BooleanField(
        default=False,
        help_text="Physical keys / access codes handed to tenant.",
    )
    keys_handed_over_at = models.DateTimeField(null=True, blank=True)

    emergency_contacts_captured = models.BooleanField(
        default=False,
        help_text="Emergency contact details captured on the tenant record.",
    )
    emergency_contacts_captured_at = models.DateTimeField(null=True, blank=True)

    # ── v2 deferred items (stored, excluded from progress calc) ───────────────
    incoming_inspection_booked = models.BooleanField(
        default=False,
        help_text="[v2 deferred] Incoming inspection appointment booked.",
    )
    incoming_inspection_booked_at = models.DateTimeField(null=True, blank=True)

    deposit_banked_trust = models.BooleanField(
        default=False,
        help_text="[v2 deferred] Deposit transferred to trust account.",
    )
    deposit_banked_trust_at = models.DateTimeField(null=True, blank=True)

    # ── Metadata ──────────────────────────────────────────────────────────────
    notes = models.TextField(blank=True, help_text="Agent notes about this onboarding.")
    completed_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Set automatically when all v1 items are ticked.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tenant Onboarding"
        verbose_name_plural = "Tenant Onboardings"

    def __str__(self) -> str:
        return f"Onboarding for {self.lease}"

    # ── v1 items used for progress % calculation ──────────────────────────────
    V1_ITEMS: tuple[str, ...] = (
        "welcome_pack_sent",
        "deposit_received",
        "first_rent_scheduled",
        "keys_handed_over",
        "emergency_contacts_captured",
    )

    @property
    def progress(self) -> int:
        """Return completion percentage (0–100) based on v1 items only."""
        done = sum(1 for field in self.V1_ITEMS if getattr(self, field))
        return round(done / len(self.V1_ITEMS) * 100)

    @property
    def is_complete(self) -> bool:
        """True when all v1 checklist items are ticked."""
        return all(getattr(self, field) for field in self.V1_ITEMS)


class Tenant(models.Model):
    """
    Canonical tenant record. Bridges Person (legal identity) and
    User (portal login) into a single queryable entity.

    A Person becomes a Tenant when a property owner or agent registers them
    in the system — either by creating the record manually, or by deriving
    it from an existing Lease via assign_from_lease().
    """

    person = models.OneToOneField(
        Person,
        on_delete=models.CASCADE,
        related_name="tenant_profile",
        help_text="Legal identity — must already exist as a Person record.",
    )
    linked_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_records",
        help_text=(
            "Portal login account (optional — not all tenants have portal access). "
            "Link this once the tenant has been invited and accepted."
        ),
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Is this tenant currently active in the system?",
    )
    notes = models.TextField(blank=True, help_text="Agent notes about this tenant.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["person__full_name"]
        verbose_name = "Tenant"
        verbose_name_plural = "Tenants"

    def __str__(self) -> str:
        return f"Tenant: {self.person.full_name}"

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def current_assignment(self) -> "TenantUnitAssignment | None":
        """
        Return the active TenantUnitAssignment for today, or None.

        An assignment is considered active when:
          - start_date <= today
          - end_date is null (open-ended) OR end_date >= today
        """
        today = date.today()
        return (
            self.assignments.filter(start_date__lte=today)
            .filter(models.Q(end_date__isnull=True) | models.Q(end_date__gte=today))
            .select_related("unit", "property")
            .first()
        )

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------

    def assign_unit(
        self,
        unit: Unit,
        start_date: date,
        end_date: "date | None" = None,
        assigned_by=None,
        notes: str = "",
    ) -> "TenantUnitAssignment":
        """
        Manually assign this tenant to a unit for a date range.

        Called by property owners or agents directly, without requiring
        a lease agreement.

        Args:
            unit:        The Unit the tenant will occupy.
            start_date:  Inclusive start of occupancy.
            end_date:    Inclusive end of occupancy. Pass None for open-ended.
            assigned_by: The User (agent/admin) creating this assignment.
            notes:       Optional free-text context.

        Returns:
            The newly created TenantUnitAssignment.

        Raises:
            ValueError: If end_date is before start_date.
            ValueError: If an overlapping assignment already exists for
                        this (tenant, unit) combination. The caller must
                        explicitly end the prior assignment before creating
                        a new one.
        """
        if end_date is not None and end_date < start_date:
            raise ValueError(
                f"end_date ({end_date}) must be on or after start_date ({start_date})."
            )

        # Detect overlapping assignments for this tenant on the same unit.
        # An open assignment (end_date=None) overlaps any new range.
        overlap_qs = TenantUnitAssignment.objects.filter(tenant=self, unit=unit).filter(
            models.Q(start_date__lte=end_date if end_date else date.max)
            & (
                models.Q(end_date__isnull=True)
                | models.Q(end_date__gte=start_date)
            )
        )
        if overlap_qs.exists():
            raise ValueError(
                f"Tenant '{self}' already has an overlapping assignment to "
                f"unit '{unit}' in the requested date range. "
                "Please end the existing assignment first."
            )

        return TenantUnitAssignment.objects.create(
            tenant=self,
            unit=unit,
            property=unit.property,
            lease=None,
            start_date=start_date,
            end_date=end_date,
            assigned_by=assigned_by,
            source=TenantUnitAssignment.Source.MANUAL,
            notes=notes,
        )

    def assign_from_lease(self, lease: Lease) -> "TenantUnitAssignment":
        """
        Derive a TenantUnitAssignment from an existing Lease record.

        Mirrors the lease's unit, start_date, and end_date. Idempotent:
        calling this method twice for the same lease returns the existing
        assignment without creating a duplicate.

        Args:
            lease: The Lease to derive the assignment from.

        Returns:
            A TenantUnitAssignment (new or existing).

        Raises:
            ValueError: If the lease has no unit.
            ValueError: If lease.primary_tenant does not match this
                        Tenant's Person record.
            ValueError: If a conflicting (non-lease) assignment exists
                        for the same (tenant, unit) date range.
        """
        if lease.unit is None:
            raise ValueError(f"Lease #{lease.pk} has no unit assigned.")

        if lease.primary_tenant_id != self.person_id:
            raise ValueError(
                f"Lease #{lease.pk} primary_tenant does not match this "
                f"Tenant's person record. Cannot assign."
            )

        # Idempotency: return existing if already linked to this lease.
        existing = TenantUnitAssignment.objects.filter(lease=lease).first()
        if existing is not None:
            return existing

        # Check for overlapping assignments from other sources.
        overlap_qs = TenantUnitAssignment.objects.filter(
            tenant=self, unit=lease.unit
        ).filter(
            models.Q(start_date__lte=lease.end_date if lease.end_date else date.max)
            & (
                models.Q(end_date__isnull=True)
                | models.Q(end_date__gte=lease.start_date)
            )
        )
        if overlap_qs.exists():
            raise ValueError(
                f"Tenant '{self}' already has an overlapping assignment to "
                f"unit '{lease.unit}' for the lease date range "
                f"({lease.start_date} → {lease.end_date or 'open'}). "
                "Please resolve the conflict before syncing from this lease."
            )

        return TenantUnitAssignment.objects.create(
            tenant=self,
            unit=lease.unit,
            property=lease.unit.property,
            lease=lease,
            start_date=lease.start_date,
            end_date=lease.end_date,
            assigned_by=None,
            source=TenantUnitAssignment.Source.LEASE,
            notes="",
        )

    @classmethod
    def get_or_create_for_lease(cls, lease: Lease) -> "Tenant":
        """
        Ensure a Tenant record exists for a lease's primary_tenant.

        Convenience helper: given a Lease, finds or creates the Tenant
        for its primary_tenant Person. Useful before calling assign_from_lease().

        Args:
            lease: The Lease whose primary_tenant to look up.

        Returns:
            The existing or newly created Tenant.

        Raises:
            ValueError: If the lease has no primary_tenant.
        """
        if lease.primary_tenant is None:
            raise ValueError(
                f"Lease #{lease.pk} has no primary_tenant — "
                "cannot derive a Tenant record."
            )
        tenant, _ = cls.objects.get_or_create(person=lease.primary_tenant)
        return tenant


class TenantUnitAssignment(models.Model):
    """
    Temporal record of a tenant occupying a unit for a date range.

    Each row answers: "Person X was the tenant of Unit Y from Date A to Date B."

    Assignments can be created in two ways:
    - MANUAL: A property owner or agent assigns a tenant directly (no lease needed).
    - LEASE:  Derived from a Lease record via Tenant.assign_from_lease().

    The `property` field is denormalized from `unit.property` at creation time
    for query efficiency (e.g. "all tenants in Property X") and historical
    accuracy (captures the property relationship as it was at assignment time).
    """

    class Source(models.TextChoices):
        MANUAL = "manual", "Manual"
        LEASE = "lease", "From Lease"

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="tenant_assignments",
        help_text="The unit occupied. Cannot be deleted while assignments exist.",
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.PROTECT,
        related_name="tenant_assignments",
        help_text=(
            "Denormalized from unit.property at assignment time. "
            "Do not edit directly."
        ),
    )
    lease = models.ForeignKey(
        Lease,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_assignment",
        help_text="Set when this assignment was derived from a specific lease.",
    )
    start_date = models.DateField(help_text="Inclusive start of occupancy.")
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Inclusive end of occupancy. Leave blank for open-ended (current).",
    )
    source = models.CharField(
        max_length=10,
        choices=Source.choices,
        default=Source.MANUAL,
        help_text="How this assignment was created.",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_assignments_created",
        help_text=(
            "Agent or admin who created this assignment. "
            "Null for lease-derived assignments."
        ),
    )
    notes = models.TextField(blank=True, help_text="Optional context for this assignment.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "Unit Assignment"
        verbose_name_plural = "Unit Assignments"
        indexes = [
            models.Index(fields=["tenant", "start_date"], name="tenant_assign_tenant_date_idx"),
            models.Index(fields=["unit", "start_date"], name="tenant_assign_unit_date_idx"),
        ]

    def __str__(self) -> str:
        end = str(self.end_date) if self.end_date else "present"
        return f"{self.tenant} @ {self.unit} ({self.start_date} → {end})"
