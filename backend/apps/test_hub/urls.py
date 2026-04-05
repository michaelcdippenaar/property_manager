from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.test_hub.views import (
    TestRunRecordViewSet,
    TestRunStreamView,
    TestIssueViewSet,
    TestHealthSnapshotViewSet,
    SelfCheckView,
    RAGStatusView,
    RAGReindexView,
    HealthDashboardView,
    ModuleStatsView,
    FrontendTestStatsView,
    FrontendTestStreamView,
)

router = DefaultRouter()
router.register("runs", TestRunRecordViewSet, basename="test-runs")
router.register("issues", TestIssueViewSet, basename="test-issues")
router.register("snapshots", TestHealthSnapshotViewSet, basename="test-snapshots")

urlpatterns = [
    # Specific paths before router to avoid router's <pk> pattern swallowing them
    path("runs/stream/", TestRunStreamView.as_view(), name="test-hub-run-stream"),
    path("runs/stream-frontend/", FrontendTestStreamView.as_view(), name="test-hub-run-stream-frontend"),
    path("", include(router.urls)),
    path("health/", HealthDashboardView.as_view(), name="test-hub-health"),
    path("selfcheck/", SelfCheckView.as_view(), name="test-hub-selfcheck"),
    path("rag-status/", RAGStatusView.as_view(), name="test-hub-rag-status"),
    path("rag-reindex/", RAGReindexView.as_view(), name="test-hub-rag-reindex"),
    path("module/<str:module>/", ModuleStatsView.as_view(), name="test-hub-module-stats"),
    path("frontend/stats/", FrontendTestStatsView.as_view(), name="test-hub-frontend-stats"),
]
