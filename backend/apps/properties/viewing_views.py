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
from apps.accounts.scoping import AgencyScopedQuerysetMixin, AgencyStampedCreateMixin
from apps.properties.access import get_accessible_property_ids

from .models import PropertyViewing
from .serializers import PropertyViewingSerializer

logger = logging.getLogger(__name__)


class PropertyViewingViewSet(AgencyScopedQuerysetMixin, AgencyStampedCreateMixin, viewsets.ModelViewSet):
    """
    CRUD for property viewings, scoped to properties accessible by the requesting user.
    """

    queryset           = PropertyViewing.objects.all()
    serializer_class   = PropertyViewingSerializer
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]
    http_method_names  = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        base = super().get_queryset()
        prop_ids = get_accessible_property_ids(self.request.user)
        qs = base.filter(
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
            serializer.validated_data["agent"] = self.request.user
        # Stamp agency via mixin.
        super().perform_create(serializer)

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

        # Resolve unit: prefer viewing.unit, fall back to request body.
        # If neither is set and the property has no units at all, auto-create a
        # default unit so single-family homes (which often have no explicit unit
        # record) can still have leases attached. Mirrors `import_view.py`.
        unit_id = viewing.unit_id or request.data.get("unit")
        auto_created_unit = None
        if not unit_id:
            from .models import Unit
            if not viewing.property.units.exists():
                auto_created_unit = Unit.objects.create(
                    property=viewing.property,
                    unit_number="1",
                    rent_amount=request.data.get("monthly_rent") or 0,
                    # Phase 4 / QA-round-5 bug 1: stamp agency from the parent
                    # property so the new Unit doesn't fall through with
                    # agency_id=NULL (which would bypass tenant_objects scoping
                    # and re-create orphan rows).
                    agency_id=viewing.property.agency_id,
                )
                unit_id = auto_created_unit.pk
            else:
                return Response(
                    {"detail": "A specific unit must be provided (either on the viewing or in the request body)."},
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
                    unit_id=unit_id,
                    primary_tenant=viewing.prospect,
                    start_date=request.data["start_date"],
                    end_date=request.data["end_date"],
                    monthly_rent=request.data["monthly_rent"],
                    deposit=request.data["deposit"],
                    status=Lease.Status.PENDING if hasattr(Lease, "Status") else "pending",
                    # Phase 4 / QA-round-5 bug 1: stamp agency from the parent
                    # property (single source of truth) so the lease is visible
                    # to tenant_objects queries and is correctly scoped.
                    agency_id=viewing.property.agency_id,
                )

                viewing.status             = PropertyViewing.Status.CONVERTED
                viewing.converted_to_lease = lease
                viewing.save(update_fields=["status", "converted_to_lease", "updated_at"])

            payload = {
                "lease": LeaseSerializer(lease, context={"request": request}).data,
            }
            if auto_created_unit is not None:
                payload["auto_created_unit"] = {
                    "id": auto_created_unit.pk,
                    "unit_number": auto_created_unit.unit_number,
                    "property_id": auto_created_unit.property_id,
                }
                payload["message"] = (
                    f"Default unit '{auto_created_unit.unit_number}' was created automatically "
                    "because the property had no existing units."
                )
            return Response(payload, status=status.HTTP_201_CREATED)

        except Exception as exc:
            logger.exception("Failed to convert viewing %s to lease", pk)
            return Response(
                {"detail": f"Conversion failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
