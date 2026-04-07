from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BankAccountViewSet, ComplianceCertificateViewSet, InsurancePolicyViewSet,
    LandlordViewSet, PropertyAgentConfigViewSet, PropertyGroupViewSet,
    PropertyOwnershipViewSet, PropertyValuationViewSet, PropertyViewSet,
    UnitInfoViewSet, UnitViewSet,
)
from .owner_views import OwnerDashboardView, OwnerPropertiesView
from .classify_view import LandlordClassifyView, LandlordClassifyRegistrationView
from .municipal_bill_view import ParseMunicipalBillView
from .mandate_views import RentalMandateViewSet

router = DefaultRouter()
router.register("landlords", LandlordViewSet, basename="landlord")
router.register("bank-accounts", BankAccountViewSet, basename="bank-account")
router.register("groups", PropertyGroupViewSet, basename="property-group")
router.register("units", UnitViewSet, basename="unit")
router.register("unit-info", UnitInfoViewSet, basename="unit-info")
router.register("ownerships", PropertyOwnershipViewSet, basename="ownership")
router.register("agent-config", PropertyAgentConfigViewSet, basename="agent-config")
router.register("compliance-certs", ComplianceCertificateViewSet, basename="compliance-cert")
router.register("insurance-policies", InsurancePolicyViewSet, basename="insurance-policy")
router.register("valuations", PropertyValuationViewSet, basename="property-valuation")
router.register("mandates", RentalMandateViewSet, basename="rental-mandate")
router.register("", PropertyViewSet, basename="property")

owner_urls = [
    path("dashboard/", OwnerDashboardView.as_view(), name="owner-dashboard"),
    path("properties/", OwnerPropertiesView.as_view(), name="owner-properties"),
]

urlpatterns = [
    path("owner/", include(owner_urls)),
    path("landlords/<int:pk>/classify/", LandlordClassifyView.as_view(), name="landlord-classify"),
    path("landlords/<int:pk>/classify-registration/", LandlordClassifyRegistrationView.as_view(), name="landlord-classify-registration"),
    path("parse-municipal-bill/", ParseMunicipalBillView.as_view(), name="parse-municipal-bill"),
    path("", include(router.urls)),
]
