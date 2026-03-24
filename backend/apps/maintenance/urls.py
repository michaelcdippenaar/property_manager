from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MaintenanceRequestViewSet, SupplierViewSet

router = DefaultRouter()
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("", MaintenanceRequestViewSet, basename="maintenance")

urlpatterns = [path("", include(router.urls))]
