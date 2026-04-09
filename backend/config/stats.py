from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.models import User
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

        return Response({
            "total_properties": Property.objects.count(),
            "total_units": real_units + unitless_properties,
            "occupied_units": Unit.objects.filter(status="occupied").count(),
            "available_units": Unit.objects.filter(status="available").count() + unitless_properties,
            "active_tenants": User.objects.filter(role="tenant", is_active=True).count(),
            "active_leases": Lease.objects.filter(status="active").count(),
            "open_maintenance": MaintenanceRequest.objects.filter(status="open").count(),
            "in_progress_maintenance": MaintenanceRequest.objects.filter(status="in_progress").count(),
            "total_suppliers": Supplier.objects.count(),
            "active_suppliers": Supplier.objects.filter(is_active=True).count(),
        })
