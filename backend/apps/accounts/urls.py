from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LoginView, MeView, OTPSendView, OTPVerifyView,
    TenantsListView, PersonViewSet, PersonDetailView, PersonDocumentListCreateView,
    PersonDocumentDetailView, PushTokenView,
    ChangePasswordView, LogoutView, PasswordResetRequestView, PasswordResetConfirmView,
    AcceptInviteView,
)
from .admin_views import UserListView, UserDetailView, InviteUserView, PendingInvitesView, CancelInviteView, ResendInviteView, AgencySettingsView
from .oauth_views import GoogleAuthView
from .lookup_views import EntityLookupView
from .totp_views import (
    TOTPStatusView, TOTPSetupView, TOTPSetupConfirmView,
    TOTPVerifyView, TOTPRecoveryView,
    TOTPResetRequestView, TOTPResetConfirmView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("google/", GoogleAuthView.as_view(), name="auth-google"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("otp/send/", OTPSendView.as_view(), name="otp-send"),
    path("otp/verify/", OTPVerifyView.as_view(), name="otp-verify"),
    path("push-token/", PushTokenView.as_view(), name="push-token"),
    path("tenants/", TenantsListView.as_view(), name="tenants-list"),
    path("persons/", PersonViewSet.as_view(), name="persons-list"),
    path("persons/<int:pk>/", PersonDetailView.as_view(), name="persons-detail"),
    path("persons/<int:person_pk>/documents/", PersonDocumentListCreateView.as_view(), name="person-documents"),
    path("persons/<int:person_pk>/documents/<int:pk>/", PersonDocumentDetailView.as_view(), name="person-document-detail"),
    # Admin role management
    path("users/", UserListView.as_view(), name="user-list"),
    path("users/<int:pk>/", UserDetailView.as_view(), name="user-detail"),
    path("users/invite/", InviteUserView.as_view(), name="user-invite"),
    path("users/invites/", PendingInvitesView.as_view(), name="user-invites"),
    path("users/invites/<int:pk>/", CancelInviteView.as_view(), name="user-invite-cancel"),
    path("users/invites/<int:pk>/resend/", ResendInviteView.as_view(), name="user-invite-resend"),
    # Auth hardening
    path("change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    path("accept-invite/", AcceptInviteView.as_view(), name="auth-accept-invite"),
    # Cross-entity lookup by ID number or company registration number
    path("lookup/", EntityLookupView.as_view(), name="entity-lookup"),
    # Agency settings (singleton)
    path("agency/", AgencySettingsView.as_view(), name="agency-settings"),
    # ── TOTP 2FA ──────────────────────────────────────────────────────────────
    path("2fa/status/", TOTPStatusView.as_view(), name="2fa-status"),
    path("2fa/setup/", TOTPSetupView.as_view(), name="2fa-setup"),
    path("2fa/setup/confirm/", TOTPSetupConfirmView.as_view(), name="2fa-setup-confirm"),
    path("2fa/verify/", TOTPVerifyView.as_view(), name="2fa-verify"),
    path("2fa/recovery/", TOTPRecoveryView.as_view(), name="2fa-recovery"),
    path("2fa/reset/request/", TOTPResetRequestView.as_view(), name="2fa-reset-request"),
    path("2fa/reset/confirm/", TOTPResetConfirmView.as_view(), name="2fa-reset-confirm"),
]
