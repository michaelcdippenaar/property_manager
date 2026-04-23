"""Owner-facing API endpoints — RNT-QUAL-006."""
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import IsOwnerOrStaff
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Property
from apps.maintenance.models import MaintenanceRequest
from .dashboard_service import get_dashboard_stats, get_activity_feed


class OwnerDashboardView(APIView):
    """
    GET /api/v1/properties/owner/dashboard/

    Returns cached portfolio stats + payment performance widget.
    Cache is invalidated on: rent payment, lease signed, maintenance
    created/closed, mandate signed.  See dashboard_signals.py.
    """

    permission_classes = [IsOwnerOrStaff]

    def get(self, request):
        user = request.user
        if not hasattr(user, "person_profile"):
            return Response({
                "total_properties": 0,
                "active_issues": 0,
                "occupancy_rate": 0,
                "payment_performance": None,
                "last_updated": None,
            })

        person = user.person_profile
        return Response(get_dashboard_stats(person.pk))


class OwnerActivityFeedView(APIView):
    """
    GET /api/v1/properties/owner/activity/

    Returns last 20 events across the owner's portfolio:
    rent received, maintenance opened/closed, lease signed, mandate signed.

    Optional query param: ?limit=N (max 50).
    """

    permission_classes = [IsOwnerOrStaff]

    def get(self, request):
        user = request.user
        if not hasattr(user, "person_profile"):
            return Response([])

        try:
            limit = min(int(request.query_params.get("limit", 20)), 50)
        except (ValueError, TypeError):
            limit = 20

        person = user.person_profile
        return Response(get_activity_feed(person.pk, limit=limit))


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
