"""
Property Viewing Views
======================
CRUD + calendar + convert-to-lease for PropertyViewing.

Endpoints:
  GET/POST  /api/v1/properties/viewings/
  GET/PATCH/DELETE  /api/v1/properties/viewings/{id}/
  GET  /api/v1/properties/viewings/calendar/?from=YYYY-MM-DD&to=YYYY-MM-DD
  POST /api/v1/properties/viewings/{id}/convert-to-lease/
"""
import logging
from datetime import date

from django.db import transaction
from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsAgentOrAdmin
from apps.properties.access import get_accessible_property_ids

from .models import PropertyViewing
from .serializers import PropertyViewingSerializer

logger = logging.getLogger(__name__)


class PropertyViewingViewSet(viewsets.ModelViewSet):
    """
    CRUD for property viewings, scoped to properties accessible by the requesting user.
    """

    serializer_class   = PropertyViewingSerializer
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]
    http_method_names  = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        prop_ids = get_accessible_property_ids(self.request.user)
        qs = PropertyViewing.objects.filter(
            property_id__in=prop_ids
        ).select_related("property", "unit", "prospect", "agent")

        # Optional filter by property
        property_id = self.request.query_params.get("property")
        if property_id:
            qs = qs.filter(property_id=property_id)

        # Optional filter by status
        viewing_status = self.request.query_params.get("status")
        if viewing_status:
            qs = qs.filter(status=viewing_status)

        return qs

    def perform_create(self, serializer):
        # Validate the target property is accessible by this user
        prop = serializer.validated_data.get("property")
        if prop:
            accessible = get_accessible_property_ids(self.request.user)
            if prop.pk not in accessible:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("You do not have access to the selected property.")
        # Auto-assign agent to requesting user if not provided
        if not serializer.validated_data.get("agent"):
            serializer.save(agent=self.request.user)
        else:
            serializer.save()

    @action(detail=False, methods=["get"], url_path="calendar")
    def calendar(self, request):
        """
        Returns all viewings between ?from=YYYY-MM-DD and ?to=YYYY-MM-DD.
        """
        from_str = request.query_params.get("from")
        to_str   = request.query_params.get("to")

        if not from_str or not to_str:
            return Response(
                {"detail": "'from' and 'to' query parameters are required (YYYY-MM-DD)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from_date = date.fromisoformat(from_str)
            to_date   = date.fromisoformat(to_str)
        except ValueError:
            return Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = self.get_queryset().filter(
            scheduled_at__date__gte=from_date,
            scheduled_at__date__lte=to_date,
        )
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="convert-to-lease")
    def convert_to_lease(self, request, pk=None):
        """
        Convert a completed viewing into a lease.

        Expected body:
          { start_date, end_date, monthly_rent, deposit }

        Creates a Lease atomically and marks the viewing as converted.
        """
        viewing = self.get_object()

        blocked_statuses = (PropertyViewing.Status.CANCELLED, PropertyViewing.Status.CONVERTED)
        if viewing.status in blocked_statuses:
            return Response(
                {"detail": f"Viewing cannot be converted: status is '{viewing.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not viewing.unit_id:
            return Response(
                {"detail": "A specific unit must be selected before converting to a lease."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate required fields
        required = ["start_date", "end_date", "monthly_rent", "deposit"]
        missing  = [f for f in required if f not in request.data]
        if missing:
            return Response(
                {"detail": f"Missing required fields: {', '.join(missing)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                from apps.leases.models import Lease
                from apps.leases.serializers import LeaseSerializer

                lease = Lease.objects.create(
                    unit=viewing.unit,
                    primary_tenant=viewing.prospect,
                    start_date=request.data["start_date"],
                    end_date=request.data["end_date"],
                    monthly_rent=request.data["monthly_rent"],
                    deposit=request.data["deposit"],
                    status=Lease.Status.PENDING if hasattr(Lease, "Status") else "pending",
                )

                viewing.status             = PropertyViewing.Status.CONVERTED
                viewing.converted_to_lease = lease
                viewing.save(update_fields=["status", "converted_to_lease", "updated_at"])

            return Response(
                LeaseSerializer(lease, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )

        except Exception as exc:
            logger.exception("Failed to convert viewing %s to lease", pk)
            return Response(
                {"detail": f"Conversion failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
