from django.urls import path
from .views import CurrentDocumentsView, PendingConsentsView, UserConsentView

urlpatterns = [
    path("documents/current/", CurrentDocumentsView.as_view(), name="legal-current-documents"),
    path("pending/", PendingConsentsView.as_view(), name="legal-pending-consents"),
    path("consent/", UserConsentView.as_view(), name="legal-consent"),
]
