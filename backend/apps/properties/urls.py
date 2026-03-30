from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PropertyAgentConfigViewSet, PropertyGroupViewSet, PropertyOwnershipViewSet, PropertyViewSet, UnitInfoViewSet, UnitViewSet
from .owner_views import OwnerDashboardView, OwnerPropertiesView

router = DefaultRouter()
router.register("groups", PropertyGroupViewSet, basename="property-group")
router.register("units", UnitViewSet, basename="unit")
router.register("unit-info", UnitInfoViewSet, basename="unit-info")
router.register("ownerships", PropertyOwnershipViewSet, basename="ownership")
router.register("agent-config", PropertyAgentConfigViewSet, basename="agent-config")
router.register("", PropertyViewSet, basename="property")

owner_urls = [
    path("dashboard/", OwnerDashboardView.as_view(), name="owner-dashboard"),
    path("properties/", OwnerPropertiesView.as_view(), name="owner-properties"),
]

urlpatterns = [
    path("owner/", include(owner_urls)),
    path("", include(router.urls)),
]
