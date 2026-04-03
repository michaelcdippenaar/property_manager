import logging

from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .audit import log_auth_event
from .models import User
from .serializers import UserSerializer
from .throttles import AuthAnonThrottle

logger = logging.getLogger(__name__)


class GoogleAuthView(APIView):
    """Authenticate or register via Google ID token.

    POST /api/v1/auth/google/
    Body: {"credential": "<google_id_token>"}
    Returns JWT tokens + user data + created flag.
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthAnonThrottle]

    def post(self, request):
        credential = request.data.get("credential", "").strip()
        if not credential:
            return Response(
                {"error": "Google credential is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
        if not client_id:
            logger.error("GOOGLE_OAUTH_CLIENT_ID is not configured.")
            return Response(
                {"error": "Google sign-in is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            idinfo = id_token.verify_oauth2_token(
                credential, google_requests.Request(), client_id
            )
        except ValueError:
            return Response(
                {"error": "Invalid Google token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = idinfo.get("email", "").lower().strip()
        if not email or not idinfo.get("email_verified", False):
            return Response(
                {"error": "Google account email is not verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created = False
        try:
            user = User.objects.get(email=email)
            if not user.is_active:
                return Response(
                    {"error": "Account is disabled."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        except User.DoesNotExist:
            user = User.objects.create_user(
                email=email,
                password=None,
                first_name=idinfo.get("given_name", ""),
                last_name=idinfo.get("family_name", ""),
            )
            user.set_unusable_password()
            user.save(update_fields=["password"])
            created = True

        log_auth_event("google_auth", request=request, user=user, metadata={"created": created, "email": email})

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
                "created": created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
