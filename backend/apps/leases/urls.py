from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LeaseViewSet
from .parse_view import ParseLeaseDocumentView

router = DefaultRouter()
router.register("", LeaseViewSet, basename="lease")

urlpatterns = [
    path("parse-document/", ParseLeaseDocumentView.as_view(), name="lease-parse-document"),
    path("", include(router.urls)),
]
