from django.urls import path
from .views import ESigningSubmissionListCreateView, ESigningSubmissionDetailView, ESigningResendView
from .webhooks import DocuSealWebhookView

urlpatterns = [
    path('submissions/',              ESigningSubmissionListCreateView.as_view(), name='esigning-list'),
    path('submissions/<int:pk>/',     ESigningSubmissionDetailView.as_view(),     name='esigning-detail'),
    path('submissions/<int:pk>/resend/', ESigningResendView.as_view(),            name='esigning-resend'),
    path('webhook/',                  DocuSealWebhookView.as_view(),              name='esigning-webhook'),
]
