"""
Rent Payment Tracking reconciliation edge-case tests — RNT-005.

One test class per acceptance criterion.

Run with:
    cd backend && pytest apps/payments/tests/test_rnt005_reconciliation_edges.py -v

All tests exercise real DB rows via Django TestCase; no external infra needed.
AC-6 (owner dashboard real-time state) is covered at the serializer/API level
using DRF's APIClient rather than requiring a running server.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import TestCase
from django.utils import timezone

pytestmark = pytest.mark.django_db


# ── Shared test fixture helper ────────────────────────────────────────────── #


class _BaseReconciliation(TestCase):
    """
    Creates the minimum real DB graph:
      Property → Unit → Lease (ACTIVE, payment_reference set) → RentInvoice
    """

    def _make_lease_and_invoice(
        self,
        amount_due: str = "10000.00",
        credit_balance: str = "0.00",
        payment_reference: str = "KLIKK-L001",
        period_start: datetime.date | None = None,
        period_end: datetime.date | None = None,
        due_date: datetime.date | None = None,
        status_override: str | None = None,
    ):
        from apps.leases.models import Lease
        from apps.payments.models import RentInvoice
        from apps.properties.models import Property, Unit

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
            unit_number="A01",
            bedrooms=2,
            bathrooms=1,
            rent_amount=Decimal(amount_due),
        )
        lease = Lease.objects.create(
            unit=unit,
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 12, 31),
            monthly_rent=Decimal(amount_due),
            status=Lease.Status.ACTIVE,
            payment_reference=payment_reference,
        )

        ps = period_start or datetime.date(2026, 4, 1)
        pe = period_end or datetime.date(2026, 4, 30)
        dd = due_date or datetime.date(2026, 4, 1)

        invoice = RentInvoice.objects.create(
            lease=lease,
            period_start=ps,
            period_end=pe,
            amount_due=Decimal(amount_due),
            credit_balance=Decimal(credit_balance),
            status=status_override or RentInvoice.Status.UNPAID,
            due_date=dd,
        )
        return lease, invoice


# ── AC-1: Payment with correct unique reference auto-matches ──────────────── #


class TestReferenceAutoMatch(_BaseReconciliation):
    """
    AC-1 — Payment with correct unique reference auto-matches to tenant + lease.
    AC-2 — Payment with wrong reference is flagged for manual reconciliation.
    """

    def test_correct_reference_returns_rent_payment(self):
        from apps.payments.reconciliation import ingest_bank_payment

        lease, invoice = self._make_lease_and_invoice(
            amount_due="10000.00",
            payment_reference="KLIKK-L001",
        )
        payment, unmatched = ingest_bank_payment(
            Decimal("10000.00"),
            datetime.date(2026, 4, 5),
            "KLIKK-L001",
        )
        self.assertIsNotNone(payment)
        self.assertIsNone(unmatched)

    def test_correct_reference_links_to_correct_lease(self):
        from apps.payments.models import RentPayment
        from apps.payments.reconciliation import ingest_bank_payment

        lease, invoice = self._make_lease_and_invoice(
            amount_due="10000.00",
            payment_reference="KLIKK-L002",
        )
        payment, _ = ingest_bank_payment(
            Decimal("10000.00"),
            datetime.date(2026, 4, 5),
            "KLIKK-L002",
        )
        self.assertEqual(payment.invoice.lease_id, lease.pk)

    def test_correct_reference_marks_invoice_paid(self):
        from apps.payments.models import RentInvoice
        from apps.payments.reconciliation import ingest_bank_payment

        lease, invoice = self._make_lease_and_invoice(
            amount_due="10000.00",
            payment_reference="KLIKK-L003",
        )
        ingest_bank_payment(
            Decimal("10000.00"),
            datetime.date(2026, 4, 5),
            "KLIKK-L003",
        )
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, RentInvoice.Status.PAID)

    def test_case_insensitive_reference_match(self):
        """Payment reference matching must be case-insensitive."""
        from apps.payments.reconciliation import ingest_bank_payment

        lease, invoice = self._make_lease_and_invoice(
            amount_due="10000.00",
            payment_reference="klikk-L004",
        )
        payment, unmatched = ingest_bank_payment(
            Decimal("10000.00"),
            datetime.date(2026, 4, 5),
            "KLIKK-L004",  # uppercase
        )
        self.assertIsNotNone(payment)
        self.assertIsNone(unmatched)

    def test_reference_whitespace_stripped(self):
        """Leading/trailing whitespace must not prevent a match."""
        from apps.payments.reconciliation import ingest_bank_payment

        lease, invoice = self._make_lease_and_invoice(
            amount_due="10000.00",
            payment_reference="KLIKK-L005",
        )
        payment, unmatched = ingest_bank_payment(
            Decimal("10000.00"),
            datetime.date(2026, 4, 5),
            "  KLIKK-L005  ",
        )
        self.assertIsNotNone(payment)
        self.assertIsNone(unmatched)


# ── AC-2: Wrong reference flagged for manual reconciliation ───────────────── #


class TestWrongReferenceUnmatched(_BaseReconciliation):
    """
    AC-2 — Payment with wrong/unknown reference creates an UnmatchedPayment.
    """

    def test_wrong_reference_returns_unmatched(self):
        from apps.payments.reconciliation import ingest_bank_payment

        self._make_lease_and_invoice(payment_reference="KLIKK-REAL")
        payment, unmatched = ingest_bank_payment(
            Decimal("10000.00"),
            datetime.date(2026, 4, 5),
            "TOTALLY-WRONG-REF",
        )
        self.assertIsNone(payment)
        self.assertIsNotNone(unmatched)

    def test_wrong_reference_unmatched_status_is_pending(self):
        from apps.payments.models import UnmatchedPayment
        from apps.payments.reconciliation import ingest_bank_payment

        self._make_lease_and_invoice(payment_reference="KLIKK-REAL2")
        _, unmatched = ingest_bank_payment(
            Decimal("10000.00"),
            datetime.date(2026, 4, 5),
            "WRONG-REF-002",
        )
        self.assertEqual(unmatched.status, UnmatchedPayment.Status.PENDING)

    def test_empty_reference_creates_unmatched(self):
        """An empty payment reference must always quarantine."""
        from apps.payments.models import UnmatchedPayment
        from apps.payments.reconciliation import ingest_bank_payment

        self._make_lease_and_invoice(payment_reference="KLIKK-REAL3")
        payment, unmatched = ingest_bank_payment(
            Decimal("5000.00"),
            datetime.date(2026, 4, 5),
            "",
        )
        self.assertIsNone(payment)
        self.assertIsNotNone(unmatched)
        self.assertEqual(unmatched.status, UnmatchedPayment.Status.PENDING)

    def test_ambiguous_reference_unmatched_when_two_leases_share_ref(self):
        """
        If two active leases share the same payment_reference (data problem),
        the payment must NOT be auto-applied — quarantine to avoid mis-posting.
        """
        from apps.payments.reconciliation import ingest_bank_payment

        # Create two leases with the same payment_reference
        self._make_lease_and_invoice(payment_reference="DUPE-REF")
        self._make_lease_and_invoice(payment_reference="DUPE-REF")

        payment, unmatched = ingest_bank_payment(
            Decimal("10000.00"),
            datetime.date(2026, 4, 5),
            "DUPE-REF",
        )
        self.assertIsNone(payment)
        self.assertIsNotNone(unmatched)

    def test_correct_ref_but_no_open_invoice_creates_unmatched(self):
        """
        If the lease is found but all invoices are already paid, quarantine.
        """
        from apps.payments.models import RentInvoice
        from apps.payments.reconciliation import ingest_bank_payment

        lease, invoice = self._make_lease_and_invoice(payment_reference="KLIKK-NOINV")
        # Mark invoice as already paid manually
        invoice.status = RentInvoice.Status.PAID
        invoice.save(update_fields=["status"])

        payment, unmatched = ingest_bank_payment(
            Decimal("10000.00"),
            datetime.date(2026, 4, 5),
            "KLIKK-NOINV",
        )
        self.assertIsNone(payment)
        self.assertIsNotNone(unmatched)

    def test_audit_log_written_for_unmatched_ingest(self):
        """An audit log row must be created when a payment goes to unmatched."""
        from apps.payments.models import PaymentAuditLog
        from apps.payments.reconciliation import ingest_bank_payment

        _, unmatched = ingest_bank_payment(
            Decimal("5000.00"),
            datetime.date(2026, 4, 5),
            "UNRECOGNISED-REF-999",
        )
        log = PaymentAuditLog.objects.filter(
            entity_type=PaymentAuditLog.EntityType.UNMATCHED,
            entity_id=unmatched.pk,
            event="ingest_unmatched",
        ).first()
        self.assertIsNotNone(log)


# ── AC-3: Partial payments don't falsely mark rent paid ───────────────────── #


class TestPartialPaymentNoFalsePositive(_BaseReconciliation):
    """
    AC-3 — Partial payments tracked correctly; invoice never marked 'paid'
           until full amount is received.
    """

    def test_partial_payment_stays_partially_paid(self):
        from apps.payments.models import RentInvoice
        from apps.payments.reconciliation import apply_payment

        _, invoice = self._make_lease_and_invoice("10000.00")
        apply_payment(invoice, Decimal("9999.99"), payment_date=datetime.date(2026, 4, 3))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, RentInvoice.Status.PARTIALLY_PAID)

    def test_exact_full_payment_marks_paid(self):
        from apps.payments.models import RentInvoice
        from apps.payments.reconciliation import apply_payment

        _, invoice = self._make_lease_and_invoice("10000.00")
        apply_payment(invoice, Decimal("10000.00"), payment_date=datetime.date(2026, 4, 3))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, RentInvoice.Status.PAID)

    def test_penny_under_stays_partial(self):
        """R0.01 short must remain partially_paid."""
        from apps.payments.models import RentInvoice
        from apps.payments.reconciliation import apply_payment

        _, invoice = self._make_lease_and_invoice("10000.00")
        apply_payment(invoice, Decimal("9999.99"), payment_date=datetime.date(2026, 4, 3))
        invoice.refresh_from_db()
        self.assertNotEqual(invoice.status, RentInvoice.Status.PAID)

    def test_multi_partial_payments_accumulate(self):
        """Three partial payments that sum to full amount must result in PAID."""
        from apps.payments.models import RentInvoice
        from apps.payments.reconciliation import apply_payment

        _, invoice = self._make_lease_and_invoice("9000.00")
        apply_payment(invoice, Decimal("3000.00"), payment_date=datetime.date(2026, 4, 1))
        apply_payment(invoice, Decimal("3000.00"), payment_date=datetime.date(2026, 4, 5))
        apply_payment(invoice, Decimal("3000.00"), payment_date=datetime.date(2026, 4, 10))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, RentInvoice.Status.PAID)
        self.assertEqual(invoice.amount_paid, Decimal("9000.00"))

    def test_reversed_payment_reverts_partial_to_unpaid(self):
        """Reversing the only payment on a partially-paid invoice → unpaid."""
        from apps.payments.models import RentInvoice
        from apps.payments.reconciliation import apply_payment, reverse_payment

        _, invoice = self._make_lease_and_invoice("10000.00")
        pmt = apply_payment(invoice, Decimal("4000.00"), payment_date=datetime.date(2026, 4, 3))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, RentInvoice.Status.PARTIALLY_PAID)

        reverse_payment(pmt, reason="Bounced")
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, RentInvoice.Status.UNPAID)


# ── AC-4: Arrears flagging with configurable grace period ─────────────────── #


class TestArrearsFlag(_BaseReconciliation):
    """
    AC-4 — Invoices correctly flagged as arrears when overdue by N days.
    """

    def test_invoice_in_arrears_after_grace(self):
        """
        Invoice due 2026-04-01, checking on 2026-04-05 with grace_days=3
        (threshold = 2026-04-02 < 2026-04-05) → must appear in arrears.
        """
        from apps.payments.reconciliation import flag_arrears

        _, invoice = self._make_lease_and_invoice(
            amount_due="10000.00",
            due_date=datetime.date(2026, 4, 1),
        )
        qs = flag_arrears(as_of_date=datetime.date(2026, 4, 5), grace_days=3)
        self.assertIn(invoice, qs)

    def test_invoice_not_in_arrears_within_grace(self):
        """
        Invoice due 2026-04-01, checking on 2026-04-02 with grace_days=3
        (threshold = 2026-03-30 < 2026-04-01 due_date → not yet overdue).
        Actually: threshold = 2026-04-02 - 3 = 2026-03-30 < 2026-04-01
        So 2026-04-01 >= 2026-03-30 → NOT in arrears.
        """
        from apps.payments.reconciliation import flag_arrears

        _, invoice = self._make_lease_and_invoice(
            amount_due="10000.00",
            due_date=datetime.date(2026, 4, 1),
        )
        qs = flag_arrears(as_of_date=datetime.date(2026, 4, 2), grace_days=3)
        self.assertNotIn(invoice, qs)

    def test_invoice_on_grace_boundary_not_in_arrears(self):
        """
        Invoice due 2026-04-01, grace_days=3.
        Checking on 2026-04-04: threshold = 2026-04-01.
        due_date (2026-04-01) is NOT < threshold (2026-04-01) → not in arrears.
        """
        from apps.payments.reconciliation import flag_arrears

        _, invoice = self._make_lease_and_invoice(
            amount_due="10000.00",
            due_date=datetime.date(2026, 4, 1),
        )
        qs = flag_arrears(as_of_date=datetime.date(2026, 4, 4), grace_days=3)
        self.assertNotIn(invoice, qs)

    def test_invoice_one_day_past_grace_in_arrears(self):
        """
        Invoice due 2026-04-01, grace_days=3.
        Checking on 2026-04-05: threshold = 2026-04-02.
        due_date (2026-04-01) < threshold (2026-04-02) → in arrears.
        """
        from apps.payments.reconciliation import flag_arrears

        _, invoice = self._make_lease_and_invoice(
            amount_due="10000.00",
            due_date=datetime.date(2026, 4, 1),
        )
        qs = flag_arrears(as_of_date=datetime.date(2026, 4, 5), grace_days=3)
        self.assertIn(invoice, qs)

    def test_paid_invoice_excluded_from_arrears(self):
        """A fully paid invoice must never appear in arrears."""
        from apps.payments.models import RentInvoice
        from apps.payments.reconciliation import apply_payment, flag_arrears

        _, invoice = self._make_lease_and_invoice(
            amount_due="10000.00",
            due_date=datetime.date(2026, 4, 1),
        )
        apply_payment(invoice, Decimal("10000.00"), payment_date=datetime.date(2026, 4, 10))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, RentInvoice.Status.PAID)

        qs = flag_arrears(as_of_date=datetime.date(2026, 4, 20), grace_days=3)
        self.assertNotIn(invoice, qs)

    def test_partially_paid_overdue_invoice_in_arrears(self):
        """A partially-paid invoice that is past the grace period is still arrears."""
        from apps.payments.reconciliation import apply_payment, flag_arrears

        _, invoice = self._make_lease_and_invoice(
            amount_due="10000.00",
            due_date=datetime.date(2026, 4, 1),
        )
        apply_payment(invoice, Decimal("3000.00"), payment_date=datetime.date(2026, 4, 3))

        qs = flag_arrears(as_of_date=datetime.date(2026, 4, 10), grace_days=3)
        self.assertIn(invoice, qs)

    def test_grace_days_zero_means_immediate_arrears(self):
        """grace_days=0: invoice is in arrears the day after due_date."""
        from apps.payments.reconciliation import flag_arrears

        _, invoice = self._make_lease_and_invoice(
            amount_due="10000.00",
            due_date=datetime.date(2026, 4, 1),
        )
        # as_of_date = 2026-04-02, threshold = 2026-04-02 - 0 = 2026-04-02
        # due_date 2026-04-01 < 2026-04-02 → in arrears
        qs = flag_arrears(as_of_date=datetime.date(2026, 4, 2), grace_days=0)
        self.assertIn(invoice, qs)

    def test_custom_grace_days_overrides_default(self):
        """Larger grace_days should push the arrears threshold further out."""
        from apps.payments.reconciliation import flag_arrears

        _, invoice = self._make_lease_and_invoice(
            amount_due="10000.00",
            due_date=datetime.date(2026, 4, 1),
        )
        # grace_days=7: threshold = 2026-04-05 - 7 = 2026-03-29
        # due_date 2026-04-01 > 2026-03-29 → NOT in arrears
        qs = flag_arrears(as_of_date=datetime.date(2026, 4, 5), grace_days=7)
        self.assertNotIn(invoice, qs)

    @patch("apps.payments.reconciliation.settings")
    def test_settings_grace_days_respected(self, mock_settings):
        """settings.RENT_ARREARS_GRACE_DAYS should be used when grace_days is None."""
        from apps.payments.reconciliation import flag_arrears

        mock_settings.RENT_ARREARS_GRACE_DAYS = 0

        _, invoice = self._make_lease_and_invoice(
            amount_due="10000.00",
            due_date=datetime.date(2026, 4, 1),
        )
        # grace_days=0 via settings; as_of=2026-04-02 → in arrears
        qs = flag_arrears(as_of_date=datetime.date(2026, 4, 2))
        self.assertIn(invoice, qs)


# ── AC-5: Receipt generates on full payment ───────────────────────────────── #


class TestReceiptGeneration(_BaseReconciliation):
    """
    AC-5 — generate_receipt() returns a valid receipt dict for fully-paid invoices.
    """

    def test_receipt_generated_after_full_payment(self):
        from apps.payments.reconciliation import apply_payment, generate_receipt

        _, invoice = self._make_lease_and_invoice("10000.00")
        apply_payment(invoice, Decimal("10000.00"), payment_date=datetime.date(2026, 4, 3))
        receipt = generate_receipt(invoice)

        self.assertIsNotNone(receipt)
        self.assertEqual(receipt["invoice_id"], invoice.pk)

    def test_receipt_contains_required_keys(self):
        from apps.payments.reconciliation import apply_payment, generate_receipt

        _, invoice = self._make_lease_and_invoice("10000.00")
        apply_payment(invoice, Decimal("10000.00"), payment_date=datetime.date(2026, 4, 3))
        receipt = generate_receipt(invoice)

        required_keys = {
            "invoice_id", "lease_id", "lease_number",
            "period_start", "period_end",
            "amount_due", "amount_paid", "credit_balance", "balance_remaining",
            "status", "due_date", "payments", "generated_at",
        }
        self.assertEqual(required_keys, required_keys & receipt.keys())

    def test_receipt_has_correct_amounts(self):
        from apps.payments.reconciliation import apply_payment, generate_receipt

        _, invoice = self._make_lease_and_invoice("8500.00")
        apply_payment(invoice, Decimal("8500.00"), payment_date=datetime.date(2026, 4, 3))
        receipt = generate_receipt(invoice)

        self.assertEqual(receipt["amount_due"], "8500.00")
        self.assertEqual(receipt["amount_paid"], "8500.00")
        self.assertEqual(receipt["status"], "paid")

    def test_receipt_lists_all_payment_lines(self):
        from apps.payments.reconciliation import apply_payment, generate_receipt

        _, invoice = self._make_lease_and_invoice("10000.00")
        apply_payment(invoice, Decimal("6000.00"), payment_date=datetime.date(2026, 4, 1))
        apply_payment(invoice, Decimal("4000.00"), payment_date=datetime.date(2026, 4, 5))
        receipt = generate_receipt(invoice)

        self.assertEqual(len(receipt["payments"]), 2)
        totals = sum(Decimal(p["amount"]) for p in receipt["payments"])
        self.assertEqual(totals, Decimal("10000.00"))

    def test_receipt_raises_for_unpaid_invoice(self):
        from apps.payments.reconciliation import generate_receipt

        _, invoice = self._make_lease_and_invoice("10000.00")
        with self.assertRaises(ValueError):
            generate_receipt(invoice)

    def test_receipt_raises_for_partial_payment(self):
        from apps.payments.reconciliation import apply_payment, generate_receipt

        _, invoice = self._make_lease_and_invoice("10000.00")
        apply_payment(invoice, Decimal("5000.00"), payment_date=datetime.date(2026, 4, 3))
        with self.assertRaises(ValueError):
            generate_receipt(invoice)

    def test_receipt_audit_log_created(self):
        from apps.payments.models import PaymentAuditLog
        from apps.payments.reconciliation import apply_payment, generate_receipt

        _, invoice = self._make_lease_and_invoice("10000.00")
        apply_payment(invoice, Decimal("10000.00"), payment_date=datetime.date(2026, 4, 3))
        generate_receipt(invoice)

        log = PaymentAuditLog.objects.filter(
            entity_type=PaymentAuditLog.EntityType.INVOICE,
            entity_id=invoice.pk,
            event="receipt_generated",
        ).first()
        self.assertIsNotNone(log)

    def test_receipt_for_overpaid_invoice(self):
        """generate_receipt must also work when invoice is OVERPAID."""
        from apps.payments.reconciliation import apply_payment, generate_receipt

        _, invoice = self._make_lease_and_invoice("10000.00")
        apply_payment(invoice, Decimal("11000.00"), payment_date=datetime.date(2026, 4, 3))
        receipt = generate_receipt(invoice)
        self.assertEqual(receipt["status"], "overpaid")


# ── AC-6: Owner dashboard reflects payment state ──────────────────────────── #


class TestOwnerDashboardPaymentState(_BaseReconciliation):
    """
    AC-6 — The serialized invoice always exposes the current status, amount_paid,
           balance_remaining and tenant_in_credit after each mutation.

    This tests the serializer layer (which is what the owner dashboard reads)
    rather than requiring a running server.
    """

    def test_serializer_reflects_unpaid_state(self):
        from apps.payments.serializers import RentInvoiceSerializer

        _, invoice = self._make_lease_and_invoice("10000.00")
        data = RentInvoiceSerializer(invoice).data
        self.assertEqual(data["status"], "unpaid")
        self.assertEqual(Decimal(data["amount_paid"]), Decimal("0.00"))
        self.assertEqual(Decimal(data["balance_remaining"]), Decimal("10000.00"))
        self.assertFalse(data["tenant_in_credit"])

    def test_serializer_reflects_partial_payment(self):
        from apps.payments.reconciliation import apply_payment
        from apps.payments.serializers import RentInvoiceSerializer

        _, invoice = self._make_lease_and_invoice("10000.00")
        apply_payment(invoice, Decimal("4000.00"), payment_date=datetime.date(2026, 4, 3))
        invoice.refresh_from_db()
        data = RentInvoiceSerializer(invoice).data

        self.assertEqual(data["status"], "partially_paid")
        self.assertEqual(Decimal(data["amount_paid"]), Decimal("4000.00"))
        self.assertEqual(Decimal(data["balance_remaining"]), Decimal("6000.00"))

    def test_serializer_reflects_full_payment(self):
        from apps.payments.reconciliation import apply_payment
        from apps.payments.serializers import RentInvoiceSerializer

        _, invoice = self._make_lease_and_invoice("10000.00")
        apply_payment(invoice, Decimal("10000.00"), payment_date=datetime.date(2026, 4, 3))
        invoice.refresh_from_db()
        data = RentInvoiceSerializer(invoice).data

        self.assertEqual(data["status"], "paid")
        self.assertEqual(Decimal(data["balance_remaining"]), Decimal("0.00"))
        self.assertFalse(data["tenant_in_credit"])

    def test_serializer_reflects_overpaid_state(self):
        from apps.payments.reconciliation import apply_payment
        from apps.payments.serializers import RentInvoiceSerializer

        _, invoice = self._make_lease_and_invoice("10000.00")
        apply_payment(invoice, Decimal("11000.00"), payment_date=datetime.date(2026, 4, 3))
        invoice.refresh_from_db()
        data = RentInvoiceSerializer(invoice).data

        self.assertEqual(data["status"], "overpaid")
        self.assertEqual(Decimal(data["balance_remaining"]), Decimal("-1000.00"))
        self.assertTrue(data["tenant_in_credit"])

    def test_serializer_reflects_reversal(self):
        """After a bounce, serialized balance_remaining must revert to full amount."""
        from apps.payments.reconciliation import apply_payment, reverse_payment
        from apps.payments.serializers import RentInvoiceSerializer

        _, invoice = self._make_lease_and_invoice("10000.00")
        pmt = apply_payment(invoice, Decimal("10000.00"), payment_date=datetime.date(2026, 4, 3))
        reverse_payment(pmt, reason="Bounce")
        invoice.refresh_from_db()
        data = RentInvoiceSerializer(invoice).data

        self.assertEqual(data["status"], "unpaid")
        self.assertEqual(Decimal(data["balance_remaining"]), Decimal("10000.00"))


# ── AC-7: No off-by-one errors around month boundaries or leap days ────────── #


class TestMonthBoundaryAndLeapDay(_BaseReconciliation):
    """
    AC-7 — Period calculations are correct at month end, month start, and
           on leap day (29 Feb).
    """

    def test_period_end_on_last_day_of_month(self):
        """Invoice for January 2026 (31 days) can be paid on Jan 31."""
        from apps.payments.models import RentInvoice
        from apps.payments.reconciliation import apply_payment

        _, invoice = self._make_lease_and_invoice(
            amount_due="12000.00",
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 1, 31),
            due_date=datetime.date(2026, 1, 1),
        )
        apply_payment(invoice, Decimal("12000.00"), payment_date=datetime.date(2026, 1, 31))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, RentInvoice.Status.PAID)

    def test_payment_on_first_day_of_next_month(self):
        """Payment made on the first day after period end is still valid."""
        from apps.payments.models import RentInvoice
        from apps.payments.reconciliation import apply_payment

        _, invoice = self._make_lease_and_invoice(
            amount_due="12000.00",
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 1, 31),
            due_date=datetime.date(2026, 1, 1),
        )
        apply_payment(invoice, Decimal("12000.00"), payment_date=datetime.date(2026, 2, 1))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, RentInvoice.Status.PAID)

    def test_february_invoice_non_leap_year(self):
        """February 2025 has 28 days (non-leap); invoice period_end = Feb 28."""
        from apps.payments.models import RentInvoice
        from apps.payments.reconciliation import apply_payment

        _, invoice = self._make_lease_and_invoice(
            amount_due="10000.00",
            period_start=datetime.date(2025, 2, 1),
            period_end=datetime.date(2025, 2, 28),
            due_date=datetime.date(2025, 2, 1),
        )
        apply_payment(invoice, Decimal("10000.00"), payment_date=datetime.date(2025, 2, 28))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, RentInvoice.Status.PAID)

    def test_february_invoice_leap_year_2024(self):
        """February 2024 has 29 days; payment on Feb 29 must work."""
        from apps.payments.models import RentInvoice
        from apps.payments.reconciliation import apply_payment

        _, invoice = self._make_lease_and_invoice(
            amount_due="10000.00",
            period_start=datetime.date(2024, 2, 1),
            period_end=datetime.date(2024, 2, 29),
            due_date=datetime.date(2024, 2, 1),
        )
        apply_payment(invoice, Decimal("10000.00"), payment_date=datetime.date(2024, 2, 29))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, RentInvoice.Status.PAID)

    def test_arrears_across_month_boundary(self):
        """
        Invoice due 2026-01-31; checking on 2026-02-05 with grace_days=3.
        Threshold = 2026-02-05 - 3 = 2026-02-02.
        due_date 2026-01-31 < 2026-02-02 → in arrears.
        """
        from apps.payments.reconciliation import flag_arrears

        _, invoice = self._make_lease_and_invoice(
            amount_due="10000.00",
            due_date=datetime.date(2026, 1, 31),
        )
        qs = flag_arrears(as_of_date=datetime.date(2026, 2, 5), grace_days=3)
        self.assertIn(invoice, qs)

    def test_arrears_not_triggered_same_day_due(self):
        """
        Invoice due today with grace_days=3; must NOT be in arrears on due date.
        """
        from apps.payments.reconciliation import flag_arrears

        today = datetime.date(2026, 4, 1)
        _, invoice = self._make_lease_and_invoice(
            amount_due="10000.00",
            due_date=today,
        )
        qs = flag_arrears(as_of_date=today, grace_days=3)
        self.assertNotIn(invoice, qs)

    def test_credit_carry_forward_across_feb_leap_year(self):
        """
        Overpayment in Feb 2024 (leap year) must carry credit correctly to Mar 2024.
        """
        from apps.payments.models import RentInvoice
        from apps.payments.reconciliation import apply_payment, carry_credit_forward

        _, feb_invoice = self._make_lease_and_invoice(
            amount_due="10000.00",
            period_start=datetime.date(2024, 2, 1),
            period_end=datetime.date(2024, 2, 29),
            due_date=datetime.date(2024, 2, 1),
        )
        apply_payment(feb_invoice, Decimal("11000.00"), payment_date=datetime.date(2024, 2, 28))
        feb_invoice.refresh_from_db()

        mar_invoice = RentInvoice.objects.create(
            lease=feb_invoice.lease,
            period_start=datetime.date(2024, 3, 1),
            period_end=datetime.date(2024, 3, 31),
            amount_due=Decimal("10000.00"),
            due_date=datetime.date(2024, 3, 1),
        )

        credit = carry_credit_forward(feb_invoice, mar_invoice)
        self.assertEqual(credit, Decimal("1000.00"))
        mar_invoice.refresh_from_db()
        self.assertEqual(mar_invoice.credit_balance, Decimal("1000.00"))
        self.assertEqual(mar_invoice.status, RentInvoice.Status.PARTIALLY_PAID)

    def test_december_into_january_arrears(self):
        """
        Invoice due 2026-12-31 (year-end boundary); checking on 2027-01-05
        with grace_days=3 → in arrears.
        """
        from apps.payments.reconciliation import flag_arrears

        _, invoice = self._make_lease_and_invoice(
            amount_due="10000.00",
            due_date=datetime.date(2026, 12, 31),
        )
        qs = flag_arrears(as_of_date=datetime.date(2027, 1, 5), grace_days=3)
        self.assertIn(invoice, qs)
