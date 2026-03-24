from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterView, LoginView, MeView, OTPSendView, OTPVerifyView, TenantsListView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("otp/send/", OTPSendView.as_view(), name="otp-send"),
    path("otp/verify/", OTPVerifyView.as_view(), name="otp-verify"),
    path("tenants/", TenantsListView.as_view(), name="tenants-list"),
]
