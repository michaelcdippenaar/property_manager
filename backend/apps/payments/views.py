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

from apps.accounts.models import User
from apps.accounts.permissions import IsAdminOrAgencyAdmin, IsAgentOrAdmin
from apps.accounts.scoping import AgencyScopedQuerysetMixin, AgencyStampedCreateMixin, _is_admin
from rest_framework.permissions import IsAuthenticated

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
    AgencyScopedQuerysetMixin,
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

    permission_classes = [IsAuthenticated]
    serializer_class = RentInvoiceSerializer
    queryset = RentInvoice.objects.select_related("lease").prefetch_related("payments")

    def get_queryset(self):
        user = self.request.user

        # Phase 2.7: tenants have no agency_id; mixin would .none() them.
        # Bypass the mixin for the tenant role and scope by their leases.
        if user.is_authenticated and user.role == User.Role.TENANT:
            from apps.tenant_portal.views import get_tenant_leases
            tenant_lease_ids = get_tenant_leases(user).values_list("pk", flat=True)
            qs = RentInvoice.objects.select_related("lease").prefetch_related("payments").filter(
                lease_id__in=tenant_lease_ids
            )
        else:
            # Mixin: filters by user.agency_id for non-admins; full table for ADMIN.
            qs = super().get_queryset()
            if user.role == User.Role.OWNER:
                from apps.properties.access import get_accessible_property_ids
                prop_ids = get_accessible_property_ids(user)
                qs = qs.filter(lease__unit__property_id__in=prop_ids)
            elif not (user.role == User.Role.ADMIN or user.is_superuser):
                # All agent/staff roles: layer the property-access filter on top.
                from apps.properties.access import get_accessible_property_ids
                prop_ids = get_accessible_property_ids(user)
                qs = qs.filter(lease__unit__property_id__in=prop_ids)

        params = self.request.query_params

        if status_filter := params.get("status"):
            qs = qs.filter(status=status_filter)

        if lease_id := params.get("lease"):
            qs = qs.filter(lease_id=lease_id)

        if search := params.get("search"):
            qs = qs.filter(
                Q(lease__lease_number__icontains=search)
                | Q(lease__primary_tenant__full_name__icontains=search)
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

    @action(detail=True, methods=["post"], url_path="payments",
            permission_classes=[IsAgentOrAdmin])
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


class RentPaymentViewSet(AgencyScopedQuerysetMixin, mixins.RetrieveModelMixin, GenericViewSet):
    """
    Read-only viewset for individual payments, plus the reverse action.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = RentPaymentSerializer
    queryset = RentPayment.objects.select_related("invoice", "created_by")

    def get_queryset(self):
        user = self.request.user

        # Phase 2.7: tenants have no agency_id; bypass the mixin for tenants.
        if user.is_authenticated and user.role == User.Role.TENANT:
            from apps.tenant_portal.views import get_tenant_leases
            tenant_lease_ids = get_tenant_leases(user).values_list("pk", flat=True)
            return RentPayment.objects.select_related("invoice", "created_by").filter(
                invoice__lease_id__in=tenant_lease_ids
            )

        qs = super().get_queryset()
        if not (user.role == User.Role.ADMIN or user.is_superuser):
            # Owner and all agent/staff roles: layer on accessible properties.
            from apps.properties.access import get_accessible_property_ids
            prop_ids = get_accessible_property_ids(user)
            qs = qs.filter(invoice__lease__unit__property_id__in=prop_ids)

        return qs

    @action(detail=True, methods=["post"], url_path="reverse",
            permission_classes=[IsAgentOrAdmin])
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
    AgencyScopedQuerysetMixin,
    AgencyStampedCreateMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    """
    Create + read viewset for UnmatchedPayment + manual assign action.

    Restricted to agency_admin and admin roles only — unmatched deposits are
    financial reconciliation records that tenants and owners must not access.

    Operators may manually enter an unmatched deposit (create) but update
    and destroy are excluded — once quarantined, a record is only resolved
    via the assign action, preserving the audit trail.
    """

    permission_classes = [IsAdminOrAgencyAdmin]
    serializer_class = UnmatchedPaymentSerializer
    queryset = UnmatchedPayment.objects.select_related("assigned_to_invoice", "resolved_payment")

    def get_queryset(self):
        qs = super().get_queryset()
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
