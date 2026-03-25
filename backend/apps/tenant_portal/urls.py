from django.urls import path

from . import views

urlpatterns = [
    path(
        "conversations/",
        views.TenantConversationsListCreateView.as_view(),
        name="tenant-ai-conversations",
    ),
    path(
        "conversations/<int:pk>/",
        views.TenantConversationDetailView.as_view(),
        name="tenant-ai-conversation-detail",
    ),
    path(
        "conversations/<int:pk>/messages/",
        views.TenantConversationMessageCreateView.as_view(),
        name="tenant-ai-conversation-messages",
    ),
    path(
        "conversations/<int:pk>/maintenance-draft/",
        views.TenantConversationMaintenanceDraftView.as_view(),
        name="tenant-ai-maintenance-draft",
    ),
]
