"""
Rent reconciliation engine — RNT-QUAL-004 / RNT-005.

All mutations go through these functions so that:
  - Invoice status is always consistent with payment totals.
  - Every state change is written to PaymentAuditLog.
  - Notifications are dispatched on reversals.

Public API
----------
apply_payment(invoice, amount, *, payment_date, reference, payer_name, source, actor)
    Record a new cleared payment and reconcile the invoice.

reverse_payment(payment, *, reason, actor)
    Mark a payment as reversed (bounced EFT) and recompute invoice status.

assign_unmatched(unmatched, invoice, *, actor, payment_date, source, payer_name)
    Resolve an UnmatchedPayment by creating a RentPayment and reconciling.

carry_credit_forward(old_invoice, new_invoice, *, actor)
    When an overpaid invoice rolls into the next cycle, transfer the credit.

ingest_bank_payment(amount, payment_date, reference, *, payer_name, actor)
    Auto-match an incoming bank payment to a lease by payment_reference.
    Returns (RentPayment, None) on match, or (None, UnmatchedPayment) on miss.

flag_arrears(as_of_date, *, grace_days)
    Return queryset of RentInvoice rows that are past-due by at least grace_days.

generate_receipt(invoice)
    Return a dict representing a payment receipt for a fully-paid invoice.
    Raises ValueError if the invoice is not fully paid.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Union

from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from .models import PaymentAuditLog, RentInvoice, RentPayment, UnmatchedPayment

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    User = get_user_model()


# ── Internal helpers ──────────────────────────────────────────────────────── #


def _log(
    entity_type: str,
    entity_id: int,
    event: str,
    *,
    lease_id: int | None = None,
    actor=None,
    from_status: str = "",
    to_status: str = "",
    detail: dict | None = None,
) -> PaymentAuditLog:
    return PaymentAuditLog.objects.create(
        entity_type=entity_type,
        entity_id=entity_id,
        lease_id=lease_id,
        actor=actor,
        event=event,
        from_status=from_status,
        to_status=to_status,
        detail=detail or {},
    )


def _recompute_invoice_status(invoice: RentInvoice, actor=None) -> RentInvoice:
    """
    Recalculate invoice status from live payment totals and update DB.

    State machine:
      paid_total = sum of CLEARED payments
      effective_paid = paid_total + credit_balance_carried_in

      effective_paid == 0               → unpaid
      0 < effective_paid < amount_due   → partially_paid
      effective_paid == amount_due      → paid
      effective_paid > amount_due       → overpaid  (excess stays as credit)
    """
    paid_total = invoice.amount_paid  # property: sums CLEARED payments only
    effective = paid_total + invoice.credit_balance
    amount_due = invoice.amount_due

    old_status = invoice.status

    if effective <= Decimal("0.00"):
        new_status = RentInvoice.Status.UNPAID
    elif effective < amount_due:
        new_status = RentInvoice.Status.PARTIALLY_PAID
    elif effective == amount_due:
        new_status = RentInvoice.Status.PAID
    else:
        new_status = RentInvoice.Status.OVERPAID

    if new_status != old_status:
        invoice.status = new_status
        invoice.save(update_fields=["status", "updated_at"])
        _log(
            PaymentAuditLog.EntityType.INVOICE,
            invoice.pk,
            "status_changed",
            lease_id=invoice.lease_id,
            actor=actor,
            from_status=old_status,
            to_status=new_status,
            detail={"amount_due": str(amount_due), "effective_paid": str(effective)},
        )

    return invoice


# ── Public API ────────────────────────────────────────────────────────────── #


@transaction.atomic
def apply_payment(
    invoice: RentInvoice,
    amount: Decimal,
    *,
    payment_date,
    reference: str = "",
    payer_name: str = "",
    source: str = RentPayment.SOURCE_TENANT,
    actor=None,
) -> RentPayment:
    """
    Record a new cleared payment against *invoice* and reconcile.

    Handles:
    - Partial payment (amount < balance remaining)
    - Full payment
    - Overpayment (amount > balance remaining) — excess stays on invoice for
      carry-forward to next cycle.
    - Split payment — just call this multiple times; each call creates one
      RentPayment row, and status is recomputed after each.
    """
    if amount <= Decimal("0.00"):
        raise ValueError("Payment amount must be positive.")

    payment = RentPayment.objects.create(
        invoice=invoice,
        amount=amount,
        payment_date=payment_date,
        reference=reference,
        payer_name=payer_name,
        source=source,
        status=RentPayment.Status.CLEARED,
        created_by=actor,
    )

    _log(
        PaymentAuditLog.EntityType.PAYMENT,
        payment.pk,
        "payment_recorded",
        lease_id=invoice.lease_id,
        actor=actor,
        from_status="",
        to_status=RentPayment.Status.CLEARED,
        detail={
            "amount": str(amount),
            "source": source,
            "reference": reference,
            "payer_name": payer_name,
        },
    )

    # Refresh invoice from DB to get latest totals before recomputing
    invoice.refresh_from_db()
    _recompute_invoice_status(invoice, actor=actor)

    return payment


@transaction.atomic
def reverse_payment(
    payment: RentPayment,
    *,
    reason: str,
    actor=None,
) -> RentPayment:
    """
    Mark *payment* as reversed (bounced EFT / recall) and recompute invoice.

    After reversal the invoice status reverts toward unpaid/partially_paid.
    Notifications are dispatched to tenant + agent.
    """
    if payment.status == RentPayment.Status.REVERSED:
        raise ValueError(f"Payment #{payment.pk} is already reversed.")

    old_status = payment.status
    payment.status = RentPayment.Status.REVERSED
    payment.reversed_at = timezone.now()
    payment.reversal_reason = reason
    payment.save(update_fields=["status", "reversed_at", "reversal_reason"])

    _log(
        PaymentAuditLog.EntityType.PAYMENT,
        payment.pk,
        "payment_reversed",
        lease_id=payment.invoice.lease_id,
        actor=actor,
        from_status=old_status,
        to_status=RentPayment.Status.REVERSED,
        detail={"reason": reason, "amount": str(payment.amount)},
    )

    invoice = payment.invoice
    invoice.refresh_from_db()
    _recompute_invoice_status(invoice, actor=actor)

    # Dispatch notifications (best-effort — failure must not roll back the reversal)
    try:
        _notify_reversal(payment, reason)
    except Exception:
        pass

    return payment


@transaction.atomic
def assign_unmatched(
    unmatched: UnmatchedPayment,
    invoice: RentInvoice,
    *,
    actor=None,
    payment_date=None,
    source: str = RentPayment.SOURCE_TENANT,
    payer_name: str = "",
) -> RentPayment:
    """
    Resolve an UnmatchedPayment by assigning it to *invoice*.

    Creates a RentPayment, reconciles the invoice, and marks the
    UnmatchedPayment as resolved.
    """
    if unmatched.status != UnmatchedPayment.Status.PENDING:
        raise ValueError(
            f"UnmatchedPayment #{unmatched.pk} is already {unmatched.status}."
        )

    effective_date = payment_date or unmatched.payment_date
    effective_payer = payer_name or unmatched.payer_name

    payment = apply_payment(
        invoice,
        unmatched.amount,
        payment_date=effective_date,
        reference=unmatched.reference,
        payer_name=effective_payer,
        source=source,
        actor=actor,
    )

    unmatched.status = UnmatchedPayment.Status.RESOLVED
    unmatched.assigned_to_invoice = invoice
    unmatched.resolved_payment = payment
    unmatched.resolved_by = actor
    unmatched.resolved_at = timezone.now()
    unmatched.save(
        update_fields=[
            "status",
            "assigned_to_invoice",
            "resolved_payment",
            "resolved_by",
            "resolved_at",
        ]
    )

    _log(
        PaymentAuditLog.EntityType.UNMATCHED,
        unmatched.pk,
        "unmatched_resolved",
        lease_id=invoice.lease_id,
        actor=actor,
        from_status=UnmatchedPayment.Status.PENDING,
        to_status=UnmatchedPayment.Status.RESOLVED,
        detail={
            "invoice_id": invoice.pk,
            "payment_id": payment.pk,
            "amount": str(unmatched.amount),
        },
    )

    return payment


@transaction.atomic
def carry_credit_forward(
    old_invoice: RentInvoice,
    new_invoice: RentInvoice,
    *,
    actor=None,
) -> Decimal:
    """
    Transfer any credit balance from *old_invoice* to *new_invoice*.

    Call this when generating the next cycle's invoice.
    Returns the credit amount transferred (ZAR).

    Only transfers when old_invoice is overpaid (balance_remaining < 0).
    """
    credit = -old_invoice.balance_remaining  # positive when overpaid
    if credit <= Decimal("0.00"):
        return Decimal("0.00")

    old_invoice.credit_balance = Decimal("0.00")
    old_invoice.save(update_fields=["credit_balance", "updated_at"])

    new_invoice.credit_balance = new_invoice.credit_balance + credit
    new_invoice.save(update_fields=["credit_balance", "updated_at"])

    # Recompute both
    old_invoice.refresh_from_db()
    _recompute_invoice_status(old_invoice, actor=actor)
    new_invoice.refresh_from_db()
    _recompute_invoice_status(new_invoice, actor=actor)

    _log(
        PaymentAuditLog.EntityType.INVOICE,
        old_invoice.pk,
        "credit_carried_forward",
        lease_id=old_invoice.lease_id,
        actor=actor,
        detail={
            "credit_amount": str(credit),
            "to_invoice_id": new_invoice.pk,
        },
    )
    _log(
        PaymentAuditLog.EntityType.INVOICE,
        new_invoice.pk,
        "credit_received",
        lease_id=new_invoice.lease_id,
        actor=actor,
        detail={
            "credit_amount": str(credit),
            "from_invoice_id": old_invoice.pk,
        },
    )

    return credit


# ── RNT-005: Reference-based auto-match ──────────────────────────────────── #


@transaction.atomic
def ingest_bank_payment(
    amount: Decimal,
    payment_date: datetime.date,
    reference: str,
    *,
    payer_name: str = "",
    source: str = RentPayment.SOURCE_TENANT,
    actor=None,
) -> tuple[RentPayment | None, UnmatchedPayment | None]:
    """
    Auto-match an incoming bank deposit to a lease by ``payment_reference``.

    Match algorithm
    ---------------
    1. Look for an ACTIVE lease whose ``payment_reference`` matches ``reference``
       (case-insensitive, stripped).  The most recent open invoice (status in
       unpaid/partially_paid) on that lease is targeted.
    2. If exactly one match is found, apply the payment normally.
    3. If zero or >1 matches, quarantine as UnmatchedPayment for operator review.

    Returns
    -------
    (RentPayment, None)      — successful auto-match
    (None, UnmatchedPayment) — no/ambiguous match; operator action required
    """
    from apps.leases.models import Lease

    clean_ref = reference.strip()

    if not clean_ref:
        # Empty reference — always unmatched
        um = UnmatchedPayment.objects.create(
            amount=amount,
            payment_date=payment_date,
            reference=reference,
            payer_name=payer_name,
        )
        _log(
            PaymentAuditLog.EntityType.UNMATCHED,
            um.pk,
            "ingest_unmatched",
            actor=actor,
            detail={"reason": "empty_reference", "amount": str(amount)},
        )
        return None, um

    matching_leases = Lease.objects.filter(
        payment_reference__iexact=clean_ref,
        status=Lease.Status.ACTIVE,
    )

    lease_count = matching_leases.count()
    if lease_count != 1:
        um = UnmatchedPayment.objects.create(
            amount=amount,
            payment_date=payment_date,
            reference=reference,
            payer_name=payer_name,
        )
        reason = "no_match" if lease_count == 0 else "ambiguous_match"
        _log(
            PaymentAuditLog.EntityType.UNMATCHED,
            um.pk,
            "ingest_unmatched",
            actor=actor,
            detail={"reason": reason, "reference": clean_ref, "amount": str(amount)},
        )
        return None, um

    lease = matching_leases.get()

    # Find the oldest open invoice (unpaid or partially_paid) on this lease
    open_invoice = (
        RentInvoice.objects.filter(
            lease=lease,
            status__in=[RentInvoice.Status.UNPAID, RentInvoice.Status.PARTIALLY_PAID],
        )
        .order_by("period_start")
        .first()
    )

    if open_invoice is None:
        # No open invoice — quarantine (could be advance payment or duplicate)
        um = UnmatchedPayment.objects.create(
            amount=amount,
            payment_date=payment_date,
            reference=reference,
            payer_name=payer_name,
        )
        _log(
            PaymentAuditLog.EntityType.UNMATCHED,
            um.pk,
            "ingest_unmatched",
            actor=actor,
            detail={
                "reason": "no_open_invoice",
                "lease_id": lease.pk,
                "reference": clean_ref,
                "amount": str(amount),
            },
        )
        return None, um

    payment = apply_payment(
        open_invoice,
        amount,
        payment_date=payment_date,
        reference=reference,
        payer_name=payer_name,
        source=source,
        actor=actor,
    )
    return payment, None


# ── RNT-005: Arrears flagging ─────────────────────────────────────────────── #

#: Default grace period in days before a late invoice is considered arrears.
#: Override via settings.RENT_ARREARS_GRACE_DAYS.
_DEFAULT_ARREARS_GRACE_DAYS: int = 3


def flag_arrears(
    as_of_date: datetime.date | None = None,
    *,
    grace_days: int | None = None,
) -> QuerySet:
    """
    Return a QuerySet of RentInvoice rows that are in arrears.

    An invoice is in arrears when::

        due_date + grace_days < as_of_date  AND  status in (unpaid, partially_paid)

    Parameters
    ----------
    as_of_date:
        Reference date.  Defaults to today (UTC).
    grace_days:
        Days after due_date before the invoice counts as arrears.
        Falls back to ``settings.RENT_ARREARS_GRACE_DAYS`` (default 3).

    Returns
    -------
    QuerySet[RentInvoice]  (not yet evaluated — callers may further filter/annotate)
    """
    if as_of_date is None:
        as_of_date = timezone.now().date()

    if grace_days is None:
        grace_days = getattr(settings, "RENT_ARREARS_GRACE_DAYS", _DEFAULT_ARREARS_GRACE_DAYS)

    arrears_threshold = as_of_date - datetime.timedelta(days=grace_days)

    return RentInvoice.objects.filter(
        status__in=[RentInvoice.Status.UNPAID, RentInvoice.Status.PARTIALLY_PAID],
        due_date__lt=arrears_threshold,
    )


# ── RNT-005: Receipt generation ───────────────────────────────────────────── #


def generate_receipt(invoice: RentInvoice) -> dict:
    """
    Return a dict representing a payment receipt for a fully-paid invoice.

    Raises
    ------
    ValueError
        If the invoice is not in ``paid`` or ``overpaid`` status (i.e. not
        fully settled).

    Receipt dict keys
    -----------------
    invoice_id, lease_id, lease_number,
    period_start, period_end,
    amount_due, amount_paid, credit_balance, balance_remaining,
    status, due_date,
    payments: list of payment summaries,
    generated_at
    """
    invoice.refresh_from_db()
    if invoice.status not in (RentInvoice.Status.PAID, RentInvoice.Status.OVERPAID):
        raise ValueError(
            f"Cannot generate receipt for invoice #{invoice.pk}: "
            f"status is '{invoice.status}' (must be 'paid' or 'overpaid')."
        )

    cleared_payments = invoice.payments.filter(status=RentPayment.Status.CLEARED).order_by("payment_date")

    payment_lines = [
        {
            "payment_id": p.pk,
            "amount": str(p.amount),
            "payment_date": p.payment_date.isoformat(),
            "reference": p.reference,
            "payer_name": p.payer_name,
            "source": p.source,
        }
        for p in cleared_payments
    ]

    lease = invoice.lease
    receipt = {
        "invoice_id": invoice.pk,
        "lease_id": invoice.lease_id,
        "lease_number": getattr(lease, "lease_number", None) or str(invoice.lease_id),
        "period_start": invoice.period_start.isoformat(),
        "period_end": invoice.period_end.isoformat(),
        "amount_due": str(invoice.amount_due),
        "amount_paid": str(invoice.amount_paid),
        "credit_balance": str(invoice.credit_balance),
        "balance_remaining": str(invoice.balance_remaining),
        "status": invoice.status,
        "due_date": invoice.due_date.isoformat(),
        "payments": payment_lines,
        "generated_at": timezone.now().isoformat(),
    }

    _log(
        PaymentAuditLog.EntityType.INVOICE,
        invoice.pk,
        "receipt_generated",
        lease_id=invoice.lease_id,
        detail={"amount_paid": str(invoice.amount_paid)},
    )

    return receipt


# ── Notification helpers ──────────────────────────────────────────────────── #


def _notify_reversal(payment: RentPayment, reason: str) -> None:
    """
    Send email/SMS notifications to tenant and agent on payment reversal.

    Uses the existing notifications service if available; degrades silently
    if the notifications app is not configured.
    """
    try:
        from apps.notifications.services.email import send_email
    except ImportError:
        return

    invoice = payment.invoice
    lease = invoice.lease

    # Notify tenant
    tenant = getattr(lease, "primary_tenant", None)
    if tenant:
        tenant_email = getattr(tenant, "email", None)
        if tenant_email:
            send_email(
                to=tenant_email,
                subject="Payment reversal notice — action required",
                body=(
                    f"Dear {tenant.full_name},\n\n"
                    f"Your EFT payment of ZAR {payment.amount} "
                    f"for the period {invoice.period_start} – {invoice.period_end} "
                    f"has been reversed.\n\n"
                    f"Reason: {reason}\n\n"
                    f"Outstanding balance: ZAR {invoice.balance_remaining}\n\n"
                    "Please arrange payment as soon as possible to avoid further action."
                ),
            )

    # Notify agent (lease created_by is not reliably the agent, so we try the
    # lease unit's property manager)
    try:
        agent = lease.unit.property.agent
        agent_email = getattr(agent, "email", None)
        if agent_email:
            send_email(
                to=agent_email,
                subject=f"Bounced EFT — Lease {lease.lease_number or lease.pk}",
                body=(
                    f"A payment of ZAR {payment.amount} on Lease "
                    f"{lease.lease_number or lease.pk} "
                    f"(tenant: {getattr(tenant, 'full_name', 'unknown')}) "
                    f"has been reversed.\n\n"
                    f"Reason: {reason}\n\n"
                    f"Outstanding balance: ZAR {invoice.balance_remaining}"
                ),
            )
    except AttributeError:
        pass
