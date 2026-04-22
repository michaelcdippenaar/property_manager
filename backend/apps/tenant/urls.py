from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("tenants", views.TenantViewSet, basename="tenant")
router.register("assignments", views.TenantUnitAssignmentViewSet, basename="tenant-assignment")
router.register("onboarding", views.TenantOnboardingViewSet, basename="tenant-onboarding")

urlpatterns = [
    path("", include(router.urls)),
]
