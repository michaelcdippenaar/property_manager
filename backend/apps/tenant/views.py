from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsAgentOrAdmin

from .models import Tenant, TenantUnitAssignment
from .serializers import (
    AssignUnitSerializer,
    TenantSerializer,
    TenantUnitAssignmentSerializer,
)


class TenantViewSet(viewsets.ModelViewSet):
    """CRUD for Tenant records + assign-unit action."""

    serializer_class = TenantSerializer
    permission_classes = [IsAgentOrAdmin]

    def get_queryset(self):
        qs = (
            Tenant.objects.select_related("person", "linked_user")
            .prefetch_related("assignments__unit", "assignments__property")
        )
        # Optional filter: ?property=<id> — only tenants with assignments on this property
        property_id = self.request.query_params.get("property")
        if property_id:
            qs = qs.filter(assignments__property_id=property_id).distinct()
        return qs

    @action(detail=False, methods=["post"], url_path="assign-unit")
    def assign_unit(self, request):
        """Manually assign a tenant to a unit."""
        ser = AssignUnitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        tenant = ser.validated_data["tenant_id"]
        unit = ser.validated_data["unit_id"]

        try:
            assignment = tenant.assign_unit(
                unit=unit,
                start_date=ser.validated_data["start_date"],
                end_date=ser.validated_data["end_date"],
                assigned_by=request.user,
                notes=ser.validated_data["notes"],
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            TenantUnitAssignmentSerializer(assignment).data,
            status=status.HTTP_201_CREATED,
        )


class TenantUnitAssignmentViewSet(viewsets.ModelViewSet):
    """List / update / delete unit assignments."""

    serializer_class = TenantUnitAssignmentSerializer
    permission_classes = [IsAgentOrAdmin]

    def get_queryset(self):
        qs = TenantUnitAssignment.objects.select_related(
            "tenant__person", "unit", "property", "lease", "assigned_by",
        )
        # Filter by property
        property_id = self.request.query_params.get("property")
        if property_id:
            qs = qs.filter(property_id=property_id)
        # Filter by unit
        unit_id = self.request.query_params.get("unit")
        if unit_id:
            qs = qs.filter(unit_id=unit_id)
        # Filter by tenant
        tenant_id = self.request.query_params.get("tenant")
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs
