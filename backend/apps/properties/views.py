import io
import os
from PIL import Image as PilImage

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

from rest_framework import viewsets, parsers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import IsAgentOrAdmin
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .access import get_accessible_property_ids
from .models import (
    BankAccount, ComplianceCertificate, InsurancePolicy, Landlord, LandlordDocument,
    Property, PropertyAgentConfig, PropertyDocument, PropertyGroup, PropertyOwnership,
    PropertyPhoto, PropertyValuation, Unit, UnitInfo,
)
from .serializers import (
    BankAccountSerializer, ComplianceCertificateSerializer, InsurancePolicySerializer,
    LandlordDocumentSerializer, LandlordSerializer, PropertyAgentConfigSerializer,
    PropertyDocumentSerializer, PropertyGroupSerializer, PropertyOwnershipSerializer,
    PropertyPhotoSerializer, PropertySerializer, PropertyValuationSerializer,
    UnitInfoSerializer, UnitSerializer,
)


def _make_thumbnail(original_file, size=(400, 400)):
    """Return a Django ContentFile containing a JPEG thumbnail."""
    from django.core.files.base import ContentFile
    img = PilImage.open(original_file)
    img = img.convert("RGB")
    img.thumbnail(size, PilImage.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=72, optimize=True)
    buf.seek(0)
    return ContentFile(buf.read())


class PropertyViewSet(viewsets.ModelViewSet):
    serializer_class = PropertySerializer
    permission_classes = [IsAgentOrAdmin]

    def get_queryset(self):
        prop_ids = get_accessible_property_ids(self.request.user)
        qs = Property.objects.filter(pk__in=prop_ids)
        if self.request.query_params.get("unlinked") in ("1", "true", "yes"):
            qs = qs.exclude(ownerships__is_current=True)
        return qs

    @action(
        detail=True, methods=["get", "post", "delete"], url_path="photos(?:/(?P<photo_id>[0-9]+))?",
        parser_classes=[parsers.MultiPartParser, parsers.FormParser],
    )
    def photos(self, request, pk=None, photo_id=None):
        prop = self.get_object()

        if request.method == "DELETE":
            photo = get_object_or_404(PropertyPhoto, pk=photo_id, property=prop)
            photo.photo.delete(save=False)
            if photo.thumbnail:
                photo.thumbnail.delete(save=False)
            photo.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

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
        unit_id = request.data.get("unit") or None
        if unit_id and not prop.units.filter(pk=unit_id).exists():
            return Response({"detail": "Unit does not belong to this property."}, status=status.HTTP_400_BAD_REQUEST)
        created = []
        for f in files:
            photo = PropertyPhoto.objects.create(
                property=prop,
                unit_id=unit_id,
                photo=f,
                caption=request.data.get("caption", ""),
            )
            # Generate and save thumbnail
            try:
                f.seek(0)
                thumb_content = _make_thumbnail(f)
                base = os.path.splitext(os.path.basename(f.name))[0]
                photo.thumbnail.save(f"{base}_thumb.jpg", thumb_content, save=True)
            except Exception:
                pass  # thumbnail is optional — original still works
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
            Q(ownerships__property_id__in=prop_ids) | Q(ownerships__isnull=True)
        ).distinct().prefetch_related('bank_accounts', 'ownerships__property')
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(email__icontains=search))
        return qs

    @action(detail=True, methods=['post'], url_path='upload-document', parser_classes=[parsers.MultiPartParser])
    def upload_document(self, request, pk=None):
        landlord = self.get_object()
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)
        # Delete old file if exists
        if landlord.registration_document:
            landlord.registration_document.delete(save=False)
        landlord.registration_document = file
        landlord.registration_document_name = file.name
        landlord.save(update_fields=['registration_document', 'registration_document_name'])
        return Response({
            'registration_document': request.build_absolute_uri(landlord.registration_document.url),
            'registration_document_name': landlord.registration_document_name,
        })

    @action(detail=True, methods=['delete'], url_path='delete-document')
    def delete_document(self, request, pk=None):
        landlord = self.get_object()
        if landlord.registration_document:
            landlord.registration_document.delete(save=False)
        landlord.registration_document_name = ''
        landlord.save(update_fields=['registration_document', 'registration_document_name'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True, methods=['get', 'post'],
        url_path='fica-documents',
        parser_classes=[parsers.MultiPartParser, parsers.FormParser],
    )
    def fica_documents(self, request, pk=None):
        """List or upload FICA/CIPC supporting documents for this landlord."""
        landlord = self.get_object()
        if request.method == 'GET':
            docs = landlord.documents.all()
            return Response(LandlordDocumentSerializer(docs, many=True, context={'request': request}).data)

        files = request.FILES.getlist('files')
        if not files:
            return Response({'error': 'No files provided.'}, status=status.HTTP_400_BAD_REQUEST)
        created = []
        for f in files:
            doc = LandlordDocument.objects.create(landlord=landlord, file=f, filename=f.name)
            created.append(doc)
        return Response(
            LandlordDocumentSerializer(created, many=True, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['delete'], url_path=r'fica-documents/(?P<doc_id>[0-9]+)')
    def delete_fica_document(self, request, pk=None, doc_id=None):
        """Delete a single FICA/CIPC supporting document."""
        landlord = self.get_object()
        doc = get_object_or_404(LandlordDocument, pk=doc_id, landlord=landlord)
        doc.file.delete(save=False)
        doc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
