from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import MaintenanceRequest, Supplier
from .serializers import (
    MaintenanceRequestSerializer,
    SupplierListSerializer,
    SupplierSerializer,
)


class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    serializer_class = MaintenanceRequestSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "priority", "unit", "supplier"]

    def get_queryset(self):
        user = self.request.user
        qs = MaintenanceRequest.objects.select_related("supplier")
        if user.role == "tenant":
            return qs.filter(tenant=user)
        return qs.all()


class SupplierViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filterset_fields = ["is_active"]

    def get_queryset(self):
        return Supplier.objects.prefetch_related("trades").annotate(
            active_jobs_count=Count(
                "assigned_requests",
                filter=Q(assigned_requests__status__in=["open", "in_progress"]),
            )
        )

    def get_serializer_class(self):
        if self.action == "list":
            return SupplierListSerializer
        return SupplierSerializer

    @action(detail=True, methods=["get"])
    def requests(self, request, pk=None):
        supplier = self.get_object()
        qs = supplier.assigned_requests.select_related("unit__property").all()
        data = MaintenanceRequestSerializer(qs, many=True).data
        return Response(data)
