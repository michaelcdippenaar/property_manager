"""
Rent reconciliation edge-case tests — RNT-QUAL-004.

Each acceptance criterion from the task gets its own test class.

Run with:
    pytest backend/apps/payments/tests/test_reconciliation_edges.py -v

All tests use Django's TestCase (with DB) because reconciliation logic
performs multi-row DB writes inside transactions.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase

pytestmark = pytest.mark.django_db


# ── Fixtures / helpers ────────────────────────────────────────────────────── #


def _make_lease_stub(pk: int = 1) -> MagicMock:
    """Minimal lease-like object (no real DB row required for unit tests)."""
    lease = MagicMock()
    lease.pk = pk
    lease.id = pk
    lease.lease_number = f"L-TEST-{pk:04d}"
    lease.primary_tenant = None
    return lease


class ReconciliationTestCase(TestCase):
    """
    Base class that creates real DB rows using the models directly
    (no factories dependency — keeps this test fully self-contained).
    """

    def _make_invoice(
        self,
        amount_due: str = "10000.00",
        credit_balance: str = "0.00",
    ):
        """Create a minimal RentInvoice using test_hub's lease fixture if available,
        otherwise create a bare invoice pointing to a stub lease PK.

        Since Lease is in a separate app we create a real Lease + Unit + Property
        via the test_hub helpers when available, falling back to direct model creation.
        """
        from apps.payments.models import RentInvoice

        # Create the minimum supporting objects inline (no factory dependency)
        from apps.properties.models import Property, Unit
        from apps.leases.models import Lease

        prop = Property.objects.create(
            name="Test Property",
            address="1 Test St",
            city="Cape Town",
            province="WC",
            postal_code="8001",
            property_type="apartment",
        )
        unit = Unit.objects.create(
            property=prop,
            unit_number="101",
            bedrooms=2,
            bathrooms=1,
            rent_amount=Decimal(amount_due),
        )
        lease = Lease.objects.create(
            unit=unit,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            monthly_rent=Decimal(amount_due),
            status=Lease.Status.ACTIVE,
        )

        return RentInvoice.objects.create(
            lease=lease,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
            amount_due=Decimal(amount_due),
            credit_balance=Decimal(credit_balance),
            status=RentInvoice.Status.UNPAID,
            due_date=date(2026, 4, 1),
        )


# ── AC1: Partial payment ──────────────────────────────────────────────────── #


class TestPartialPayment(ReconciliationTestCase):
    """AC1 — Partial payment marks invoice partially_paid, balance visible."""

    def test_partial_payment_status(self):
        from apps.payments.models import RentInvoice
        from apps.payments.reconciliation import apply_payment

        invoice = self._make_invoice("10000.00")
        apply_payment(
            invoice,
            Decimal("4000.00"),
            payment_date=date(2026, 4, 3),
            reference="PARTIAL-REF",
        )

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, RentInvoice.Status.PARTIALLY_PAID)

    def test_partial_payment_balance_remaining(self):
        from apps.payments.reconciliation import apply_payment

        invoice = self._make_invoice("10000.00")
        apply_payment(
            invoice,
            Decimal("4000.00"),
            payment_date=date(2026, 4, 3),
        )

        invoice.refresh_from_db()
        self.assertEqual(invoice.balance_remaining, Decimal("6000.00"))

    def test_partial_payment_audit_log_created(self):
        from apps.payments.models import PaymentAuditLog
        from apps.payments.reconciliation import apply_payment

        invoice = self._make_invoice("10000.00")
        apply_payment(invoice, Decimal("4000.00"), payment_date=date(2026, 4, 3))

        logs = PaymentAuditLog.objects.filter(
            entity_type=PaymentAuditLog.EntityType.INVOICE,
            entity_id=invoice.pk,
            event="status_changed",
        )
        self.assertTrue(logs.exists())


# ── AC2: Overpayment ─────────────────────────────────────────────────────── #


class TestOverpayment(ReconciliationTestCase):
    """AC2 — Overpayment marks invoice overpaid; tenant_in_credit is True."""

    def test_overpayment_status(self):
        from apps.payments.models import RentInvoice
        from apps.payments.reconciliation import apply_payment

        invoice = self._make_invoice("10000.00")
        apply_payment(
            invoice,
            Decimal("12000.00"),
            payment_date=date(2026, 4, 1),
        )

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, RentInvoice.Status.OVERPAID)

    def test_overpayment_tenant_in_credit_flag(self):
        from apps.payments.reconciliation import apply_payment

        invoice = self._make_invoice("10000.00")
        apply_payment(invoice, Decimal("12000.00"), payment_date=date(2026, 4, 1))

        invoice.refresh_from_db()
        self.assertTrue(invoice.tenant_in_credit)

    def test_overpayment_balance_remaining_is_negative(self):
        from apps.payments.reconciliation import apply_payment

        invoice = self._make_invoice("10000.00")
        apply_payment(invoice, Decimal("12000.00"), payment_date=date(2026, 4, 1))

        invoice.refresh_from_db()
        self.assertEqual(invoice.balance_remaining, Decimal("-2000.00"))

    def test_credit_carries_forward_to_next_invoice(self):
        from apps.payments.models import RentInvoice
        from apps.payments.reconciliation import apply_payment, carry_credit_forward
        from apps.leases.models import Lease

        invoice = self._make_invoice("10000.00")
        apply_payment(invoice, Decimal("12000.00"), payment_date=date(2026, 4, 1))
        invoice.refresh_from_db()

        # Create next cycle invoice on same lease
        next_invoice = RentInvoice.objects.create(
            lease=invoice.lease,
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            amount_due=Decimal("10000.00"),
            due_date=date(2026, 5, 1),
        )

        credit = carry_credit_forward(invoice, next_invoice)

        self.assertEqual(credit, Decimal("2000.00"))
        next_invoice.refresh_from_db()
        self.assertEqual(next_invoice.credit_balance, Decimal("2000.00"))
        # Next invoice should be partially paid (R2000 credit against R10000 due)
        self.assertEqual(next_invoice.status, RentInvoice.Status.PARTIALLY_PAID)


# ── AC3: Reversal / bounced EFT ──────────────────────────────────────────── #


class TestPaymentReversal(ReconciliationTestCase):
    """AC3 — Reversal reverts invoice to unpaid; tenant + agent notified."""

    def test_reversal_marks_payment_reversed(self):
        from apps.payments.models import RentPayment
        from apps.payments.reconciliation import apply_payment, reverse_payment

        invoice = self._make_invoice("10000.00")
        payment = apply_payment(
            invoice,
            Decimal("10000.00"),
            payment_date=date(2026, 4, 1),
        )

        reverse_payment(payment, reason="Insufficient funds")

        payment.refresh_from_db()
        self.assertEqual(payment.status, RentPayment.Status.REVERSED)
        self.assertIsNotNone(payment.reversed_at)
        self.assertEqual(payment.reversal_reason, "Insufficient funds")

    def test_reversal_reverts_invoice_to_unpaid(self):
        from apps.payments.models import RentInvoice
        from apps.payments.reconciliation import apply_payment, reverse_payment

        invoice = self._make_invoice("10000.00")
        payment = apply_payment(invoice, Decimal("10000.00"), payment_date=date(2026, 4, 1))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, RentInvoice.Status.PAID)

        reverse_payment(payment, reason="Bounced")

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, RentInvoice.Status.UNPAID)

    def test_reversal_audit_log(self):
        from apps.payments.models import PaymentAuditLog
        from apps.payments.reconciliation import apply_payment, reverse_payment

        invoice = self._make_invoice("10000.00")
        payment = apply_payment(invoice, Decimal("10000.00"), payment_date=date(2026, 4, 1))
        reverse_payment(payment, reason="Test bounce")

        log = PaymentAuditLog.objects.filter(
            entity_type=PaymentAuditLog.EntityType.PAYMENT,
            entity_id=payment.pk,
            event="payment_reversed",
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.to_status, "reversed")

    def test_double_reversal_raises(self):
        from apps.payments.reconciliation import apply_payment, reverse_payment

        invoice = self._make_invoice("10000.00")
        payment = apply_payment(invoice, Decimal("10000.00"), payment_date=date(2026, 4, 1))
        reverse_payment(payment, reason="First bounce")

        with self.assertRaises(ValueError):
            reverse_payment(payment, reason="Second bounce")

    @patch("apps.payments.reconciliation._notify_reversal")
    def test_reversal_triggers_notification(self, mock_notify):
        from apps.payments.reconciliation import apply_payment, reverse_payment

        invoice = self._make_invoice("10000.00")
        payment = apply_payment(invoice, Decimal("10000.00"), payment_date=date(2026, 4, 1))
        reverse_payment(payment, reason="Bounce test")

        mock_notify.assert_called_once()


# ── AC4: Unmatched payment ────────────────────────────────────────────────── #


class TestUnmatchedPayment(ReconciliationTestCase):
    """AC4 — Wrong reference quarantined; operator can manually assign."""

    def test_unmatched_created_with_pending_status(self):
        from apps.payments.models import UnmatchedPayment

        um = UnmatchedPayment.objects.create(
            amount=Decimal("8000.00"),
            payment_date=date(2026, 4, 5),
            reference="WRONG-REF-999",
            payer_name="Unknown Payer",
        )
        self.assertEqual(um.status, UnmatchedPayment.Status.PENDING)

    def test_assign_unmatched_resolves_it(self):
        from apps.payments.models import UnmatchedPayment
        from apps.payments.reconciliation import assign_unmatched

        invoice = self._make_invoice("10000.00")
        um = UnmatchedPayment.objects.create(
            amount=Decimal("10000.00"),
            payment_date=date(2026, 4, 5),
            reference="UNKNOWN-001",
        )

        assign_unmatched(um, invoice)

        um.refresh_from_db()
        self.assertEqual(um.status, UnmatchedPayment.Status.RESOLVED)
        self.assertEqual(um.assigned_to_invoice, invoice)
        self.assertIsNotNone(um.resolved_payment)

    def test_assign_unmatched_reconciles_invoice(self):
        from apps.payments.models import RentInvoice, UnmatchedPayment
        from apps.payments.reconciliation import assign_unmatched

        invoice = self._make_invoice("10000.00")
        um = UnmatchedPayment.objects.create(
            amount=Decimal("10000.00"),
            payment_date=date(2026, 4, 5),
            reference="UNKNOWN-002",
        )

        assign_unmatched(um, invoice)

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, RentInvoice.Status.PAID)

    def test_assign_already_resolved_raises(self):
        from apps.payments.models import UnmatchedPayment
        from apps.payments.reconciliation import assign_unmatched

        invoice = self._make_invoice("10000.00")
        um = UnmatchedPayment.objects.create(
            amount=Decimal("5000.00"),
            payment_date=date(2026, 4, 5),
            status=UnmatchedPayment.Status.RESOLVED,
        )

        with self.assertRaises(ValueError):
            assign_unmatched(um, invoice)

    def test_assign_unmatched_audit_log(self):
        from apps.payments.models import PaymentAuditLog, UnmatchedPayment
        from apps.payments.reconciliation import assign_unmatched

        invoice = self._make_invoice("10000.00")
        um = UnmatchedPayment.objects.create(
            amount=Decimal("10000.00"),
            payment_date=date(2026, 4, 5),
        )
        assign_unmatched(um, invoice)

        log = PaymentAuditLog.objects.filter(
            entity_type=PaymentAuditLog.EntityType.UNMATCHED,
            entity_id=um.pk,
            event="unmatched_resolved",
        ).first()
        self.assertIsNotNone(log)


# ── AC5: Split payment (tenant + guarantor) ───────────────────────────────── #


class TestSplitPayment(ReconciliationTestCase):
    """AC5 — Two payments from different sources aggregate under the same invoice."""

    def test_split_payment_aggregates(self):
        from apps.payments.models import RentInvoice, RentPayment
        from apps.payments.reconciliation import apply_payment

        invoice = self._make_invoice("10000.00")

        # Tenant pays R6 000, guarantor covers the rest
        apply_payment(
            invoice,
            Decimal("6000.00"),
            payment_date=date(2026, 4, 1),
            source=RentPayment.SOURCE_TENANT,
            payer_name="Jane Doe",
        )
        apply_payment(
            invoice,
            Decimal("4000.00"),
            payment_date=date(2026, 4, 3),
            source=RentPayment.SOURCE_GUARANTOR,
            payer_name="John Doe (guarantor)",
        )

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, RentInvoice.Status.PAID)
        self.assertEqual(invoice.amount_paid, Decimal("10000.00"))

    def test_split_payment_two_payment_rows_exist(self):
        from apps.payments.models import RentPayment
        from apps.payments.reconciliation import apply_payment

        invoice = self._make_invoice("10000.00")
        apply_payment(invoice, Decimal("6000.00"), payment_date=date(2026, 4, 1))
        apply_payment(invoice, Decimal("4000.00"), payment_date=date(2026, 4, 3))

        self.assertEqual(invoice.payments.filter(status=RentPayment.Status.CLEARED).count(), 2)

    def test_split_partial_remains_partially_paid(self):
        from apps.payments.models import RentInvoice
        from apps.payments.reconciliation import apply_payment

        invoice = self._make_invoice("10000.00")
        apply_payment(invoice, Decimal("4000.00"), payment_date=date(2026, 4, 1))

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, RentInvoice.Status.PARTIALLY_PAID)


# ── AC6: Audit trail ──────────────────────────────────────────────────────── #


class TestAuditTrail(ReconciliationTestCase):
    """AC6 — Every state change is written to PaymentAuditLog."""

    def test_payment_recorded_creates_log(self):
        from apps.payments.models import PaymentAuditLog
        from apps.payments.reconciliation import apply_payment

        invoice = self._make_invoice("10000.00")
        payment = apply_payment(invoice, Decimal("5000.00"), payment_date=date(2026, 4, 1))

        log = PaymentAuditLog.objects.filter(
            entity_type=PaymentAuditLog.EntityType.PAYMENT,
            entity_id=payment.pk,
            event="payment_recorded",
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.detail["amount"], "5000.00")

    def test_full_lifecycle_audit_logs(self):
        """
        Partial → full payment → reversal → re-pay path generates
        the expected sequence of audit events.
        """
        from apps.payments.models import PaymentAuditLog
        from apps.payments.reconciliation import apply_payment, reverse_payment

        invoice = self._make_invoice("10000.00")

        p1 = apply_payment(invoice, Decimal("5000.00"), payment_date=date(2026, 4, 1))
        p2 = apply_payment(invoice, Decimal("5000.00"), payment_date=date(2026, 4, 2))
        reverse_payment(p2, reason="Test")
        apply_payment(invoice, Decimal("5000.00"), payment_date=date(2026, 4, 10))

        invoice_logs = PaymentAuditLog.objects.filter(
            entity_type=PaymentAuditLog.EntityType.INVOICE,
            entity_id=invoice.pk,
        )
        # Should have multiple status_changed events
        self.assertGreaterEqual(invoice_logs.count(), 2)

    def test_audit_log_lease_id_denormalised(self):
        """lease_id is stored directly on the log row for fast lookup."""
        from apps.payments.models import PaymentAuditLog
        from apps.payments.reconciliation import apply_payment

        invoice = self._make_invoice("10000.00")
        apply_payment(invoice, Decimal("5000.00"), payment_date=date(2026, 4, 1))

        log = PaymentAuditLog.objects.filter(lease_id=invoice.lease_id).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.lease_id, invoice.lease_id)
