from rest_framework import viewsets, parsers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import IsAgentOrAdmin
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .access import get_accessible_property_ids
from .models import (
    BankAccount, ComplianceCertificate, InsurancePolicy, Landlord, Property,
    PropertyAgentConfig, PropertyDocument, PropertyGroup, PropertyOwnership,
    PropertyPhoto, PropertyValuation, Unit, UnitInfo,
)
from .serializers import (
    BankAccountSerializer, ComplianceCertificateSerializer, InsurancePolicySerializer,
    LandlordSerializer, PropertyAgentConfigSerializer, PropertyDocumentSerializer,
    PropertyGroupSerializer, PropertyOwnershipSerializer, PropertyPhotoSerializer,
    PropertySerializer, PropertyValuationSerializer, UnitInfoSerializer, UnitSerializer,
)


class PropertyViewSet(viewsets.ModelViewSet):
    serializer_class = PropertySerializer
    permission_classes = [IsAgentOrAdmin]

    def get_queryset(self):
        prop_ids = get_accessible_property_ids(self.request.user)
        return Property.objects.filter(pk__in=prop_ids)

    @action(
        detail=True, methods=["get", "post"], url_path="photos",
        parser_classes=[parsers.MultiPartParser, parsers.FormParser],
    )
    def photos(self, request, pk=None):
        prop = self.get_object()
        if request.method == "GET":
            qs = prop.photos.all()
            unit_id = request.query_params.get("unit")
            if unit_id:
                qs = qs.filter(unit_id=unit_id)
            return Response(PropertyPhotoSerializer(qs, many=True, context={"request": request}).data)

        # POST — upload one or more photos
        files = request.FILES.getlist("photo")
        if not files:
            return Response({"detail": "No photo files provided."}, status=status.HTTP_400_BAD_REQUEST)
        unit_id = request.data.get("unit")
        created = []
        for f in files:
            photo = PropertyPhoto.objects.create(
                property=prop,
                unit_id=unit_id or None,
                photo=f,
                caption=request.data.get("caption", ""),
            )
            created.append(photo)
        return Response(
            PropertyPhotoSerializer(created, many=True, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True, methods=["get", "post", "delete"], url_path="documents(?:/(?P<doc_id>[0-9]+))?",
        parser_classes=[parsers.MultiPartParser, parsers.FormParser],
    )
    def documents(self, request, pk=None, doc_id=None):
        prop = self.get_object()

        if request.method == "DELETE":
            if not doc_id:
                return Response({"detail": "Document ID required."}, status=status.HTTP_400_BAD_REQUEST)
            doc = get_object_or_404(PropertyDocument, pk=doc_id, property=prop)
            doc.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        if request.method == "GET":
            qs = prop.documents.all()
            unit_id = request.query_params.get("unit")
            doc_type = request.query_params.get("doc_type")
            if unit_id:
                qs = qs.filter(Q(unit_id=unit_id) | Q(unit__isnull=True))
            if doc_type:
                qs = qs.filter(doc_type=doc_type)
            return Response(PropertyDocumentSerializer(qs, many=True, context={"request": request}).data)

        # POST — upload document
        file = request.FILES.get("document")
        if not file:
            return Response({"detail": "No document file provided."}, status=status.HTTP_400_BAD_REQUEST)
        doc = PropertyDocument.objects.create(
            property=prop,
            unit_id=request.data.get("unit") or None,
            document=file,
            doc_type=request.data.get("doc_type", "other"),
            name=request.data.get("name", ""),
            notes=request.data.get("notes", ""),
        )
        return Response(
            PropertyDocumentSerializer(doc, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


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


class ComplianceCertificateViewSet(viewsets.ModelViewSet):
    serializer_class = ComplianceCertificateSerializer
    permission_classes = [IsAgentOrAdmin]
    filterset_fields = ["property", "cert_type"]

    def get_queryset(self):
        prop_ids = get_accessible_property_ids(self.request.user)
        return ComplianceCertificate.objects.filter(
            property_id__in=prop_ids
        ).select_related("property").order_by("-issued_date")


class InsurancePolicyViewSet(viewsets.ModelViewSet):
    serializer_class = InsurancePolicySerializer
    permission_classes = [IsAgentOrAdmin]
    filterset_fields = ["property", "is_active"]

    def get_queryset(self):
        prop_ids = get_accessible_property_ids(self.request.user)
        return InsurancePolicy.objects.filter(
            property_id__in=prop_ids
        ).select_related("property").order_by("-start_date")


class PropertyValuationViewSet(viewsets.ModelViewSet):
    serializer_class = PropertyValuationSerializer
    permission_classes = [IsAgentOrAdmin]
    filterset_fields = ["property", "valuation_type"]

    def get_queryset(self):
        prop_ids = get_accessible_property_ids(self.request.user)
        return PropertyValuation.objects.filter(
            property_id__in=prop_ids
        ).select_related("property").order_by("-valuation_date")
