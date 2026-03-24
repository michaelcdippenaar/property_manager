from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import MaintenanceRequest
from .serializers import MaintenanceRequestSerializer


class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    serializer_class = MaintenanceRequestSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "priority", "unit"]

    def get_queryset(self):
        user = self.request.user
        if user.role == "tenant":
            return MaintenanceRequest.objects.filter(tenant=user)
        return MaintenanceRequest.objects.all()
