"""
Supplier-facing API endpoints.
All views require an authenticated user with role=supplier linked to a Supplier record.
"""
from datetime import timedelta

from django.db.models import Q
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import JobDispatch, JobQuote, JobQuoteRequest, Supplier, SupplierDocument
from .supplier_serializers import (
    SupplierDocumentSerializer,
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
    permission_classes = [IsAuthenticated]

    def get(self, request):
        supplier = self.get_supplier(request)
        if not supplier:
            return Response({"detail": "No supplier profile linked"}, status=status.HTTP_403_FORBIDDEN)

        qrs = JobQuoteRequest.objects.filter(supplier=supplier)
        return Response({
            "new_requests": qrs.filter(status__in=["pending", "viewed"]).count(),
            "pending_quotes": qrs.filter(status="quoted").count(),
            "awarded_jobs": qrs.filter(status="awarded").count(),
            "completed_jobs": supplier.assigned_requests.filter(status__in=["resolved", "closed"]).count(),
            "rating": float(supplier.rating) if supplier.rating else None,
            "company_name": supplier.display_name,
        })


class SupplierJobsView(SupplierMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        supplier = self.get_supplier(request)
        if not supplier:
            return Response({"detail": "No supplier profile linked"}, status=status.HTTP_403_FORBIDDEN)

        status_filter = request.query_params.get("status")
        qrs = JobQuoteRequest.objects.filter(supplier=supplier).select_related(
            "dispatch__maintenance_request__unit__property",
        ).prefetch_related("quote").order_by("-created_at")

        if status_filter:
            qrs = qrs.filter(status=status_filter)

        return Response(SupplierJobSerializer(qrs, many=True).data)


class SupplierJobDetailView(SupplierMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        supplier = self.get_supplier(request)
        if not supplier:
            return Response({"detail": "No supplier profile linked"}, status=status.HTTP_403_FORBIDDEN)

        try:
            qr = JobQuoteRequest.objects.select_related(
                "dispatch__maintenance_request__unit__property",
            ).prefetch_related("quote").get(id=pk, supplier=supplier)
        except JobQuoteRequest.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        # Mark as viewed
        if not qr.viewed_at:
            from django.utils import timezone
            qr.viewed_at = timezone.now()
            if qr.status == "pending":
                qr.status = "viewed"
            qr.save()

        return Response(SupplierJobSerializer(qr).data)


class SupplierJobQuoteView(SupplierMixin, APIView):
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

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


class SupplierProfileView(SupplierMixin, APIView):
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]

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
