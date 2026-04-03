from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import IsAgentOrAdmin
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .access import get_accessible_property_ids
from .models import BankAccount, Landlord, Property, PropertyAgentConfig, PropertyGroup, PropertyOwnership, Unit, UnitInfo
from .serializers import (
    BankAccountSerializer, LandlordSerializer,
    PropertyAgentConfigSerializer, PropertyGroupSerializer,
    PropertyOwnershipSerializer, PropertySerializer, UnitInfoSerializer, UnitSerializer,
)


class PropertyViewSet(viewsets.ModelViewSet):
    serializer_class = PropertySerializer
    permission_classes = [IsAgentOrAdmin]

    def get_queryset(self):
        prop_ids = get_accessible_property_ids(self.request.user)
        return Property.objects.filter(pk__in=prop_ids)


class UnitViewSet(viewsets.ModelViewSet):
    serializer_class = UnitSerializer
    permission_classes = [IsAgentOrAdmin]
    filterset_fields = ["property", "status"]

    def get_queryset(self):
        prop_ids = get_accessible_property_ids(self.request.user)
        return Unit.objects.filter(property_id__in=prop_ids).select_related("property")


class UnitInfoViewSet(viewsets.ModelViewSet):
    serializer_class = UnitInfoSerializer
    permission_classes = [IsAgentOrAdmin]
    filterset_fields = ["property", "unit"]

    def get_queryset(self):
        prop_ids = get_accessible_property_ids(self.request.user)
        return UnitInfo.objects.filter(property_id__in=prop_ids).select_related("property", "unit")


class PropertyAgentConfigViewSet(viewsets.ModelViewSet):
    serializer_class = PropertyAgentConfigSerializer
    permission_classes = [IsAgentOrAdmin]
    filterset_fields = ["property"]

    def get_queryset(self):
        prop_ids = get_accessible_property_ids(self.request.user)
        return PropertyAgentConfig.objects.filter(property_id__in=prop_ids).select_related("property")

    @action(detail=False, methods=["get", "put", "patch"], url_path="by-property/(?P<property_id>[0-9]+)")
    def by_property(self, request, property_id=None):
        config, _ = PropertyAgentConfig.objects.get_or_create(property_id=property_id)
        if request.method == "GET":
            return Response(PropertyAgentConfigSerializer(config).data)
        serializer = PropertyAgentConfigSerializer(config, data=request.data, partial=request.method == "PATCH")
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PropertyOwnershipViewSet(viewsets.ModelViewSet):
    serializer_class = PropertyOwnershipSerializer
    permission_classes = [IsAgentOrAdmin]

    def get_queryset(self):
        prop_ids = get_accessible_property_ids(self.request.user)
        qs = PropertyOwnership.objects.filter(property_id__in=prop_ids).select_related("property")
        property_id = self.request.query_params.get("property")
        if property_id:
            qs = qs.filter(property_id=property_id)
        return qs

    @action(detail=False, methods=["get"], url_path="current/(?P<property_id>[0-9]+)")
    def current(self, request, property_id=None):
        ownership = get_object_or_404(PropertyOwnership, property_id=property_id, is_current=True)
        return Response(PropertyOwnershipSerializer(ownership).data)


class LandlordViewSet(viewsets.ModelViewSet):
    serializer_class = LandlordSerializer
    permission_classes = [IsAgentOrAdmin]

    def get_queryset(self):
        prop_ids = get_accessible_property_ids(self.request.user)
        qs = Landlord.objects.filter(
            ownerships__property_id__in=prop_ids
        ).distinct().prefetch_related('bank_accounts', 'ownerships__property')
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(email__icontains=search))
        return qs


class BankAccountViewSet(viewsets.ModelViewSet):
    serializer_class = BankAccountSerializer
    permission_classes = [IsAgentOrAdmin]

    def get_queryset(self):
        prop_ids = get_accessible_property_ids(self.request.user)
        qs = BankAccount.objects.filter(
            landlord__ownerships__property_id__in=prop_ids
        ).distinct().select_related('landlord')
        landlord_id = self.request.query_params.get('landlord')
        if landlord_id:
            qs = qs.filter(landlord_id=landlord_id)
        return qs


class PropertyGroupViewSet(viewsets.ModelViewSet):
    serializer_class = PropertyGroupSerializer
    permission_classes = [IsAgentOrAdmin]

    def get_queryset(self):
        prop_ids = get_accessible_property_ids(self.request.user)
        return PropertyGroup.objects.filter(
            properties__id__in=prop_ids
        ).distinct().prefetch_related("properties")
