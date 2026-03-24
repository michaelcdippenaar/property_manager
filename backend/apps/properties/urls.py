from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PropertyViewSet, UnitViewSet

router = DefaultRouter()
router.register("", PropertyViewSet, basename="property")
router.register("units", UnitViewSet, basename="unit")

urlpatterns = [path("", include(router.urls))]
