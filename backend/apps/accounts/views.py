import secrets

from django.conf import settings
from django.contrib.auth import authenticate
from django.utils import timezone
from datetime import timedelta
from rest_framework import status, generics, parsers
from rest_framework.permissions import AllowAny, IsAuthenticated

from .permissions import IsAgentOrAdmin
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken

from django.shortcuts import get_object_or_404
from .models import (
    User, OTPCode, Person, PersonDocument, PushToken, LoginAttempt, UserInvite, Agency,
    UserTOTP, TOTP_REQUIRED_ROLES, TOTP_OPTIONAL_ROLES, TOTP_GRACE_PERIOD_DAYS,
)
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, OTPSendSerializer, OTPVerifySerializer, PersonSerializer, PersonDocumentSerializer, TenantListSerializer
from .audit import log_auth_event
from .throttles import AuthAnonThrottle, InviteAcceptThrottle, LoginHourlyThrottle, OTPSendThrottle, OTPVerifyThrottle, PasswordChangeThrottle
from utils.http import get_client_ip


class RegisterView(APIView):
    """
    Public self-registration — only permitted to bootstrap the singleton
    Agency. Once an Agency exists, additional users must be onboarded via
    ``/users/invite/`` so that the existing admin can choose the new user's
    role (tenant / supplier / owner / agent). Allowing open registration
    after bootstrap would silently grant every new signup full admin
    visibility over the existing landlord's data.
    """
    permission_classes = [AllowAny]
    throttle_classes = [AuthAnonThrottle]

    def post(self, request):
        # Pass request in context so RegisterSerializer can record UserConsent
        # rows with the correct IP + user-agent for POPIA s11 audit trail.
        serializer = RegisterSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        log_auth_event("register", request=request, user=user)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthAnonThrottle, LoginHourlyThrottle]

    LOCKOUT_THRESHOLD = 5
    LOCKOUT_WINDOW_MINUTES = 30

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        ip = get_client_ip(request)

        # Check lockout
        if email:
            window = timezone.now() - timedelta(minutes=self.LOCKOUT_WINDOW_MINUTES)
            recent_failures = LoginAttempt.objects.filter(
                email=email, succeeded=False, created_at__gte=window
            ).count()
            if recent_failures >= self.LOCKOUT_THRESHOLD:
                return Response(
                    {"detail": "Account temporarily locked due to too many failed login attempts. Try again later."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

        serializer = LoginSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            # Log failed attempt
            if email:
                LoginAttempt.objects.create(email=email, ip_address=ip or None, succeeded=False)
            log_auth_event("login_failed", request=request, metadata={"email": email})
            raise

        # Log successful attempt
        if email:
            LoginAttempt.objects.create(email=email, ip_address=ip or None, succeeded=True)

        user = serializer.validated_data["user"]
        log_auth_event("login_success", request=request, user=user)

        # ── 2FA gate ──────────────────────────────────────────────────────────
        from .totp_views import _make_two_fa_token

        totp_required = user.role in TOTP_REQUIRED_ROLES
        totp_enrolled = False
        try:
            totp_rec = user.totp
            totp_enrolled = totp_rec.is_active
        except UserTOTP.DoesNotExist:
            totp_rec = None

        if totp_required and not totp_enrolled:
            # Ensure grace period record exists
            if totp_rec is None:
                totp_rec = UserTOTP.objects.create(user=user, secret="")
            if totp_rec.grace_deadline is None:
                totp_rec.grace_deadline = timezone.now() + timedelta(days=TOTP_GRACE_PERIOD_DAYS)
                totp_rec.save(update_fields=["grace_deadline"])

            now = timezone.now()
            in_grace = now < totp_rec.grace_deadline
            if in_grace:
                # Allow through but signal that enrollment is required
                two_fa_token = _make_two_fa_token(user)
                refresh = RefreshToken.for_user(user)
                return Response({
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": UserSerializer(user).data,
                    "two_fa_required": False,
                    "two_fa_enroll_required": True,
                    "two_fa_token": two_fa_token,
                    "grace_deadline": totp_rec.grace_deadline.isoformat(),
                }, status=status.HTTP_200_OK)
            else:
                # Hard-blocked — must enroll via two_fa_token before getting full access
                two_fa_token = _make_two_fa_token(user)
                return Response({
                    "two_fa_required": False,
                    "two_fa_enroll_required": True,
                    "two_fa_hard_blocked": True,
                    "two_fa_token": two_fa_token,
                }, status=status.HTTP_200_OK)

        if totp_enrolled:
            # 2FA required — return partial token; frontend calls /auth/2fa/verify/
            two_fa_token = _make_two_fa_token(user)
            return Response({
                "two_fa_required": True,
                "two_fa_token": two_fa_token,
            }, status=status.HTTP_200_OK)

        # ── Optional 2FA prompt (e.g. owner role) ────────────────────────────
        totp_optional = user.role in TOTP_OPTIONAL_ROLES
        if totp_optional and not totp_enrolled:
            refresh = RefreshToken.for_user(user)
            # Only suggest setup if the user has never skipped the prompt before.
            suggest = user.skipped_2fa_setup_at is None
            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
                "two_fa_suggest_setup": suggest,
            }, status=status.HTTP_200_OK)

        # No 2FA required/enrolled — issue full tokens directly
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        }, status=status.HTTP_200_OK)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class OTPSendView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPSendThrottle]

    def post(self, request):
        serializer = OTPSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            # Don't reveal whether phone exists
            return Response({"detail": "OTP sent if phone is registered."})

        code = f"{secrets.randbelow(900000) + 100000}"
        OTPCode.objects.create(user=user, code=code)
        from core.notifications import send_sms_otp
        send_sms_otp(phone, code)

        log_auth_event("otp_sent", request=request, user=user, metadata={"phone": phone})

        return Response({"detail": "OTP sent if phone is registered."})


class OTPVerifyView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPVerifyThrottle]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        code = serializer.validated_data["code"]
        expiry = timezone.now() - timedelta(minutes=10)

        try:
            user = User.objects.get(phone=phone)
            otp = OTPCode.objects.filter(
                user=user, code=code, is_used=False, created_at__gte=expiry
            ).latest("created_at")
        except (User.DoesNotExist, OTPCode.DoesNotExist):
            log_auth_event("otp_failed", request=request, metadata={"phone": phone})
            return Response({"detail": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)

        otp.is_used = True
        otp.save()

        log_auth_event("otp_verified", request=request, user=user, metadata={"phone": phone})

        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        })


class PushTokenView(APIView):
    """Register or refresh an FCM/APNs push token for the authenticated user."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get("token", "").strip()
        platform = request.data.get("platform", "").strip().lower()
        if not token:
            return Response({"detail": "token is required."}, status=status.HTTP_400_BAD_REQUEST)
        if platform not in ("ios", "android"):
            return Response({"platform": ["Invalid platform. Must be one of: ios, android."]}, status=status.HTTP_400_BAD_REQUEST)

        PushToken.objects.update_or_create(
            user=request.user,
            token=token,
            defaults={"platform": platform},
        )
        return Response({"detail": "Token registered."})

    def delete(self, request):
        """
        Deregister a push token for the authenticated user (POPIA device deregistration).

        Body: {"token": "<device-token>"}

        Behaviour:
        - 400 if `token` is missing from the request body.
        - 204 if the token was deleted, or if it never existed (idempotent).
        """
        token = request.data.get("token", "").strip()
        if not token:
            return Response({"detail": "token is required."}, status=status.HTTP_400_BAD_REQUEST)
        PushToken.objects.filter(user=request.user, token=token).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PushPreferenceView(APIView):
    """
    GET  /auth/push-preferences/   — list all category preferences for the user
    POST /auth/push-preferences/   — upsert a category preference
         Body: {"category": "rent", "enabled": true}
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.notifications.models import PushPreference

        prefs = PushPreference.objects.filter(user=request.user).values(
            "category", "enabled"
        )
        # Fill in defaults for categories with no saved row
        existing = {p["category"]: p["enabled"] for p in prefs}
        result = [
            {"category": cat, "enabled": existing.get(cat, True)}
            for cat, _ in PushPreference.Category.choices
        ]
        return Response(result)

    def post(self, request):
        from apps.notifications.models import PushPreference

        category = (request.data.get("category") or "").strip()
        enabled = request.data.get("enabled")

        if category not in dict(PushPreference.Category.choices):
            return Response(
                {"detail": f"category must be one of: {', '.join(dict(PushPreference.Category.choices))}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(enabled, bool):
            return Response(
                {"detail": "enabled must be a boolean."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        PushPreference.objects.update_or_create(
            user=request.user,
            category=category,
            defaults={"enabled": enabled},
        )
        return Response({"category": category, "enabled": enabled})


class Skip2FASetupView(APIView):
    """
    POST /auth/2fa/skip/
    Authenticated.  Called by optional-2FA users (owner role) who click
    "Skip for now" on the 2FA setup suggestion prompt.  Stamps
    skipped_2fa_setup_at so subsequent logins no longer show the prompt.
    Idempotent — calling again just refreshes the timestamp.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.role not in TOTP_OPTIONAL_ROLES:
            return Response(
                {"detail": "2FA skip is not applicable for your role."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.skipped_2fa_setup_at = timezone.now()
        user.save(update_fields=["skipped_2fa_setup_at"])
        return Response({"detail": "2FA setup prompt dismissed."})


class MarkWelcomeSeenView(APIView):
    """
    POST /auth/welcome/
    Idempotent — stamps seen_welcome_at on the authenticated user the first
    time they dismiss the tenant welcome screen.  Subsequent calls are a no-op.
    Returns the updated UserSerializer payload so the client can refresh its
    cached profile in one round-trip.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.seen_welcome_at:
            user.seen_welcome_at = timezone.now()
            user.save(update_fields=["seen_welcome_at"])
        return Response(UserSerializer(user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [PasswordChangeThrottle]

    def post(self, request):
        current = request.data.get("current_password", "")
        new = request.data.get("new_password", "")

        # Google OAuth users (unusable password) can set password without current
        if request.user.has_usable_password():
            if not request.user.check_password(current):
                return Response({"detail": "Current password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

        from django.contrib.auth.password_validation import validate_password
        try:
            validate_password(new, request.user)
        except Exception as e:
            return Response({"detail": list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(new)
        request.user.save()
        log_auth_event("password_change", request=request, user=request.user)
        return Response({"detail": "Password changed."})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if refresh:
            try:
                token = RefreshToken(refresh)
                token.blacklist()
            except Exception:
                pass
        log_auth_event("logout", request=request, user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthAnonThrottle]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        # Always return 200 to avoid email enumeration
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return Response({"detail": "If that email is registered, a reset link has been sent."})

        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        base_url = getattr(settings, "SIGNING_PUBLIC_APP_BASE_URL", "")
        reset_url = f"{base_url}/reset-password?uid={uid}&token={token}"

        log_auth_event("password_reset_request", request=request, user=user, metadata={"email": email})

        try:
            from apps.notifications.services.email import send_template_email
            send_template_email(
                "password_reset",
                to_emails=email,
                context={
                    "recipient_name": user.first_name or user.email.split("@")[0],
                    "reset_url": reset_url,
                },
            )
        except Exception:
            pass

        return Response({"detail": "If that email is registered, a reset link has been sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthAnonThrottle]

    def post(self, request):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_decode

        uid = request.data.get("uid", "")
        token = request.data.get("token", "")
        new_password = request.data.get("new_password", "")

        try:
            user_id = urlsafe_base64_decode(uid).decode()
            user = User.objects.get(pk=user_id)
        except Exception:
            return Response({"detail": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({"detail": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)

        from django.contrib.auth.password_validation import validate_password
        try:
            validate_password(new_password, user)
        except Exception as e:
            return Response({"detail": list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        log_auth_event("password_reset_confirm", request=request, user=user)
        return Response({"detail": "Password has been reset."})


class AcceptInviteView(APIView):
    """Accept an invite: validate token, create user with password or Google credential."""
    permission_classes = [AllowAny]
    throttle_classes = [InviteAcceptThrottle]

    def get(self, request):
        """Return invite details (email, role) for the frontend to pre-fill."""
        from django.core.exceptions import ValidationError as DjangoValidationError
        token = request.query_params.get("token", "")
        try:
            invite = UserInvite.objects.select_related("invited_by").get(token=token)
        except (UserInvite.DoesNotExist, ValueError, DjangoValidationError):
            return Response({"detail": "Invalid invite link."}, status=status.HTTP_400_BAD_REQUEST)

        if invite.cancelled_at is not None:
            return Response(
                {
                    "detail": "invite_cancelled",
                    "invited_by": invite.invited_by.full_name if invite.invited_by else "Klikk",
                },
                status=status.HTTP_410_GONE,
            )

        if invite.accepted_at is not None:
            return Response(
                {"detail": "This invitation has already been used. Please sign in instead."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"email": invite.email, "role": invite.role})

    def post(self, request):
        from django.core.exceptions import ValidationError as DjangoValidationError
        token = request.data.get("token", "")
        try:
            invite = UserInvite.objects.get(token=token, accepted_at__isnull=True)
        except (UserInvite.DoesNotExist, ValueError, DjangoValidationError):
            return Response({"detail": "Invalid or expired invite."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if an ACTIVE user with this email already exists. Soft-deleted
        # users are renamed below so they don't block re-registration via invite.
        if User.objects.filter(email=invite.email, is_active=True).exists():
            invite.accepted_at = timezone.now()
            invite.save()
            return Response({"detail": "A user with this email already exists. Please sign in."}, status=status.HTTP_400_BAD_REQUEST)

        # Free the unique-email constraint on any soft-deleted user holding this email
        import uuid
        User.objects.filter(email=invite.email, is_active=False).update(
            email=f"deleted_{uuid.uuid4().hex[:8]}_{invite.email}"
        )

        first_name = request.data.get("first_name", "").strip()
        last_name = request.data.get("last_name", "").strip()
        password = request.data.get("password", "")
        google_credential = request.data.get("google_credential", "")

        if google_credential:
            # Accept via Google — verify token and create user
            from google.oauth2 import id_token
            from google.auth.transport import requests as google_requests

            client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
            try:
                idinfo = id_token.verify_oauth2_token(google_credential, google_requests.Request(), client_id)
            except Exception:
                return Response({"detail": "Invalid Google credential."}, status=status.HTTP_400_BAD_REQUEST)

            google_email = idinfo.get("email", "").lower()
            if google_email != invite.email.lower():
                return Response(
                    {"detail": f"Google account email ({google_email}) does not match invite email ({invite.email})."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user = User.objects.create_user(
                email=invite.email,
                first_name=idinfo.get("given_name", first_name),
                last_name=idinfo.get("family_name", last_name),
                role=invite.role,
            )
            user.set_unusable_password()
            if invite.agency_id:
                user.agency = invite.agency
            user.save()
        else:
            # Accept via password
            if not password:
                return Response({"detail": "Password is required."}, status=status.HTTP_400_BAD_REQUEST)

            from django.contrib.auth.password_validation import validate_password
            try:
                validate_password(password)
            except Exception as e:
                return Response({"detail": list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

            user = User.objects.create_user(
                email=invite.email,
                first_name=first_name,
                last_name=last_name,
                password=password,
                role=invite.role,
            )
            if invite.agency_id:
                user.agency = invite.agency
                user.save(update_fields=["agency"])

        invite.accepted_at = timezone.now()
        invite.save()

        log_auth_event("invite_accepted", request=request, user=user, metadata={"invite_id": invite.id, "role": invite.role})

        # Return JWT so the user is immediately logged in.
        # If this role requires 2FA, also signal enrollment so the frontend
        # can redirect to the enrollment flow immediately post-registration.
        refresh = RefreshToken.for_user(user)
        totp_enroll_required = user.role in TOTP_REQUIRED_ROLES
        if totp_enroll_required:
            from .totp_views import _make_two_fa_token
            two_fa_token = _make_two_fa_token(user)
            totp_rec, _ = UserTOTP.objects.get_or_create(user=user, defaults={"secret": ""})
            if totp_rec.grace_deadline is None:
                totp_rec.grace_deadline = timezone.now() + timedelta(days=TOTP_GRACE_PERIOD_DAYS)
                totp_rec.save(update_fields=["grace_deadline"])
        else:
            two_fa_token = None

        response_data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
            "two_fa_enroll_required": totp_enroll_required,
        }
        if two_fa_token:
            response_data["two_fa_token"] = two_fa_token
        return Response(response_data, status=status.HTTP_201_CREATED)


class TenantsListView(generics.ListAPIView):
    """
    Returns all Person records who appear on at least one lease
    (as primary tenant or co-tenant), annotated with active-lease counts
    so the list can render Active/Inactive badges.
    """
    serializer_class = TenantListSerializer
    permission_classes = [IsAgentOrAdmin]

    def get_queryset(self):
        from django.db.models import Q, Count
        from apps.properties.access import get_accessible_property_ids

        qs = Person.objects.filter(
            Q(leases_as_primary__isnull=False) | Q(co_tenancies__isnull=False)
        ).distinct()

        # Scope to tenants on leases within the user's accessible properties
        user = self.request.user
        if user.role != 'admin':
            prop_ids = get_accessible_property_ids(user)
            qs = qs.filter(
                Q(leases_as_primary__unit__property_id__in=prop_ids)
                | Q(co_tenancies__lease__unit__property_id__in=prop_ids)
            ).distinct()

        return (
            qs
            .select_related("linked_user")
            .annotate(
                active_primary_lease_count=Count(
                    "leases_as_primary",
                    filter=Q(leases_as_primary__status="active"),
                    distinct=True,
                ),
                active_cotenant_lease_count=Count(
                    "co_tenancies",
                    filter=Q(co_tenancies__lease__status="active"),
                    distinct=True,
                ),
            )
            .order_by("full_name")
        )


class PersonViewSet(generics.ListCreateAPIView):
    serializer_class = PersonSerializer
    permission_classes = [IsAgentOrAdmin]

    def get_queryset(self):
        qs = Person.objects.all()
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(full_name__icontains=q)
        return qs


class PersonDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = PersonSerializer
    permission_classes = [IsAgentOrAdmin]
    queryset = Person.objects.all()


class PersonDocumentListCreateView(generics.ListCreateAPIView):
    serializer_class = PersonDocumentSerializer
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def get_queryset(self):
        return PersonDocument.objects.filter(person_id=self.kwargs['person_pk'])

    def perform_create(self, serializer):
        person = get_object_or_404(Person, pk=self.kwargs['person_pk'])
        serializer.save(person=person)


class PersonDocumentDetailView(generics.DestroyAPIView):
    serializer_class = PersonDocumentSerializer
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]

    def get_queryset(self):
        return PersonDocument.objects.filter(person_id=self.kwargs['person_pk'])
