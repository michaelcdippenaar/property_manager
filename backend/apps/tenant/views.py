from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import User
from apps.accounts.permissions import IsAgentOrAdmin
from apps.accounts.scoping import AgencyScopedQuerysetMixin, AgencyStampedCreateMixin

from .models import Tenant, TenantOnboarding, TenantUnitAssignment
from .serializers import (
    AssignUnitSerializer,
    TenantOnboardingCreateSerializer,
    TenantOnboardingSerializer,
    TenantSerializer,
    TenantUnitAssignmentSerializer,
)


class TenantViewSet(AgencyScopedQuerysetMixin, AgencyStampedCreateMixin, viewsets.ModelViewSet):
    """CRUD for Tenant records + assign-unit action."""

    serializer_class = TenantSerializer
    permission_classes = [IsAgentOrAdmin]
    queryset = (
        Tenant.objects.select_related("person", "linked_user")
        .prefetch_related("assignments__unit", "assignments__property")
    )

    def get_queryset(self):
        qs = super().get_queryset()
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


class TenantUnitAssignmentViewSet(
    AgencyScopedQuerysetMixin, AgencyStampedCreateMixin, viewsets.ModelViewSet
):
    """List / update / delete unit assignments."""

    serializer_class = TenantUnitAssignmentSerializer
    permission_classes = [IsAgentOrAdmin]
    queryset = TenantUnitAssignment.objects.select_related(
        "tenant__person", "unit", "property", "lease", "assigned_by",
    )

    def get_queryset(self):
        qs = super().get_queryset()
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


class TenantOnboardingViewSet(viewsets.ModelViewSet):
    """
    CRUD + tick-item action for TenantOnboarding checklists.

    Agents/admins: full access.
    Tenants: read-only (GET list/detail) to power the welcome screen.

    Phase 2.7: Tenants and owners have no agency_id, so the
    AgencyScopedQuerysetMixin is NOT applied at the class level.
    Instead, agency-staff branches inside ``get_queryset`` add the
    explicit agency filter (defence in depth) and ``perform_create``
    stamps agency_id from the resolved lease.
    """

    http_method_names = ["get", "post", "patch", "head", "options"]
    queryset = TenantOnboarding.objects.all()

    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            # Both agents and tenants may read
            return [IsAuthenticated()]
        return [IsAgentOrAdmin()]

    def get_serializer_class(self):
        if self.action == "create":
            return TenantOnboardingCreateSerializer
        return TenantOnboardingSerializer

    def get_queryset(self):
        qs = TenantOnboarding.objects.select_related(
            "lease__primary_tenant",
            "lease__unit__property",
        )
        user = self.request.user
        if user.role == User.Role.TENANT:
            # Tenant sees only their own onboarding records
            qs = qs.filter(
                lease__primary_tenant__linked_user=user,
            )
        elif user.role == User.Role.OWNER:
            # Owner sees only records for properties they own
            from apps.properties.models import Landlord, PropertyOwnership

            person = getattr(user, "person_profile", None)
            if not person:
                return qs.none()
            landlord_ids = Landlord.objects.filter(person=person).values_list("pk", flat=True)
            owned_property_ids = PropertyOwnership.objects.filter(
                landlord_id__in=landlord_ids, is_current=True
            ).values_list("property_id", flat=True)
            qs = qs.filter(lease__unit__property_id__in=owned_property_ids)
        else:
            # Agents/admins: layer agency scoping (defence in depth) for
            # everyone except ADMIN/superuser.
            if not (user.role == User.Role.ADMIN or user.is_superuser):
                if not user.agency_id:
                    return qs.none()
                qs = qs.filter(agency_id=user.agency_id)
            lease_id = self.request.query_params.get("lease")
            if lease_id:
                qs = qs.filter(lease_id=lease_id)
            property_id = self.request.query_params.get("property")
            if property_id:
                qs = qs.filter(lease__unit__property_id=property_id)
        return qs

    def create(self, request, *args, **kwargs):
        ser = TenantOnboardingCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        onboarding = ser.save()
        # Phase 2.7: stamp agency_id from the lease so the row is tenant-scoped.
        if onboarding.agency_id is None and getattr(onboarding.lease, "agency_id", None):
            onboarding.agency_id = onboarding.lease.agency_id
            onboarding.save(update_fields=["agency_id"])
        return Response(
            TenantOnboardingSerializer(onboarding).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        """PATCH — tick one or more checklist items."""
        instance = self.get_object()
        ser = TenantOnboardingSerializer(instance, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        onboarding = ser.save()
        return Response(TenantOnboardingSerializer(onboarding).data)
