"""apps/audit/urls.py"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AuditEventViewSet, AuditTimelineView

router = DefaultRouter()
router.register("events", AuditEventViewSet, basename="audit-event")

urlpatterns = router.urls + [
    path(
        "timeline/<str:app_label>/<str:model>/<int:pk>/",
        AuditTimelineView.as_view(),
        name="audit-timeline",
    ),
]
