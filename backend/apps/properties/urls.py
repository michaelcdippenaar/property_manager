from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PropertyGroupViewSet, PropertyViewSet, UnitViewSet

router = DefaultRouter()
router.register("groups", PropertyGroupViewSet, basename="property-group")
router.register("units", UnitViewSet, basename="unit")
router.register("", PropertyViewSet, basename="property")

urlpatterns = [path("", include(router.urls))]
