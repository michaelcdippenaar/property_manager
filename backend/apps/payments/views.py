"""
DRF views for the payments app — RNT-QUAL-004.

Endpoints:
  GET  /api/v1/payments/invoices/                       list invoices
  GET  /api/v1/payments/invoices/{id}/                  invoice detail + nested payments
  GET  /api/v1/payments/invoices/{id}/audit-log/        audit events for this invoice
  POST /api/v1/payments/invoices/{id}/payments/         record a new payment
  POST /api/v1/payments/payments/{id}/reverse/          reverse (bounce) a payment
  GET  /api/v1/payments/unmatched/                      list unmatched deposits
  POST /api/v1/payments/unmatched/{id}/assign/          assign unmatched to invoice
"""

from decimal import Decimal

from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework import mixins

from apps.accounts.permissions import IsAgentOrAdmin

from .models import PaymentAuditLog, RentInvoice, RentPayment, UnmatchedPayment
from .reconciliation import apply_payment, assign_unmatched, reverse_payment
from .serializers import (
    AssignUnmatchedInputSerializer,
    PaymentAuditLogSerializer,
    RecordPaymentInputSerializer,
    RentInvoiceSerializer,
    RentPaymentSerializer,
    ReversePaymentInputSerializer,
    UnmatchedPaymentSerializer,
)


class RentInvoiceViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    """
    Read-only viewset for RentInvoice + reconciliation custom actions.

    Invoices are created by the system when a rent period opens — not via
    the API — so create / update / destroy are intentionally excluded.

    Supports ?search= (fuzzy match on lease_number / tenant name).
    Supports ?status= to filter by invoice status.
    Supports ?lease= to filter by lease pk.
    """

    permission_classes = [IsAgentOrAdmin]
    serializer_class = RentInvoiceSerializer

    def get_queryset(self):
        # Queryset is intentionally unscoped — view is gated to IsAgentOrAdmin
        # which limits exposure to operator roles only.
        qs = RentInvoice.objects.select_related("lease").prefetch_related(
            "payments"
        )
        params = self.request.query_params

        if status_filter := params.get("status"):
            qs = qs.filter(status=status_filter)

        if lease_id := params.get("lease"):
            qs = qs.filter(lease_id=lease_id)

        if search := params.get("search"):
            qs = qs.filter(
                Q(lease__lease_number__icontains=search)
                | Q(lease__primary_tenant__first_name__icontains=search)
                | Q(lease__primary_tenant__last_name__icontains=search)
            )

        return qs.order_by("-period_start")

    @action(detail=True, methods=["get"], url_path="audit-log")
    def audit_log(self, request, pk=None):
        """Return audit log events for this invoice and its payments."""
        invoice = self.get_object()
        payment_ids = list(invoice.payments.values_list("id", flat=True))

        logs = PaymentAuditLog.objects.filter(
            Q(entity_type=PaymentAuditLog.EntityType.INVOICE, entity_id=invoice.pk)
            | Q(entity_type=PaymentAuditLog.EntityType.PAYMENT, entity_id__in=payment_ids)
        ).select_related("actor").order_by("-created_at")

        serializer = PaymentAuditLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="payments")
    def record_payment(self, request, pk=None):
        """Record a new payment against this invoice and reconcile."""
        invoice = self.get_object()
        input_ser = RecordPaymentInputSerializer(data=request.data)
        input_ser.is_valid(raise_exception=True)
        d = input_ser.validated_data

        try:
            payment = apply_payment(
                invoice,
                Decimal(str(d["amount"])),
                payment_date=d["payment_date"],
                reference=d.get("reference", ""),
                payer_name=d.get("payer_name", ""),
                source=d.get("source", RentPayment.SOURCE_TENANT),
                actor=request.user,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        invoice.refresh_from_db()
        return Response(
            {
                "payment": RentPaymentSerializer(payment).data,
                "invoice": RentInvoiceSerializer(invoice).data,
            },
            status=status.HTTP_201_CREATED,
        )


class RentPaymentViewSet(mixins.RetrieveModelMixin, GenericViewSet):
    """
    Read-only viewset for individual payments, plus the reverse action.
    """

    permission_classes = [IsAgentOrAdmin]
    serializer_class = RentPaymentSerializer
    queryset = RentPayment.objects.select_related("invoice", "created_by")

    @action(detail=True, methods=["post"], url_path="reverse")
    def reverse(self, request, pk=None):
        """Reverse (bounce) a cleared payment."""
        payment = self.get_object()
        input_ser = ReversePaymentInputSerializer(data=request.data)
        input_ser.is_valid(raise_exception=True)

        try:
            payment = reverse_payment(
                payment,
                reason=input_ser.validated_data["reason"],
                actor=request.user,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        invoice = payment.invoice
        invoice.refresh_from_db()
        return Response(
            {
                "payment": RentPaymentSerializer(payment).data,
                "invoice": RentInvoiceSerializer(invoice).data,
            }
        )


class UnmatchedPaymentViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    """
    Create + read viewset for UnmatchedPayment + manual assign action.

    Operators may manually enter an unmatched deposit (create) but update
    and destroy are excluded — once quarantined, a record is only resolved
    via the assign action, preserving the audit trail.
    """

    permission_classes = [IsAgentOrAdmin]
    serializer_class = UnmatchedPaymentSerializer

    def get_queryset(self):
        # Queryset is intentionally unscoped — view is gated to IsAgentOrAdmin
        # which limits exposure to operator roles only.
        qs = UnmatchedPayment.objects.select_related("assigned_to_invoice", "resolved_payment")
        status_filter = self.request.query_params.get("status", "pending")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.order_by("-payment_date")

    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, pk=None):
        """Assign this unmatched payment to an invoice."""
        unmatched = self.get_object()
        input_ser = AssignUnmatchedInputSerializer(data=request.data)
        input_ser.is_valid(raise_exception=True)
        d = input_ser.validated_data

        try:
            invoice = RentInvoice.objects.get(pk=d["invoice_id"])
        except RentInvoice.DoesNotExist:
            return Response({"detail": "Invoice not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            payment = assign_unmatched(
                unmatched,
                invoice,
                actor=request.user,
                source=d.get("source", RentPayment.SOURCE_TENANT),
                payer_name=d.get("payer_name", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        invoice.refresh_from_db()
        return Response(
            {
                "payment": RentPaymentSerializer(payment).data,
                "invoice": RentInvoiceSerializer(invoice).data,
                "unmatched": UnmatchedPaymentSerializer(unmatched).data,
            },
            status=status.HTTP_201_CREATED,
        )
