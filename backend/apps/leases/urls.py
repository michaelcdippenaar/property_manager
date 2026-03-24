from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework import generics, permissions
from .views import LeaseViewSet
from .parse_view import ParseLeaseDocumentView
from .import_view import ImportLeaseView
from .template_views import LeaseTemplateListView, LeaseTemplateDetailView, GenerateLeaseDocumentView, LeaseTemplatePreviewView, LeaseTemplateAIChatView
from .builder_views import LeaseBuilderSessionCreateView, LeaseBuilderChatView, LeaseBuilderFinalizeView
from .models import LeaseTenant, LeaseOccupant, LeaseGuarantor
from .serializers import LeaseTenantSerializer, LeaseOccupantSerializer, LeaseGuarantorSerializer

router = DefaultRouter()
router.register("", LeaseViewSet, basename="lease")


class LeaseTenantList(generics.ListCreateAPIView):
    serializer_class = LeaseTenantSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = LeaseTenant.objects.select_related("person")


class LeaseOccupantList(generics.ListCreateAPIView):
    serializer_class = LeaseOccupantSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = LeaseOccupant.objects.select_related("person")


class LeaseGuarantorList(generics.ListCreateAPIView):
    serializer_class = LeaseGuarantorSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = LeaseGuarantor.objects.select_related("person")


urlpatterns = [
    path("parse-document/", ParseLeaseDocumentView.as_view(), name="lease-parse-document"),
    path("import/", ImportLeaseView.as_view(), name="lease-import"),
    # Lease templates + document generation
    path("templates/", LeaseTemplateListView.as_view(), name="lease-templates"),
    path("templates/<int:pk>/", LeaseTemplateDetailView.as_view(), name="lease-template-detail"),
    path("templates/<int:pk>/preview/", LeaseTemplatePreviewView.as_view(), name="lease-template-preview"),
    path("templates/<int:pk>/ai-chat/", LeaseTemplateAIChatView.as_view(), name="lease-template-ai-chat"),
    path("generate/", GenerateLeaseDocumentView.as_view(), name="lease-generate"),
    # AI conversational lease builder
    path("builder/sessions/", LeaseBuilderSessionCreateView.as_view(), name="builder-session-create"),
    path("builder/sessions/<int:pk>/message/", LeaseBuilderChatView.as_view(), name="builder-session-message"),
    path("builder/sessions/<int:pk>/finalize/", LeaseBuilderFinalizeView.as_view(), name="builder-session-finalize"),
    # Misc lists
    path("co-tenants/", LeaseTenantList.as_view(), name="lease-co-tenants"),
    path("occupants/", LeaseOccupantList.as_view(), name="lease-occupants"),
    path("guarantors/", LeaseGuarantorList.as_view(), name="lease-guarantors"),
    path("", include(router.urls)),
]
