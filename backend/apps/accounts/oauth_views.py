import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone as tz
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .audit import log_auth_event
from .models import Agency, User, UserInvite, UserTOTP, TOTP_REQUIRED_ROLES
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
            # Phase 3.1 — bootstrap-singleton path REMOVED.
            #
            # If a pending invite matches this email, consume it and create a
            # User attached to the invite's agency.
            invite = (
                UserInvite.objects
                .filter(email=email, accepted_at__isnull=True, cancelled_at__isnull=True)
                .order_by("-created_at")
                .first()
            )
            if invite is not None:
                with transaction.atomic():
                    user = User.objects.create_user(
                        email=email,
                        password=None,
                        first_name=idinfo.get("given_name", ""),
                        last_name=idinfo.get("family_name", ""),
                        role=invite.role,
                        agency=invite.agency,
                    )
                    user.set_unusable_password()
                    user.save(update_fields=["password"])
                    invite.accepted_at = tz.now()
                    invite.save(update_fields=["accepted_at"])
                created = True
            else:
                # No matching User and no pending invite — frontend must
                # collect agency-creation details and call complete-signup.
                # IMPORTANTLY no User row is created here.
                log_auth_event(
                    "google_auth_needs_signup",
                    request=request,
                    metadata={"email": email},
                )
                return Response(
                    {
                        "needs_signup": True,
                        "email": email,
                        "given_name": idinfo.get("given_name", ""),
                        "family_name": idinfo.get("family_name", ""),
                        "google_credential": credential,
                    },
                    status=status.HTTP_200_OK,
                )

        log_auth_event("google_auth", request=request, user=user, metadata={"created": created, "email": email})

        # ── 2FA gate ──────────────────────────────────────────────────────────
        from .totp_views import _make_two_fa_token
        from datetime import timedelta

        totp_required = user.role in TOTP_REQUIRED_ROLES
        totp_enrolled = False
        try:
            totp_rec = user.totp
            totp_enrolled = totp_rec.is_active
        except UserTOTP.DoesNotExist:
            totp_rec = None

        if totp_required and not totp_enrolled:
            if totp_rec is None:
                from .models import TOTP_GRACE_PERIOD_DAYS
                totp_rec = UserTOTP.objects.create(user=user, secret="")
            if totp_rec.grace_deadline is None:
                from .models import TOTP_GRACE_PERIOD_DAYS
                totp_rec.grace_deadline = tz.now() + timedelta(days=TOTP_GRACE_PERIOD_DAYS)
                totp_rec.save(update_fields=["grace_deadline"])

            refresh = RefreshToken.for_user(user)
            two_fa_token = _make_two_fa_token(user)
            now = tz.now()
            in_grace = now < totp_rec.grace_deadline
            resp_data = {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
                "created": created,
                "two_fa_enroll_required": True,
                "two_fa_hard_blocked": not in_grace,
                "two_fa_token": two_fa_token,
                "grace_deadline": totp_rec.grace_deadline.isoformat(),
            }
            return Response(resp_data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

        if totp_enrolled:
            two_fa_token = _make_two_fa_token(user)
            return Response(
                {"two_fa_required": True, "two_fa_token": two_fa_token, "created": created},
                status=status.HTTP_200_OK,
            )

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


class GoogleCompleteSignupView(APIView):
    """Phase 3.1 — finish a Google signup by creating an Agency + User.

    POST /api/v1/auth/google/complete-signup/
    Body: {
      "google_credential": "<id_token>",
      "account_type": "agency" | "individual",
      "agency_name": "Acme Estates"  (required if account_type == agency)
    }

    Verifies the ID token afresh, then runs the same atomic Agency-then-User
    flow as RegisterSerializer. Returns JWT tokens on success.
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthAnonThrottle]

    def post(self, request):
        credential = (request.data.get("google_credential") or "").strip()
        account_type = (request.data.get("account_type") or "").strip()
        agency_name = (request.data.get("agency_name") or "").strip()

        if not credential:
            return Response({"error": "google_credential is required."}, status=status.HTTP_400_BAD_REQUEST)
        if account_type not in dict(Agency.AccountType.choices):
            return Response(
                {"error": "account_type must be 'agency' or 'individual'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if account_type == Agency.AccountType.AGENCY and not agency_name:
            return Response(
                {"agency_name": "Agency name is required for estate agency accounts."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
        if not client_id:
            return Response(
                {"error": "Google sign-in is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            idinfo = id_token.verify_oauth2_token(
                credential, google_requests.Request(), client_id
            )
        except ValueError:
            return Response({"error": "Invalid Google token."}, status=status.HTTP_400_BAD_REQUEST)

        email = (idinfo.get("email") or "").lower().strip()
        if not email or not idinfo.get("email_verified", False):
            return Response(
                {"error": "Google account email is not verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Refuse if a user already exists for this email — they must use the
        # standard Google login path (which would have logged them in directly).
        if User.objects.filter(email=email, is_active=True).exists():
            return Response(
                {"error": "A user with this email already exists. Sign in instead."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        first_name = idinfo.get("given_name", "")
        last_name = idinfo.get("family_name", "")

        if account_type == Agency.AccountType.AGENCY:
            display_name = agency_name
        else:
            full = f"{first_name} {last_name}".strip()
            display_name = f"{full}'s Properties" if full else f"{email}'s Properties"

        with transaction.atomic():
            agency = Agency.objects.create(account_type=account_type, name=display_name)
            user = User.objects.create_user(
                email=email,
                password=None,
                first_name=first_name,
                last_name=last_name,
                role=User.Role.AGENCY_ADMIN,
                agency=agency,
            )
            user.set_unusable_password()
            user.save(update_fields=["password"])

        # Seed starter content outside the txn — best-effort.
        try:
            from .starter_content import seed_starter_content
            seed_starter_content(agency)
        except Exception:  # pragma: no cover
            logger.exception(
                "starter_content seeding failed for agency %s (google complete-signup)", agency.pk
            )

        log_auth_event(
            "google_complete_signup",
            request=request,
            user=user,
            metadata={"email": email, "account_type": account_type, "agency_id": agency.pk},
        )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
                "created": True,
            },
            status=status.HTTP_201_CREATED,
        )
