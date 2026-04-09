from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.models import Person
from apps.properties.models import Property, Unit
from apps.leases.models import Lease
from apps.maintenance.models import MaintenanceRequest, Supplier


class StatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # A property without any Unit rows is treated as a single implicit
        # available unit (mirrors get_property_active_lease_info on the
        # PropertySerializer). Without this, dashboards show fewer units than
        # properties whenever a property has not been broken out into units.
        unitless_properties = Property.objects.filter(units__isnull=True).count()
        real_units = Unit.objects.count()

        # "Active" on the dashboard means *currently in effect today* — not
        # just the manual status flag. A lease whose status is "active" but
        # whose start_date is in the future (e.g. a renewal signed in advance)
        # should not inflate the "currently leasing" / "signed agreements"
        # tiles. Same for leases that have rolled past their end_date but
        # haven't been transitioned to "expired" yet.
        today = timezone.localdate()
        in_effect_leases = Lease.objects.filter(
            status="active",
            start_date__lte=today,
            end_date__gte=today,
        )

        # A tenant is "active" if they appear on at least one in-effect lease
        # — either as the primary signatory or as a co-tenant. Counting User
        # rows here is wrong because many tenants are Person records without
        # a portal login.
        active_tenants = Person.objects.filter(
            Q(leases_as_primary__in=in_effect_leases)
            | Q(co_tenancies__lease__in=in_effect_leases)
        ).distinct().count()

        return Response({
            "total_properties": Property.objects.count(),
            "total_units": real_units + unitless_properties,
            "occupied_units": Unit.objects.filter(status="occupied").count(),
            "available_units": Unit.objects.filter(status="available").count() + unitless_properties,
            "active_tenants": active_tenants,
            "active_leases": in_effect_leases.count(),
            "open_maintenance": MaintenanceRequest.objects.filter(status="open").count(),
            "in_progress_maintenance": MaintenanceRequest.objects.filter(status="in_progress").count(),
            "total_suppliers": Supplier.objects.count(),
            "active_suppliers": Supplier.objects.filter(is_active=True).count(),
        })
