from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Property, PropertyAgentConfig, PropertyGroup, Unit, UnitInfo
from .serializers import (
    PropertyAgentConfigSerializer, PropertyGroupSerializer,
    PropertySerializer, UnitInfoSerializer, UnitSerializer,
)


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


class UnitInfoViewSet(viewsets.ModelViewSet):
    serializer_class = UnitInfoSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["property", "unit"]

    def get_queryset(self):
        return UnitInfo.objects.select_related("property", "unit")


class PropertyAgentConfigViewSet(viewsets.ModelViewSet):
    serializer_class = PropertyAgentConfigSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["property"]

    def get_queryset(self):
        return PropertyAgentConfig.objects.select_related("property")

    @action(detail=False, methods=["get", "put", "patch"], url_path="by-property/(?P<property_id>[0-9]+)")
    def by_property(self, request, property_id=None):
        config, _ = PropertyAgentConfig.objects.get_or_create(property_id=property_id)
        if request.method == "GET":
            return Response(PropertyAgentConfigSerializer(config).data)
        serializer = PropertyAgentConfigSerializer(config, data=request.data, partial=request.method == "PATCH")
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PropertyGroupViewSet(viewsets.ModelViewSet):
    serializer_class = PropertyGroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PropertyGroup.objects.prefetch_related("properties")
