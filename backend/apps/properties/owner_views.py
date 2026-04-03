"""Owner-facing API endpoints."""
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import IsOwnerOrStaff
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Property
from apps.maintenance.models import MaintenanceRequest


class OwnerDashboardView(APIView):
    permission_classes = [IsOwnerOrStaff]

    def get(self, request):
        user = request.user
        if not hasattr(user, "person_profile"):
            return Response({
                "total_properties": 0,
                "active_issues": 0,
                "occupancy_rate": 0,
            })

        person = user.person_profile
        props = Property.objects.filter(owner=person)
        total = props.count()
        units = sum(p.units.count() for p in props)
        occupied = sum(p.units.filter(status="occupied").count() for p in props)
        issues = MaintenanceRequest.objects.filter(
            unit__property__owner=person,
            status__in=["open", "in_progress"],
        ).count()

        return Response({
            "total_properties": total,
            "total_units": units,
            "occupied_units": occupied,
            "occupancy_rate": round((occupied / units * 100) if units else 0),
            "active_issues": issues,
        })


class OwnerPropertiesView(APIView):
    permission_classes = [IsOwnerOrStaff]

    def get(self, request):
        user = request.user
        if not hasattr(user, "person_profile"):
            return Response([])

        person = user.person_profile
        props = Property.objects.filter(owner=person).prefetch_related("units")

        data = []
        for p in props:
            units = p.units.all()
            data.append({
                "id": p.id,
                "name": p.name,
                "property_type": p.property_type,
                "city": p.city,
                "address": p.address,
                "unit_count": units.count(),
                "occupied_units": units.filter(status="occupied").count(),
                "active_issues": MaintenanceRequest.objects.filter(
                    unit__property=p,
                    status__in=["open", "in_progress"],
                ).count(),
            })

        return Response(data)
