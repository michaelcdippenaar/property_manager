from django.urls import path

from .views import (
    ESigningCreatePublicLinkView,
    ESigningPublicSignDetailView,
    ESigningResendView,
    ESigningSignerStatusView,
    ESigningSubmissionDetailView,
    ESigningSubmissionListCreateView,
    ESigningWebhookInfoView,
)
from .webhooks import DocuSealWebhookView

urlpatterns = [
    path("public-sign/<uuid:link_id>/", ESigningPublicSignDetailView.as_view(), name="esigning-public-sign"),
    path("submissions/", ESigningSubmissionListCreateView.as_view(), name="esigning-list"),
    path("submissions/<int:pk>/", ESigningSubmissionDetailView.as_view(), name="esigning-detail"),
    path("submissions/<int:pk>/resend/", ESigningResendView.as_view(), name="esigning-resend"),
    path("submissions/<int:pk>/signer-status/", ESigningSignerStatusView.as_view(), name="esigning-signer-status"),
    path(
        "submissions/<int:pk>/public-link/",
        ESigningCreatePublicLinkView.as_view(),
        name="esigning-public-link-create",
    ),
    path("webhook/info/", ESigningWebhookInfoView.as_view(), name="esigning-webhook-info"),
    path("webhook/", DocuSealWebhookView.as_view(), name="esigning-webhook"),
]
