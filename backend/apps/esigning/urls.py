from django.urls import path

from .views import (
    ESigningCreatePublicLinkView,
    ESigningDownloadSignedView,
    ESigningPublicCompletedView,
    ESigningPublicDocumentView,
    ESigningPublicSignDetailView,
    ESigningPublicSubmitSignatureView,
    ESigningResendView,
    ESigningSignerStatusView,
    ESigningSubmissionDetailView,
    ESigningSubmissionListCreateView,
    ESigningWebhookInfoView,
)
from .webhooks import DocuSealWebhookView

urlpatterns = [
    # Public signing (no auth)
    path("public-sign/<uuid:link_id>/", ESigningPublicSignDetailView.as_view(), name="esigning-public-sign"),
    path("public-sign/<uuid:link_id>/completed/", ESigningPublicCompletedView.as_view(), name="esigning-public-completed"),
    path("public-sign/<uuid:link_id>/document/", ESigningPublicDocumentView.as_view(), name="esigning-public-document"),
    path("public-sign/<uuid:link_id>/sign/", ESigningPublicSubmitSignatureView.as_view(), name="esigning-public-submit"),

    # Authenticated staff endpoints
    path("submissions/", ESigningSubmissionListCreateView.as_view(), name="esigning-list"),
    path("submissions/<int:pk>/", ESigningSubmissionDetailView.as_view(), name="esigning-detail"),
    path("submissions/<int:pk>/download/", ESigningDownloadSignedView.as_view(), name="esigning-download"),
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
