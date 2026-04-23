from django.urls import path

from .views import (
    DataExportRequestView,
    DSARQueueView,
    DSARReviewView,
    ErasureRequestView,
    ExportDownloadView,
    MyDSARRequestsView,
)

urlpatterns = [
    # Tenant / data-subject self-service
    path("data-export/", DataExportRequestView.as_view(), name="popia-data-export"),
    path("erasure-request/", ErasureRequestView.as_view(), name="popia-erasure-request"),
    path("my-requests/", MyDSARRequestsView.as_view(), name="popia-my-requests"),
    path("download/<str:token>/", ExportDownloadView.as_view(), name="popia-download"),

    # Operator queue
    path("dsar-queue/", DSARQueueView.as_view(), name="popia-dsar-queue"),
    path("dsar-queue/<int:pk>/review/", DSARReviewView.as_view(), name="popia-dsar-review"),
]
