from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BankAccountViewSet, ComplianceCertificateViewSet, InsurancePolicyViewSet,
    LandlordViewSet, PropertyAgentAssignmentViewSet, PropertyAgentConfigViewSet,
    PropertyGroupViewSet, PropertyOwnershipViewSet, PropertyValuationViewSet,
    PropertyViewSet, RoomViewSet, UnitInfoViewSet, UnitViewSet,
)
from .owner_views import OwnerActivityFeedView, OwnerDashboardView, OwnerPropertiesView
from .classify_view import LandlordClassifyView, LandlordClassifyRegistrationView
from .chat_view import LandlordChatView
from .municipal_bill_view import ParseMunicipalBillView
from .mandate_parse_view import ParseMandateDocumentView
from .mandate_views import RentalMandateViewSet
from .viewing_views import PropertyViewingViewSet

router = DefaultRouter()
router.register("landlords", LandlordViewSet, basename="landlord")
router.register("bank-accounts", BankAccountViewSet, basename="bank-account")
router.register("groups", PropertyGroupViewSet, basename="property-group")
router.register("units", UnitViewSet, basename="unit")
router.register("rooms", RoomViewSet, basename="room")
router.register("unit-info", UnitInfoViewSet, basename="unit-info")
router.register("ownerships", PropertyOwnershipViewSet, basename="ownership")
router.register("agent-config", PropertyAgentConfigViewSet, basename="agent-config")
router.register("compliance-certs", ComplianceCertificateViewSet, basename="compliance-cert")
router.register("insurance-policies", InsurancePolicyViewSet, basename="insurance-policy")
router.register("valuations", PropertyValuationViewSet, basename="property-valuation")
router.register("mandates", RentalMandateViewSet, basename="rental-mandate")
router.register("viewings", PropertyViewingViewSet, basename="property-viewing")
router.register("agent-assignments", PropertyAgentAssignmentViewSet, basename="agent-assignment")
router.register("", PropertyViewSet, basename="property")

owner_urls = [
    path("dashboard/", OwnerDashboardView.as_view(), name="owner-dashboard"),
    path("activity/", OwnerActivityFeedView.as_view(), name="owner-activity"),
    path("properties/", OwnerPropertiesView.as_view(), name="owner-properties"),
]

urlpatterns = [
    path("owner/", include(owner_urls)),
    path("landlords/<int:pk>/classify/", LandlordClassifyView.as_view(), name="landlord-classify"),
    path("landlords/<int:pk>/classify-registration/", LandlordClassifyRegistrationView.as_view(), name="landlord-classify-registration"),
    path("landlords/<int:pk>/chat/", LandlordChatView.as_view(), name="landlord-chat"),
    path("parse-municipal-bill/", ParseMunicipalBillView.as_view(), name="parse-municipal-bill"),
    path(
        "<int:property_id>/mandates/parse-document/",
        ParseMandateDocumentView.as_view(),
        name="property-mandate-parse-document",
    ),
    path("", include(router.urls)),
]
