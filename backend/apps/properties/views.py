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
from apps.accounts.scoping import AgencyScopedQuerysetMixin, AgencyStampedCreateMixin
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .access import get_accessible_property_ids
from .models import (
    BankAccount, ComplianceCertificate, InsurancePolicy, Landlord, LandlordDocument,
    Property, PropertyAgentAssignment, PropertyAgentConfig, PropertyDocument,
    PropertyGroup, PropertyOwnership, PropertyPhoto, PropertyValuation, Room, Unit, UnitInfo,
)
from .serializers import (
    BankAccountSerializer, ComplianceCertificateSerializer, InsurancePolicySerializer,
    LandlordDocumentSerializer, LandlordSerializer, PropertyAgentAssignmentSerializer,
    PropertyAgentConfigSerializer, PropertyDocumentSerializer, PropertyGroupSerializer,
    PropertyOwnershipSerializer, PropertyPhotoSerializer, PropertySerializer,
    PropertyValuationSerializer, RoomSerializer, UnitInfoSerializer, UnitSerializer,
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


class PropertyViewSet(AgencyScopedQuerysetMixin, AgencyStampedCreateMixin, viewsets.ModelViewSet):
    queryset = Property.objects.all()
    serializer_class = PropertySerializer
    permission_classes = [IsAgentOrAdmin]

    def get_queryset(self):
        qs = super().get_queryset()  # mixin applies agency_id filter
        prop_ids = get_accessible_property_ids(self.request.user)
        qs = qs.filter(pk__in=prop_ids)
        if self.request.query_params.get("unlinked") in ("1", "true", "yes"):
            qs = qs.exclude(ownerships__is_current=True)
        return qs

    @action(
        detail=True, methods=["get", "post", "delete", "patch"], url_path="photos(?:/(?P<photo_id>[0-9]+))?",
        parser_classes=[parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser],
    )
    def photos(self, request, pk=None, photo_id=None):
        prop = self.get_object()

        if request.method == "PATCH":
            # Bulk reorder: [{"id": 1, "position": 0}, {"id": 2, "position": 1}, ...]
            for item in request.data:
                PropertyPhoto.objects.filter(pk=item["id"], property=prop).update(position=item["position"])
            qs = prop.photos.all()
            unit_id = request.query_params.get("unit")
            if unit_id:
                qs = qs.filter(unit_id=unit_id)
            return Response(PropertyPhotoSerializer(qs, many=True, context={"request": request}).data)

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


class UnitViewSet(AgencyScopedQuerysetMixin, AgencyStampedCreateMixin, viewsets.ModelViewSet):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    permission_classes = [IsAgentOrAdmin]
    filterset_fields = ["property", "status"]

    def get_queryset(self):
        qs = super().get_queryset()
        prop_ids = get_accessible_property_ids(self.request.user)
        return qs.filter(property_id__in=prop_ids).select_related("property")


class RoomViewSet(AgencyScopedQuerysetMixin, AgencyStampedCreateMixin, viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [IsAgentOrAdmin]
    filterset_fields = ["unit"]

    def get_queryset(self):
        qs = super().get_queryset()
        prop_ids = get_accessible_property_ids(self.request.user)
        return qs.filter(unit__property_id__in=prop_ids).select_related("unit")


class UnitInfoViewSet(AgencyScopedQuerysetMixin, AgencyStampedCreateMixin, viewsets.ModelViewSet):
    queryset = UnitInfo.objects.all()
    serializer_class = UnitInfoSerializer
    permission_classes = [IsAgentOrAdmin]
    filterset_fields = ["property", "unit"]

    def get_queryset(self):
        qs = super().get_queryset()
        prop_ids = get_accessible_property_ids(self.request.user)
        return qs.filter(property_id__in=prop_ids).select_related("property", "unit")


class PropertyAgentConfigViewSet(AgencyScopedQuerysetMixin, AgencyStampedCreateMixin, viewsets.ModelViewSet):
    queryset = PropertyAgentConfig.objects.all()
    serializer_class = PropertyAgentConfigSerializer
    permission_classes = [IsAgentOrAdmin]
    filterset_fields = ["property"]

    def get_queryset(self):
        qs = super().get_queryset()
        prop_ids = get_accessible_property_ids(self.request.user)
        return qs.filter(property_id__in=prop_ids).select_related("property")

    @action(detail=False, methods=["get", "put", "patch"], url_path="by-property/(?P<property_id>[0-9]+)")
    def by_property(self, request, property_id=None):
        config, _ = PropertyAgentConfig.objects.get_or_create(property_id=property_id)
        if request.method == "GET":
            return Response(PropertyAgentConfigSerializer(config).data)
        serializer = PropertyAgentConfigSerializer(config, data=request.data, partial=request.method == "PATCH")
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PropertyOwnershipViewSet(AgencyScopedQuerysetMixin, AgencyStampedCreateMixin, viewsets.ModelViewSet):
    queryset = PropertyOwnership.objects.all()
    serializer_class = PropertyOwnershipSerializer
    permission_classes = [IsAgentOrAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        prop_ids = get_accessible_property_ids(self.request.user)
        qs = qs.filter(property_id__in=prop_ids).select_related("property")
        property_id = self.request.query_params.get("property")
        if property_id:
            qs = qs.filter(property_id=property_id)
        return qs

    @action(detail=False, methods=["get"], url_path="current/(?P<property_id>[0-9]+)")
    def current(self, request, property_id=None):
        ownership = get_object_or_404(PropertyOwnership, property_id=property_id, is_current=True)
        return Response(PropertyOwnershipSerializer(ownership).data)


class LandlordViewSet(AgencyScopedQuerysetMixin, AgencyStampedCreateMixin, viewsets.ModelViewSet):
    queryset = Landlord.objects.all()
    serializer_class = LandlordSerializer
    permission_classes = [IsAgentOrAdmin]

    def get_queryset(self):
        base = super().get_queryset()
        # `base` is already agency-scoped by AgencyScopedQuerysetMixin for
        # non-admin users; admin sees the full table. Within that scope we
        # show landlords that EITHER (a) have an ownership linked to a
        # property the user can access, OR (b) have no ownerships yet —
        # i.e. just-created, not yet attached to a property.
        #
        # The (b) branch was previously gated to admin only; on a non-admin
        # agency_admin account a brand-new landlord would 404 on its detail
        # fetch the instant after create, because `ownerships` was empty
        # and the property-id filter rejected it. Reproduced during the
        # first-run E2E test on a freshly-registered agency. The multi-
        # tenant agency scope already isolates the orphan, so unifying the
        # admin + non-admin branches is safe.
        prop_ids = get_accessible_property_ids(self.request.user)
        qs = base.filter(
            Q(ownerships__property_id__in=prop_ids) | Q(ownerships__isnull=True)
        ).distinct()
        qs = qs.prefetch_related('bank_accounts', 'ownerships__property')
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


class BankAccountViewSet(AgencyScopedQuerysetMixin, AgencyStampedCreateMixin, viewsets.ModelViewSet):
    queryset = BankAccount.objects.all()
    serializer_class = BankAccountSerializer
    permission_classes = [IsAgentOrAdmin]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_queryset(self):
        base = super().get_queryset()
        prop_ids = get_accessible_property_ids(self.request.user)
        qs = base.filter(
            landlord__ownerships__property_id__in=prop_ids
        ).distinct().select_related('landlord')
        landlord_id = self.request.query_params.get('landlord')
        if landlord_id:
            qs = qs.filter(landlord_id=landlord_id)
        return qs

    def get_serializer_context(self):
        return {**super().get_serializer_context(), 'request': self.request}

    @action(detail=True, methods=['post'], url_path='upload-confirmation',
            parser_classes=[parsers.MultiPartParser, parsers.FormParser])
    def upload_confirmation(self, request, pk=None):
        ba = self.get_object()
        f = request.FILES.get('file')
        if not f:
            return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)
        if ba.confirmation_letter:
            ba.confirmation_letter.delete(save=False)
        ba.confirmation_letter = f
        ba.save(update_fields=['confirmation_letter'])
        return Response(BankAccountSerializer(ba, context={'request': request}).data)

    @action(detail=True, methods=['delete'], url_path='remove-confirmation')
    def remove_confirmation(self, request, pk=None):
        ba = self.get_object()
        if ba.confirmation_letter:
            ba.confirmation_letter.delete(save=False)
        ba.confirmation_letter = None
        ba.save(update_fields=['confirmation_letter'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class PropertyGroupViewSet(AgencyScopedQuerysetMixin, AgencyStampedCreateMixin, viewsets.ModelViewSet):
    queryset = PropertyGroup.objects.all()
    serializer_class = PropertyGroupSerializer
    permission_classes = [IsAgentOrAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        prop_ids = get_accessible_property_ids(self.request.user)
        return qs.filter(
            properties__id__in=prop_ids
        ).distinct().prefetch_related("properties")


class ComplianceCertificateViewSet(AgencyScopedQuerysetMixin, AgencyStampedCreateMixin, viewsets.ModelViewSet):
    queryset = ComplianceCertificate.objects.all()
    serializer_class = ComplianceCertificateSerializer
    permission_classes = [IsAgentOrAdmin]
    filterset_fields = ["property", "cert_type"]

    def get_queryset(self):
        qs = super().get_queryset()
        prop_ids = get_accessible_property_ids(self.request.user)
        return qs.filter(
            property_id__in=prop_ids
        ).select_related("property").order_by("-issued_date")


class InsurancePolicyViewSet(AgencyScopedQuerysetMixin, AgencyStampedCreateMixin, viewsets.ModelViewSet):
    queryset = InsurancePolicy.objects.all()
    serializer_class = InsurancePolicySerializer
    permission_classes = [IsAgentOrAdmin]
    filterset_fields = ["property", "is_active"]

    def get_queryset(self):
        qs = super().get_queryset()
        prop_ids = get_accessible_property_ids(self.request.user)
        return qs.filter(
            property_id__in=prop_ids
        ).select_related("property").order_by("-start_date")


class PropertyValuationViewSet(AgencyScopedQuerysetMixin, AgencyStampedCreateMixin, viewsets.ModelViewSet):
    queryset = PropertyValuation.objects.all()
    serializer_class = PropertyValuationSerializer
    permission_classes = [IsAgentOrAdmin]
    filterset_fields = ["property", "valuation_type"]

    def get_queryset(self):
        qs = super().get_queryset()
        prop_ids = get_accessible_property_ids(self.request.user)
        return qs.filter(
            property_id__in=prop_ids
        ).select_related("property").order_by("-valuation_date")


class PropertyAgentAssignmentViewSet(AgencyScopedQuerysetMixin, AgencyStampedCreateMixin, viewsets.ModelViewSet):
    """
    CRUD for property-agent assignments.
    Filterable by ?property=ID or ?agent=ID.
    """
    queryset = PropertyAgentAssignment.objects.all()
    serializer_class = PropertyAgentAssignmentSerializer
    permission_classes = [IsAgentOrAdmin]

    def get_queryset(self):
        base = super().get_queryset()
        prop_ids = get_accessible_property_ids(self.request.user)
        qs = base.filter(
            property_id__in=prop_ids,
        ).select_related("property", "agent", "assigned_by").order_by("-created_at")

        prop_filter = self.request.query_params.get("property")
        if prop_filter:
            qs = qs.filter(property_id=prop_filter)
        agent_filter = self.request.query_params.get("agent")
        if agent_filter:
            qs = qs.filter(agent_id=agent_filter)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def perform_create(self, serializer):
        # Stamp agency via the mixin (which calls serializer.save(agency_id=...))
        # then patch in `assigned_by` on the resulting instance.
        super().perform_create(serializer)
        instance = serializer.instance
        if instance and instance.assigned_by_id != self.request.user.id:
            instance.assigned_by = self.request.user
            instance.save(update_fields=["assigned_by"])
