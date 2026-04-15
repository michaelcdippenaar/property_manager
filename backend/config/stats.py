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
        from apps.properties.access import get_accessible_property_ids

        # Scope all stats to the user's accessible properties
        prop_ids = get_accessible_property_ids(request.user)
        properties = Property.objects.filter(pk__in=prop_ids)
        units = Unit.objects.filter(property_id__in=prop_ids)

        # A property without any Unit rows is treated as a single implicit
        # available unit (mirrors get_property_active_lease_info on the
        # PropertySerializer).
        unitless_properties = properties.filter(units__isnull=True).count()
        real_units = units.count()

        # "Active" on the dashboard means *currently in effect today*
        today = timezone.localdate()
        in_effect_leases = Lease.objects.filter(
            status="active",
            start_date__lte=today,
            end_date__gte=today,
            unit__property_id__in=prop_ids,
        )

        # A tenant is "active" if they appear on at least one in-effect lease
        active_tenants = Person.objects.filter(
            Q(leases_as_primary__in=in_effect_leases)
            | Q(co_tenancies__lease__in=in_effect_leases)
        ).distinct().count()

        return Response({
            "total_properties": properties.count(),
            "total_units": real_units + unitless_properties,
            "occupied_units": units.filter(status="occupied").count(),
            "available_units": units.filter(status="available").count() + unitless_properties,
            "active_tenants": active_tenants,
            "active_leases": in_effect_leases.count(),
            "open_maintenance": MaintenanceRequest.objects.filter(status="open", unit__property_id__in=prop_ids).count(),
            "in_progress_maintenance": MaintenanceRequest.objects.filter(status="in_progress", unit__property_id__in=prop_ids).count(),
            "total_suppliers": Supplier.objects.count(),
            "active_suppliers": Supplier.objects.filter(is_active=True).count(),
        })
