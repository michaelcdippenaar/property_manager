from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    JobDispatchListView,
    MaintenanceRequestViewSet,
    SupplierQuoteDeclineView,
    SupplierQuoteView,
    SupplierViewSet,
)

router = DefaultRouter()
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("", MaintenanceRequestViewSet, basename="maintenance")

urlpatterns = [
    # Supplier-facing quote pages (token-based, no auth)
    path("quotes/<uuid:token>/", SupplierQuoteView.as_view(), name="supplier-quote"),
    path("quotes/<uuid:token>/decline/", SupplierQuoteDeclineView.as_view(), name="supplier-quote-decline"),
    # Dispatch overview
    path("dispatches/", JobDispatchListView.as_view(), name="dispatch-list"),
    # Router routes
    path("", include(router.urls)),
]
