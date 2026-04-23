from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .agent_assist_views import AgentAssistChatView, AgentAssistRagStatusView
from .monitor_views import (
    AgentHealthCheckView,
    AgentMonitorDashboardView,
    AgentTokenLogView,
    MaintenanceChatLogView,
    ProgressiveTestView,
)
from .views import (
    AgentInvoiceApprovalView,
    AgentQuestionViewSet,
    JobDispatchListView,
    MaintenanceRequestViewSet,
    MaintenanceSkillViewSet,
    SupplierQuoteDeclineView,
    SupplierQuoteView,
    SupplierViewSet,
)
from .supplier_views import (
    SupplierCalendarView,
    SupplierDashboardView,
    SupplierDocumentsView,
    SupplierInvoiceView,
    SupplierJobAcceptView,
    SupplierJobDeclineView,
    SupplierJobDetailView,
    SupplierJobQuoteView,
    SupplierJobsView,
    SupplierJobStatusUpdateView,
    SupplierPaymentHistoryView,
    SupplierProfileView,
)

router = DefaultRouter()
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("agent-questions", AgentQuestionViewSet, basename="agent-question")
router.register("skills", MaintenanceSkillViewSet, basename="skill")
router.register("", MaintenanceRequestViewSet, basename="maintenance")

supplier_portal_urls = [
    path("dashboard/", SupplierDashboardView.as_view(), name="supplier-portal-dashboard"),
    path("jobs/", SupplierJobsView.as_view(), name="supplier-portal-jobs"),
    path("jobs/<int:pk>/", SupplierJobDetailView.as_view(), name="supplier-portal-job-detail"),
    path("jobs/<int:pk>/quote/", SupplierJobQuoteView.as_view(), name="supplier-portal-quote"),
    path("jobs/<int:pk>/decline/", SupplierJobDeclineView.as_view(), name="supplier-portal-decline"),
    path("jobs/<int:pk>/accept/", SupplierJobAcceptView.as_view(), name="supplier-portal-accept"),
    path("jobs/<int:pk>/status/", SupplierJobStatusUpdateView.as_view(), name="supplier-portal-status-update"),
    path("jobs/<int:pk>/invoice/", SupplierInvoiceView.as_view(), name="supplier-portal-invoice"),
    path("payments/", SupplierPaymentHistoryView.as_view(), name="supplier-portal-payments"),
    path("profile/", SupplierProfileView.as_view(), name="supplier-portal-profile"),
    path("documents/", SupplierDocumentsView.as_view(), name="supplier-portal-documents"),
    path("calendar/", SupplierCalendarView.as_view(), name="supplier-portal-calendar"),
]

urlpatterns = [
    path("agent-assist/chat/", AgentAssistChatView.as_view(), name="agent-assist-chat"),
    path(
        "agent-assist/rag-status/",
        AgentAssistRagStatusView.as_view(),
        name="agent-assist-rag-status",
    ),
    # Agent Monitor endpoints
    path("monitor/dashboard/", AgentMonitorDashboardView.as_view(), name="agent-monitor-dashboard"),
    path("monitor/token-logs/", AgentTokenLogView.as_view(), name="agent-monitor-tokens"),
    path("monitor/health/", AgentHealthCheckView.as_view(), name="agent-monitor-health"),
    path("monitor/tests/", ProgressiveTestView.as_view(), name="agent-monitor-tests"),
    path("monitor/chat-log/", MaintenanceChatLogView.as_view(), name="agent-monitor-chat-log"),
    # Supplier portal (authenticated supplier users)
    path("supplier/", include(supplier_portal_urls)),
    # Token-based quote pages (no auth)
    path("quotes/<uuid:token>/", SupplierQuoteView.as_view(), name="supplier-quote"),
    path("quotes/<uuid:token>/decline/", SupplierQuoteDeclineView.as_view(), name="supplier-quote-decline"),
    # Dispatch overview
    path("dispatches/", JobDispatchListView.as_view(), name="dispatch-list"),
    # Agent invoice approval
    path("<int:request_pk>/invoice/", AgentInvoiceApprovalView.as_view(), name="agent-invoice"),
    # Router routes
    path("", include(router.urls)),
]
