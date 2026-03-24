from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.models import User
from apps.properties.models import Property, Unit
from apps.leases.models import Lease
from apps.maintenance.models import MaintenanceRequest


class StatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "total_properties": Property.objects.count(),
            "total_units": Unit.objects.count(),
            "occupied_units": Unit.objects.filter(status="occupied").count(),
            "available_units": Unit.objects.filter(status="available").count(),
            "active_tenants": User.objects.filter(role="tenant", is_active=True).count(),
            "active_leases": Lease.objects.filter(status="active").count(),
            "open_maintenance": MaintenanceRequest.objects.filter(status="open").count(),
            "in_progress_maintenance": MaintenanceRequest.objects.filter(status="in_progress").count(),
        })
