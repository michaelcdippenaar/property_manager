"""
Payments & Reconciliation models — RNT-QUAL-004.

Key concepts
------------
RentInvoice
    One invoice per rent period per lease.  Status follows a state machine:
    unpaid → partially_paid | paid | overpaid | reversed

RentPayment
    An individual EFT / cash receipt tied to an invoice.
    Multiple payments can aggregate against the same invoice (split payment).

UnmatchedPayment
    Deposits that cannot be auto-matched (wrong reference, no active lease).
    Operator manually assigns them; they are then converted to RentPayment rows.

PaymentAuditLog
    Immutable append-only log of every status transition on an invoice or
    payment.  Referenced by RNT-SEC-008.
"""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class RentInvoice(models.Model):
    """One monthly rent invoice per lease period."""

    class Status(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PARTIALLY_PAID = "partially_paid", "Partially Paid"
        PAID = "paid", "Paid"
        OVERPAID = "overpaid", "Overpaid"
        REVERSED = "reversed", "Reversed"

    lease = models.ForeignKey(
        "leases.Lease",
        on_delete=models.CASCADE,
        related_name="rent_invoices",
    )
    period_start = models.DateField(help_text="First day of the rent period")
    period_end = models.DateField(help_text="Last day of the rent period")
    amount_due = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Expected rent for this period (ZAR)",
    )
    # Running balance updated by reconcile(); positive = overpayment credit
    credit_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Credit carried forward from previous cycle (ZAR). Positive = tenant in credit.",
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.UNPAID,
    )
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-period_start"]
        unique_together = [("lease", "period_start")]
        indexes = [
            models.Index(fields=["lease", "status"]),
            models.Index(fields=["due_date"]),
        ]

    def __str__(self) -> str:
        return f"Invoice #{self.pk} — Lease {self.lease_id} {self.period_start} [{self.status}]"

    # ── Computed helpers ─────────────────────────────────────────────────── #

    @property
    def amount_paid(self) -> Decimal:
        """Sum of all non-reversed payment amounts against this invoice."""
        return self.payments.filter(
            status=RentPayment.Status.CLEARED
        ).aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0.00")

    @property
    def balance_remaining(self) -> Decimal:
        """Positive = still owed; negative = overpaid."""
        return self.amount_due - self.amount_paid - self.credit_balance

    @property
    def tenant_in_credit(self) -> bool:
        """True when the tenant has paid more than was due."""
        return self.balance_remaining < Decimal("0.00")


class RentPayment(models.Model):
    """
    A single EFT receipt or cash transaction applied to a RentInvoice.

    Multiple RentPayments may aggregate against one invoice (split payments,
    e.g. tenant + guarantor paying from separate accounts).
    """

    class Status(models.TextChoices):
        CLEARED = "cleared", "Cleared"
        REVERSED = "reversed", "Reversed (Bounced EFT)"

    invoice = models.ForeignKey(
        RentInvoice,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    reference = models.CharField(
        max_length=150,
        blank=True,
        help_text="Bank reference or payment ID supplied by the tenant",
    )
    payer_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Name as it appeared on the bank statement",
    )
    # Source identifies whether this is a tenant or guarantor payment
    SOURCE_TENANT = "tenant"
    SOURCE_GUARANTOR = "guarantor"
    SOURCE_OTHER = "other"
    SOURCE_CHOICES = [
        (SOURCE_TENANT, "Tenant"),
        (SOURCE_GUARANTOR, "Guarantor"),
        (SOURCE_OTHER, "Other"),
    ]
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default=SOURCE_TENANT,
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.CLEARED,
    )
    reversed_at = models.DateTimeField(null=True, blank=True)
    reversal_reason = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recorded_payments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-payment_date", "-created_at"]

    def __str__(self) -> str:
        return (
            f"Payment #{self.pk} ZAR {self.amount} → Invoice {self.invoice_id} "
            f"[{self.status}]"
        )


class UnmatchedPayment(models.Model):
    """
    Funds received that could not be automatically matched to a lease invoice
    (wrong reference, unknown payer, etc.).

    An operator manually assigns these to a lease + invoice; the record is then
    converted to a RentPayment and this row is marked resolved.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Needs Reconciliation"
        RESOLVED = "resolved", "Resolved"
        REJECTED = "rejected", "Rejected / Returned"

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    reference = models.CharField(max_length=150, blank=True)
    payer_name = models.CharField(max_length=200, blank=True)
    bank_statement_line = models.TextField(
        blank=True,
        help_text="Raw bank statement line for operator context",
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
    )
    # Set when operator assigns this to a lease/invoice
    assigned_to_invoice = models.ForeignKey(
        RentInvoice,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="unmatched_sources",
    )
    # The RentPayment created when this is resolved
    resolved_payment = models.OneToOneField(
        RentPayment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="unmatched_source",
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resolved_unmatched_payments",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-payment_date"]
        indexes = [
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return (
            f"Unmatched ZAR {self.amount} on {self.payment_date} "
            f"ref='{self.reference}' [{self.status}]"
        )


class PaymentAuditLog(models.Model):
    """
    Immutable audit trail for every status change on invoices and payments.

    Append-only — nothing should ever UPDATE or DELETE rows here.
    Ties to RNT-SEC-008 (audit trail requirement).
    """

    class EntityType(models.TextChoices):
        INVOICE = "invoice", "Invoice"
        PAYMENT = "payment", "Payment"
        UNMATCHED = "unmatched", "Unmatched Payment"

    entity_type = models.CharField(max_length=15, choices=EntityType.choices)
    entity_id = models.PositiveIntegerField(help_text="PK of the related entity")
    # Denormalised for fast display without joins
    lease_id = models.PositiveIntegerField(null=True, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payment_audit_logs",
    )
    event = models.CharField(
        max_length=50,
        help_text="Short machine-readable event code, e.g. 'status_changed', 'payment_reversed'",
    )
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20, blank=True)
    detail = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extra context: amounts, reasons, payer info, etc.",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["lease_id", "-created_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"AuditLog [{self.entity_type}#{self.entity_id}] "
            f"{self.from_status} → {self.to_status} @ {self.created_at:%Y-%m-%d %H:%M}"
        )
