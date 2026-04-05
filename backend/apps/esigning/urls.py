from django.urls import path

from .views import (
    ESigningCreatePublicLinkView,
    ESigningDownloadSignedView,
    ESigningTestPdfView,
    ESigningPublicDocumentView,
    ESigningPublicDocumentDeleteView,
    ESigningPublicDocumentsView,
    ESigningPublicDraftView,
    ESigningPublicSignDetailView,
    ESigningPublicSubmitSignatureView,
    ESigningResendView,
    ESigningSignerStatusView,
    ESigningSubmissionDetailView,
    ESigningSubmissionDocumentsView,
    ESigningSubmissionListCreateView,
    ESigningWebhookInfoView,
    GotenbergHealthView,
)

urlpatterns = [
    # Public signing (no auth)
    path("public-sign/<uuid:link_id>/", ESigningPublicSignDetailView.as_view(), name="esigning-public-sign"),
    path("public-sign/<uuid:link_id>/document/", ESigningPublicDocumentView.as_view(), name="esigning-public-document"),
    path("public-sign/<uuid:link_id>/sign/", ESigningPublicSubmitSignatureView.as_view(), name="esigning-public-submit"),
    path("public-sign/<uuid:link_id>/draft/", ESigningPublicDraftView.as_view(), name="esigning-public-draft"),
    path("public-sign/<uuid:link_id>/documents/", ESigningPublicDocumentsView.as_view(), name="esigning-public-documents"),
    path("public-sign/<uuid:link_id>/documents/<int:doc_id>/", ESigningPublicDocumentDeleteView.as_view(), name="esigning-public-document-delete"),

    # Authenticated staff endpoints
    path("submissions/", ESigningSubmissionListCreateView.as_view(), name="esigning-list"),
    path("submissions/<int:pk>/", ESigningSubmissionDetailView.as_view(), name="esigning-detail"),
    path("submissions/<int:pk>/download/", ESigningDownloadSignedView.as_view(), name="esigning-download"),
    path("submissions/<int:pk>/test-pdf/", ESigningTestPdfView.as_view(), name="esigning-test-pdf"),
    path("submissions/<int:pk>/resend/", ESigningResendView.as_view(), name="esigning-resend"),
    path("submissions/<int:pk>/signer-status/", ESigningSignerStatusView.as_view(), name="esigning-signer-status"),
    path("submissions/<int:pk>/documents/", ESigningSubmissionDocumentsView.as_view(), name="esigning-submission-documents"),
    path(
        "submissions/<int:pk>/public-link/",
        ESigningCreatePublicLinkView.as_view(),
        name="esigning-public-link-create",
    ),
    path("webhook/info/", ESigningWebhookInfoView.as_view(), name="esigning-webhook-info"),
    path("gotenberg/health/", GotenbergHealthView.as_view(), name="gotenberg-health"),
]
