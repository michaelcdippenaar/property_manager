from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    JobDispatchListView,
    MaintenanceRequestViewSet,
    SupplierQuoteDeclineView,
    SupplierQuoteView,
    SupplierViewSet,
)
from .supplier_views import (
    SupplierCalendarView,
    SupplierDashboardView,
    SupplierDocumentsView,
    SupplierJobDeclineView,
    SupplierJobDetailView,
    SupplierJobQuoteView,
    SupplierJobsView,
    SupplierProfileView,
)

router = DefaultRouter()
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("", MaintenanceRequestViewSet, basename="maintenance")

supplier_portal_urls = [
    path("dashboard/", SupplierDashboardView.as_view(), name="supplier-portal-dashboard"),
    path("jobs/", SupplierJobsView.as_view(), name="supplier-portal-jobs"),
    path("jobs/<int:pk>/", SupplierJobDetailView.as_view(), name="supplier-portal-job-detail"),
    path("jobs/<int:pk>/quote/", SupplierJobQuoteView.as_view(), name="supplier-portal-quote"),
    path("jobs/<int:pk>/decline/", SupplierJobDeclineView.as_view(), name="supplier-portal-decline"),
    path("profile/", SupplierProfileView.as_view(), name="supplier-portal-profile"),
    path("documents/", SupplierDocumentsView.as_view(), name="supplier-portal-documents"),
    path("calendar/", SupplierCalendarView.as_view(), name="supplier-portal-calendar"),
]

urlpatterns = [
    # Supplier portal (authenticated supplier users)
    path("supplier/", include(supplier_portal_urls)),
    # Token-based quote pages (no auth)
    path("quotes/<uuid:token>/", SupplierQuoteView.as_view(), name="supplier-quote"),
    path("quotes/<uuid:token>/decline/", SupplierQuoteDeclineView.as_view(), name="supplier-quote-decline"),
    # Dispatch overview
    path("dispatches/", JobDispatchListView.as_view(), name="dispatch-list"),
    # Router routes
    path("", include(router.urls)),
]
