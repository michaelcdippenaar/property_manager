from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Property, PropertyGroup, Unit
from .serializers import PropertyGroupSerializer, PropertySerializer, UnitSerializer


class PropertyViewSet(viewsets.ModelViewSet):
    serializer_class = PropertySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("agent", "admin"):
            return Property.objects.filter(agent=user)
        return Property.objects.all()


class UnitViewSet(viewsets.ModelViewSet):
    serializer_class = UnitSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["property", "status"]

    def get_queryset(self):
        return Unit.objects.select_related("property")


class PropertyGroupViewSet(viewsets.ModelViewSet):
    serializer_class = PropertyGroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PropertyGroup.objects.prefetch_related("properties")
