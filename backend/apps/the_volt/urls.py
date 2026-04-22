from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.the_volt.owners.views import VaultOwnerMeView
from apps.the_volt.entities.views import VaultEntityViewSet, EntityRelationshipViewSet, RelationshipTypeCatalogueViewSet
from apps.the_volt.documents.views import VaultDocumentViewSet
from apps.the_volt.schemas.views import EntitySchemaViewSet
from apps.the_volt.gateway.views import (
    DataRequestCreateView,
    DataRequestListView,
    DataRequestApproveView,
    DataRequestDenyView,
    DataCheckoutStatusView,
    DataCheckoutView,
    DataRequestApprovalInfoView,
    DataRequestApprovePublicView,
)

router = DefaultRouter()
router.register("entities", VaultEntityViewSet, basename="vault-entity")
router.register("relationships", EntityRelationshipViewSet, basename="vault-relationship")
router.register("relationship-types", RelationshipTypeCatalogueViewSet, basename="vault-relationship-type")
router.register("documents", VaultDocumentViewSet, basename="vault-document")
router.register("schemas", EntitySchemaViewSet, basename="vault-schema")

urlpatterns = [
    # Owner vault
    path("vault/me/", VaultOwnerMeView.as_view(), name="vault-me"),

    # Gateway — subscriber-facing (X-Volt-API-Key auth)
    path("gateway/request/", DataRequestCreateView.as_view(), name="volt-gateway-request"),
    path("gateway/checkout/", DataCheckoutView.as_view(), name="volt-gateway-checkout"),
    path("gateway/requests/<uuid:token>/status/", DataCheckoutStatusView.as_view(), name="volt-request-status"),

    # Gateway — owner-facing (JWT auth)
    path("gateway/requests/", DataRequestListView.as_view(), name="volt-requests-list"),
    path("gateway/requests/<uuid:token>/approve/", DataRequestApproveView.as_view(), name="volt-request-approve"),
    path("gateway/requests/<uuid:token>/deny/", DataRequestDenyView.as_view(), name="volt-request-deny"),

    # Gateway — public (UUID token + OTP auth, no JWT required)
    path("gateway/requests/<uuid:token>/approval-info/", DataRequestApprovalInfoView.as_view(), name="volt-approval-info"),
    path("gateway/requests/<uuid:token>/approve-public/", DataRequestApprovePublicView.as_view(), name="volt-approve-public"),

    path("", include(router.urls)),
]
