from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework import generics, permissions
from .views import LeaseViewSet, LeaseCalendarAPIView, InventoryTemplateViewSet
from .parse_view import ParseLeaseDocumentView
from .import_view import ImportLeaseView
from .template_views import LeaseTemplateListView, LeaseTemplateDetailView, GenerateLeaseDocumentView, LeaseTemplatePreviewView, LeaseTemplateAIChatView, ExportTemplatePDFView, PdfRenderJobListView, PdfRenderJobRetryView
from .builder_views import LeaseBuilderSessionCreateView, LeaseBuilderChatView, LeaseBuilderFinalizeView, LeaseBuilderDraftListView, LeaseBuilderDraftSaveView
from .clause_views import ReusableClauseListCreateView, ReusableClauseDestroyView, ReusableClauseUseView, GenerateClauseView, ExtractClausesView
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
    path("calendar/", LeaseCalendarAPIView.as_view(), name="lease-calendar"),
    path("parse-document/", ParseLeaseDocumentView.as_view(), name="lease-parse-document"),
    path("import/", ImportLeaseView.as_view(), name="lease-import"),
    # Lease templates + document generation
    path("templates/", LeaseTemplateListView.as_view(), name="lease-templates"),
    path("templates/<int:pk>/", LeaseTemplateDetailView.as_view(), name="lease-template-detail"),
    path("templates/<int:pk>/preview/", LeaseTemplatePreviewView.as_view(), name="lease-template-preview"),
    path("templates/<int:pk>/ai-chat/", LeaseTemplateAIChatView.as_view(), name="lease-template-ai-chat"),
    path("templates/<int:pk>/export.pdf/", ExportTemplatePDFView.as_view(), name="lease-template-export-pdf"),
    path("generate/", GenerateLeaseDocumentView.as_view(), name="lease-generate"),
    # PDF render job queue (async retry for Gotenberg failures)
    path("render-jobs/", PdfRenderJobListView.as_view(), name="pdf-render-jobs"),
    path("render-jobs/<int:pk>/retry/", PdfRenderJobRetryView.as_view(), name="pdf-render-job-retry"),
    # Lease builder drafts
    path("builder/drafts/", LeaseBuilderDraftListView.as_view(), name="builder-draft-list"),
    path("builder/drafts/new/", LeaseBuilderDraftSaveView.as_view(), name="builder-draft-create"),
    path("builder/drafts/<int:pk>/", LeaseBuilderDraftSaveView.as_view(), name="builder-draft-save"),
    # AI conversational lease builder
    path("builder/sessions/", LeaseBuilderSessionCreateView.as_view(), name="builder-session-create"),
    path("builder/sessions/<int:pk>/message/", LeaseBuilderChatView.as_view(), name="builder-session-message"),
    path("builder/sessions/<int:pk>/finalize/", LeaseBuilderFinalizeView.as_view(), name="builder-session-finalize"),
    # Reusable clause library
    path("clauses/", ReusableClauseListCreateView.as_view(), name="clauses-list"),
    path("clauses/generate/", GenerateClauseView.as_view(), name="clauses-generate"),
    path("clauses/extract/", ExtractClausesView.as_view(), name="clauses-extract"),
    path("clauses/<int:pk>/", ReusableClauseDestroyView.as_view(), name="clause-destroy"),
    path("clauses/<int:pk>/use/", ReusableClauseUseView.as_view(), name="clause-use"),
    # Misc lists
    # Inventory templates
    path("inventory-templates/", InventoryTemplateViewSet.as_view({"get": "list", "post": "create"}), name="inventory-templates"),
    path("inventory-templates/<int:pk>/", InventoryTemplateViewSet.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}), name="inventory-template-detail"),
    # Misc lists
    path("co-tenants/", LeaseTenantList.as_view(), name="lease-co-tenants"),
    path("occupants/", LeaseOccupantList.as_view(), name="lease-occupants"),
    path("guarantors/", LeaseGuarantorList.as_view(), name="lease-guarantors"),
    path("", include(router.urls)),
]
