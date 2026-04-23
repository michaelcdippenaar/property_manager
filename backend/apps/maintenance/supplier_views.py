"""
Supplier-facing API endpoints.
All views require an authenticated user with role=supplier linked to a Supplier record.
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsSupplier

from .models import (
    JobDispatch,
    JobQuote,
    JobQuoteRequest,
    MaintenanceActivity,
    MaintenanceRequest,
    Supplier,
    SupplierDocument,
    SupplierInvoice,
)
from .supplier_serializers import (
    SupplierDocumentSerializer,
    SupplierInvoiceSerializer,
    SupplierInvoiceSubmitSerializer,
    SupplierJobQuoteSerializer,
    SupplierJobSerializer,
    SupplierProfileSerializer,
)


class SupplierMixin:
    """Get the Supplier linked to the authenticated user."""

    def get_supplier(self, request):
        if not hasattr(request.user, "supplier_profile"):
            return None
        return request.user.supplier_profile


class SupplierDashboardView(SupplierMixin, APIView):
    permission_classes = [IsSupplier]

    def get(self, request):
        supplier = self.get_supplier(request)
        if not supplier:
            return Response({"detail": "No supplier profile linked"}, status=status.HTTP_403_FORBIDDEN)

        qrs = JobQuoteRequest.objects.filter(supplier=supplier)

        # Invoice payment stats
        invoices = SupplierInvoice.objects.filter(quote_request__supplier=supplier)
        awaiting_payment_count = invoices.filter(status="approved").count()
        paid_count = invoices.filter(status="paid").count()
        outstanding_amount = (
            invoices.filter(status__in=["pending", "approved"])
            .aggregate(total=Sum("total_amount"))["total"]
            or Decimal("0.00")
        )
        paid_amount = (
            invoices.filter(status="paid")
            .aggregate(total=Sum("total_amount"))["total"]
            or Decimal("0.00")
        )

        return Response({
            "new_requests": qrs.filter(status__in=["pending", "viewed"]).count(),
            "pending_quotes": qrs.filter(status="quoted").count(),
            "awarded_jobs": qrs.filter(status="awarded").count(),
            "completed_jobs": supplier.assigned_requests.filter(status__in=["resolved", "closed"]).count(),
            "awaiting_payment": awaiting_payment_count,
            "paid_jobs": paid_count,
            "outstanding_amount": str(outstanding_amount),
            "paid_amount": str(paid_amount),
            "rating": float(supplier.rating) if supplier.rating else None,
            "company_name": supplier.display_name,
        })


class SupplierJobsView(SupplierMixin, APIView):
    permission_classes = [IsSupplier]

    def get(self, request):
        supplier = self.get_supplier(request)
        if not supplier:
            return Response({"detail": "No supplier profile linked"}, status=status.HTTP_403_FORBIDDEN)

        status_filter = request.query_params.get("status")
        qrs = JobQuoteRequest.objects.filter(supplier=supplier).select_related(
            "dispatch__maintenance_request__unit__property",
        ).prefetch_related("quote", "invoice").order_by("-created_at")

        if status_filter == "in_progress":
            # Jobs where the linked maintenance request is in_progress
            qrs = qrs.filter(
                status="awarded",
                dispatch__maintenance_request__status="in_progress",
            )
        elif status_filter == "awaiting_payment":
            # Awarded jobs with an approved invoice waiting to be paid
            qrs = qrs.filter(status="awarded", invoice__status="approved")
        elif status_filter == "paid":
            qrs = qrs.filter(status="awarded", invoice__status="paid")
        elif status_filter:
            qrs = qrs.filter(status=status_filter)

        return Response(SupplierJobSerializer(qrs, many=True).data)


class SupplierJobDetailView(SupplierMixin, APIView):
    permission_classes = [IsSupplier]

    def get(self, request, pk):
        supplier = self.get_supplier(request)
        if not supplier:
            return Response({"detail": "No supplier profile linked"}, status=status.HTTP_403_FORBIDDEN)

        try:
            qr = JobQuoteRequest.objects.select_related(
                "dispatch__maintenance_request__unit__property",
            ).prefetch_related("quote", "invoice").get(id=pk, supplier=supplier)
        except JobQuoteRequest.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        # Mark as viewed
        if not qr.viewed_at:
            qr.viewed_at = timezone.now()
            if qr.status == "pending":
                qr.status = "viewed"
            qr.save()

        return Response(SupplierJobSerializer(qr).data)


class SupplierJobQuoteView(SupplierMixin, APIView):
    permission_classes = [IsSupplier]

    def post(self, request, pk):
        supplier = self.get_supplier(request)
        if not supplier:
            return Response({"detail": "No supplier profile linked"}, status=status.HTTP_403_FORBIDDEN)

        try:
            qr = JobQuoteRequest.objects.get(id=pk, supplier=supplier)
        except JobQuoteRequest.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        if qr.status in ("awarded", "expired"):
            return Response({"detail": "This job is closed"}, status=status.HTTP_400_BAD_REQUEST)
        if hasattr(qr, "quote"):
            return Response({"detail": "Quote already submitted"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SupplierJobQuoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(quote_request=qr)

        qr.status = "quoted"
        qr.save()

        dispatch = qr.dispatch
        if dispatch.status == JobDispatch.Status.SENT:
            dispatch.status = JobDispatch.Status.QUOTING
            dispatch.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SupplierJobDeclineView(SupplierMixin, APIView):
    permission_classes = [IsSupplier]

    def post(self, request, pk):
        supplier = self.get_supplier(request)
        if not supplier:
            return Response({"detail": "No supplier profile linked"}, status=status.HTTP_403_FORBIDDEN)

        try:
            qr = JobQuoteRequest.objects.get(id=pk, supplier=supplier)
        except JobQuoteRequest.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        if qr.status in ("awarded", "expired"):
            return Response({"detail": "This job is closed"}, status=status.HTTP_400_BAD_REQUEST)

        qr.status = "declined"
        qr.save()
        return Response({"status": "declined"})


class SupplierJobAcceptView(SupplierMixin, APIView):
    """
    Supplier explicitly accepts an awarded job and marks it in-progress.
    Pushes a MaintenanceActivity log entry that the agent and tenant chat can see.
    """

    permission_classes = [IsSupplier]

    def post(self, request, pk):
        supplier = self.get_supplier(request)
        if not supplier:
            return Response({"detail": "No supplier profile linked"}, status=status.HTTP_403_FORBIDDEN)

        try:
            qr = JobQuoteRequest.objects.select_related(
                "dispatch__maintenance_request"
            ).get(id=pk, supplier=supplier)
        except JobQuoteRequest.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        if qr.status != "awarded":
            return Response({"detail": "Only awarded jobs can be accepted"}, status=status.HTTP_400_BAD_REQUEST)

        mr = qr.dispatch.maintenance_request
        if mr.status not in (MaintenanceRequest.Status.OPEN, MaintenanceRequest.Status.IN_PROGRESS):
            return Response({"detail": "Job is already resolved or closed"}, status=status.HTTP_400_BAD_REQUEST)

        # Advance maintenance request to in_progress
        if mr.status == MaintenanceRequest.Status.OPEN:
            mr.status = MaintenanceRequest.Status.IN_PROGRESS
            mr.save(update_fields=["status", "updated_at"])

        # Log activity so agent feed and tenant chat can surface it
        MaintenanceActivity.objects.create(
            request=mr,
            activity_type=MaintenanceActivity.ActivityType.STATUS_CHANGE,
            message=f"Supplier {supplier.display_name} accepted the job and will start work.",
            metadata={"supplier_id": supplier.id, "action": "accepted"},
        )

        return Response({"status": "accepted", "mr_status": mr.status})


class SupplierJobStatusUpdateView(SupplierMixin, APIView):
    """
    Supplier updates job status (in_progress → completed) with an optional progress photo.
    Logs a MaintenanceActivity that appears in the agent and tenant chat feeds.
    """

    permission_classes = [IsSupplier]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        supplier = self.get_supplier(request)
        if not supplier:
            return Response({"detail": "No supplier profile linked"}, status=status.HTTP_403_FORBIDDEN)

        try:
            qr = JobQuoteRequest.objects.select_related(
                "dispatch__maintenance_request"
            ).get(id=pk, supplier=supplier)
        except JobQuoteRequest.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        if qr.status != "awarded":
            return Response({"detail": "Only awarded jobs can be updated"}, status=status.HTTP_400_BAD_REQUEST)

        new_status = request.data.get("status")
        note = request.data.get("note", "").strip()
        photo = request.FILES.get("photo")

        valid_statuses = {
            MaintenanceRequest.Status.IN_PROGRESS,
            MaintenanceRequest.Status.RESOLVED,
        }
        if new_status not in valid_statuses:
            return Response(
                {"detail": f"status must be one of: {', '.join(valid_statuses)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mr = qr.dispatch.maintenance_request
        old_status = mr.status
        mr.status = new_status
        if new_status == MaintenanceRequest.Status.RESOLVED:
            mr.resolved_at = timezone.now()
        mr.save(update_fields=["status", "resolved_at", "updated_at"])

        # Build activity message
        status_labels = {
            MaintenanceRequest.Status.IN_PROGRESS: "in progress",
            MaintenanceRequest.Status.RESOLVED: "complete",
        }
        msg_parts = [f"Supplier marked job as {status_labels.get(new_status, new_status)}."]
        if note:
            msg_parts.append(note)
        message = " ".join(msg_parts)

        activity = MaintenanceActivity.objects.create(
            request=mr,
            activity_type=MaintenanceActivity.ActivityType.STATUS_CHANGE,
            message=message,
            file=photo if photo else None,
            metadata={
                "supplier_id": supplier.id,
                "old_status": old_status,
                "new_status": new_status,
            },
        )

        return Response({
            "status": new_status,
            "activity_id": activity.id,
            "message": message,
        })


class SupplierInvoiceView(SupplierMixin, APIView):
    """
    GET  /supplier/jobs/<pk>/invoice/  — retrieve existing invoice
    POST /supplier/jobs/<pk>/invoice/  — submit invoice for agent approval
    """

    permission_classes = [IsSupplier]
    parser_classes = [MultiPartParser, FormParser]

    def _get_qr(self, request, pk):
        supplier = self.get_supplier(request)
        if not supplier:
            return None, None, Response(
                {"detail": "No supplier profile linked"}, status=status.HTTP_403_FORBIDDEN
            )
        try:
            qr = JobQuoteRequest.objects.select_related(
                "dispatch__maintenance_request"
            ).get(id=pk, supplier=supplier)
        except JobQuoteRequest.DoesNotExist:
            return None, None, Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return supplier, qr, None

    def get(self, request, pk):
        supplier, qr, err = self._get_qr(request, pk)
        if err:
            return err
        try:
            invoice = qr.invoice
        except SupplierInvoice.DoesNotExist:
            return Response({"detail": "No invoice submitted yet"}, status=status.HTTP_404_NOT_FOUND)
        return Response(SupplierInvoiceSerializer(invoice).data)

    def post(self, request, pk):
        supplier, qr, err = self._get_qr(request, pk)
        if err:
            return err

        if qr.status != "awarded":
            return Response(
                {"detail": "You can only invoice for awarded jobs"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if hasattr(qr, "invoice"):
            return Response(
                {"detail": "Invoice already submitted. Contact your agent to resubmit."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SupplierInvoiceSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = serializer.save(quote_request=qr)

        # Log activity on the maintenance request
        mr = qr.dispatch.maintenance_request
        MaintenanceActivity.objects.create(
            request=mr,
            activity_type=MaintenanceActivity.ActivityType.NOTE,
            message=f"Supplier submitted invoice of R{invoice.total_amount} — awaiting approval.",
            metadata={"supplier_id": supplier.id, "invoice_id": invoice.id},
        )

        return Response(SupplierInvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)


class SupplierPaymentHistoryView(SupplierMixin, APIView):
    """
    Returns invoice history for the logged-in supplier with totals.
    """

    permission_classes = [IsSupplier]

    def get(self, request):
        supplier = self.get_supplier(request)
        if not supplier:
            return Response({"detail": "No supplier profile linked"}, status=status.HTTP_403_FORBIDDEN)

        invoices = (
            SupplierInvoice.objects.filter(quote_request__supplier=supplier)
            .select_related("quote_request__dispatch__maintenance_request")
            .order_by("-submitted_at")
        )

        outstanding = (
            invoices.filter(status__in=["pending", "approved"])
            .aggregate(total=Sum("total_amount"))["total"]
            or Decimal("0.00")
        )
        paid = (
            invoices.filter(status="paid")
            .aggregate(total=Sum("total_amount"))["total"]
            or Decimal("0.00")
        )

        return Response({
            "outstanding_amount": str(outstanding),
            "paid_amount": str(paid),
            "invoices": SupplierInvoiceSerializer(invoices, many=True).data,
        })


class SupplierProfileView(SupplierMixin, APIView):
    permission_classes = [IsSupplier]

    def get(self, request):
        supplier = self.get_supplier(request)
        if not supplier:
            return Response({"detail": "No supplier profile linked"}, status=status.HTTP_403_FORBIDDEN)
        return Response(SupplierProfileSerializer(supplier).data)

    def patch(self, request):
        supplier = self.get_supplier(request)
        if not supplier:
            return Response({"detail": "No supplier profile linked"}, status=status.HTTP_403_FORBIDDEN)
        serializer = SupplierProfileSerializer(supplier, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SupplierDocumentsView(SupplierMixin, APIView):
    permission_classes = [IsSupplier]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        supplier = self.get_supplier(request)
        if not supplier:
            return Response({"detail": "No supplier profile linked"}, status=status.HTTP_403_FORBIDDEN)
        return Response(SupplierDocumentSerializer(supplier.documents.all(), many=True).data)

    def post(self, request):
        supplier = self.get_supplier(request)
        if not supplier:
            return Response({"detail": "No supplier profile linked"}, status=status.HTTP_403_FORBIDDEN)
        serializer = SupplierDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(supplier=supplier)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SupplierCalendarView(SupplierMixin, APIView):
    permission_classes = [IsSupplier]

    def get(self, request):
        supplier = self.get_supplier(request)
        if not supplier:
            return Response({"detail": "No supplier profile linked"}, status=status.HTTP_403_FORBIDDEN)

        # Get awarded jobs with quotes that have available_from dates
        awarded = JobQuoteRequest.objects.filter(
            supplier=supplier,
            status="awarded",
        ).select_related(
            "dispatch__maintenance_request__unit__property",
            "quote",
        ).filter(quote__isnull=False)

        items = []
        for qr in awarded:
            quote = qr.quote
            mr = qr.dispatch.maintenance_request
            start = quote.available_from
            if not start:
                continue
            days = quote.estimated_days or 1
            items.append({
                "quote_request_id": qr.id,
                "title": mr.title,
                "property_name": mr.unit.property.name if mr.unit else "",
                "start_date": start,
                "end_date": start + timedelta(days=days),
                "amount": quote.amount,
                "status": mr.status,
            })

        return Response(items)
