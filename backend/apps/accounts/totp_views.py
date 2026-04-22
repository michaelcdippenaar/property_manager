"""
TOTP 2FA views — RNT-SEC-003

Flow summary:
  1. POST /auth/login/  →  if 2FA enrolled: returns {two_fa_required: true, two_fa_token: <short JWT>}
                           if 2FA NOT enrolled but required: returns {two_fa_required: false, two_fa_enroll_required: true, two_fa_token: <short JWT>}
                           if 2FA optional and not enrolled: returns full tokens as before
  2. POST /auth/2fa/verify/         (with two_fa_token in body) → returns full tokens
  3. POST /auth/2fa/setup/          (authenticated) → creates pending TOTP, returns QR URI + secret
  4. POST /auth/2fa/setup/confirm/  (authenticated, with two_fa_token) → activates TOTP, issues recovery codes
  5. POST /auth/2fa/recovery/       (with two_fa_token + recovery_code) → returns full tokens
  6. GET  /auth/2fa/status/         (authenticated) → 2FA status for the current user
  7. POST /auth/2fa/reset/request/  (public) → sends email with reset token
  8. POST /auth/2fa/reset/confirm/  (public, email token + recovery code) → deactivates TOTP so user can re-enroll

The ``two_fa_token`` is a short-lived (10 min) JWT that carries the user PK as its subject
and the custom claim ``two_fa_pending: true`` so it cannot be used as a regular access token.
"""

import base64
import io

from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import log_auth_event
from .models import User, UserTOTP, TOTPRecoveryCode, TOTP_REQUIRED_ROLES, TOTP_GRACE_PERIOD_DAYS
from .throttles import AuthAnonThrottle, OTPVerifyThrottle


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_two_fa_token(user: User) -> str:
    """Issue a short-lived JWT that marks a partially-authenticated session."""
    from rest_framework_simplejwt.tokens import AccessToken
    token = AccessToken()
    token["user_id"] = user.pk
    token["two_fa_pending"] = True
    token.set_exp(lifetime=timedelta(minutes=10))
    return str(token)


def _decode_two_fa_token(raw_token: str):
    """
    Decode a two_fa_token.  Returns the User or raises ValueError on any error.
    The token MUST carry ``two_fa_pending: true``; plain access tokens are rejected.
    """
    from rest_framework_simplejwt.tokens import AccessToken, TokenError
    try:
        token = AccessToken(raw_token)
    except TokenError as exc:
        raise ValueError(str(exc))

    if not token.get("two_fa_pending"):
        raise ValueError("Not a two_fa_token.")

    user_id = token.get("user_id")
    try:
        return User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        raise ValueError("User not found.")


def _issue_full_tokens(user: User):
    """Return access + refresh JWT pair."""
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": _user_data(user),
    }


def _user_data(user: User) -> dict:
    from .serializers import UserSerializer
    return UserSerializer(user).data


def _totp_status_for_user(user: User) -> dict:
    """Compute 2FA status fields for the current user."""
    required = user.role in TOTP_REQUIRED_ROLES
    try:
        totp = user.totp
        enrolled = totp.is_active
        grace_deadline = totp.grace_deadline.isoformat() if totp.grace_deadline else None
    except UserTOTP.DoesNotExist:
        enrolled = False
        grace_deadline = None

    in_grace = False
    hard_blocked = False
    if required and not enrolled:
        if grace_deadline is None:
            in_grace = False
            hard_blocked = False   # grace not yet started (should not normally happen)
        else:
            from django.utils import timezone
            now = timezone.now()
            deadline = user.totp.grace_deadline if hasattr(user, "totp") else None
            if deadline:
                in_grace = now < deadline
                hard_blocked = not in_grace

    return {
        "required": required,
        "enrolled": enrolled,
        "in_grace_period": in_grace,
        "hard_blocked": hard_blocked,
        "grace_deadline": grace_deadline,
    }


# ── Views ─────────────────────────────────────────────────────────────────────

class TOTPStatusView(APIView):
    """GET /auth/2fa/status/ — current user's 2FA status."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_totp_status_for_user(request.user))


class TOTPSetupView(APIView):
    """
    POST /auth/2fa/setup/
    Authenticated user requests TOTP setup.
    Returns otpauth:// URI (for QR) and base32 secret (for manual entry).
    Creates a pending UserTOTP record (is_active=False).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import pyotp

        user = request.user
        # Re-use existing pending record or create fresh one
        totp_rec, created = UserTOTP.objects.get_or_create(user=user)
        if not created and totp_rec.is_active:
            return Response(
                {"detail": "2FA is already active for this account. Disable it before re-enrolling."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if created or not totp_rec.secret:
            totp_rec.secret = pyotp.random_base32()
            totp_rec.save(update_fields=["secret"])

        issuer = getattr(settings, "TOTP_ISSUER", "Klikk")
        totp = pyotp.TOTP(totp_rec.secret)
        uri = totp.provisioning_uri(name=user.email, issuer_name=issuer)

        # Generate QR code as base64 PNG
        qr_b64 = _qr_base64(uri)

        return Response({
            "secret": totp_rec.secret,
            "otpauth_uri": uri,
            "qr_code_png_base64": qr_b64,
        })


def _qr_base64(uri: str) -> str:
    """Render a QR code for the given URI and return as base64-encoded PNG."""
    try:
        import qrcode
        qr = qrcode.make(uri)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        return ""


class TOTPSetupConfirmView(APIView):
    """
    POST /auth/2fa/setup/confirm/
    Body: { totp_code: "123456" }
    Authenticated.  Verifies the code against the pending secret, activates it,
    sets the grace_deadline (or clears it if enrollment completes within grace),
    and issues 10 recovery codes (returned once, then gone).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        code = (request.data.get("totp_code") or "").strip()
        if not code:
            return Response({"detail": "totp_code is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            totp_rec = user.totp
        except UserTOTP.DoesNotExist:
            return Response(
                {"detail": "No pending TOTP setup. Call /auth/2fa/setup/ first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if totp_rec.is_active:
            return Response({"detail": "2FA is already active."}, status=status.HTTP_400_BAD_REQUEST)

        if not totp_rec.verify(code):
            log_auth_event("otp_failed", request=request, user=user, metadata={"source": "totp_setup_confirm"})
            return Response({"detail": "Invalid TOTP code."}, status=status.HTTP_400_BAD_REQUEST)

        # Activate
        totp_rec.is_active = True
        totp_rec.enrolled_at = timezone.now()
        totp_rec.grace_deadline = None   # no longer relevant — enrolled
        totp_rec.save(update_fields=["is_active", "enrolled_at", "grace_deadline"])

        # Issue recovery codes
        plain_codes = TOTPRecoveryCode.generate_for_user(user, count=10)

        log_auth_event("otp_verified", request=request, user=user, metadata={"source": "totp_enrollment"})

        return Response({
            "detail": "2FA successfully enrolled.",
            "recovery_codes": plain_codes,
        }, status=status.HTTP_200_OK)


class TOTPVerifyView(APIView):
    """
    POST /auth/2fa/verify/
    Body: { two_fa_token: "...", totp_code: "123456" }
    AllowAny.  Completes the second factor of a login.  Returns full tokens.
    """
    permission_classes = [AllowAny]
    throttle_classes = [OTPVerifyThrottle]

    def post(self, request):
        raw_token = (request.data.get("two_fa_token") or "").strip()
        code = (request.data.get("totp_code") or "").strip()

        if not raw_token or not code:
            return Response(
                {"detail": "two_fa_token and totp_code are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = _decode_two_fa_token(raw_token)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)

        totp_rec = UserTOTP.for_user(user)
        if not totp_rec:
            return Response(
                {"detail": "2FA not enrolled for this account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not totp_rec.verify(code):
            log_auth_event("otp_failed", request=request, user=user, metadata={"source": "totp_login"})
            return Response({"detail": "Invalid or expired TOTP code."}, status=status.HTTP_400_BAD_REQUEST)

        log_auth_event("otp_verified", request=request, user=user, metadata={"source": "totp_login"})
        return Response(_issue_full_tokens(user))


class TOTPRecoveryView(APIView):
    """
    POST /auth/2fa/recovery/
    Body: { two_fa_token: "...", recovery_code: "ABCD-EFGH-IJKL" }
    AllowAny.  Use a recovery code instead of TOTP.
    """
    permission_classes = [AllowAny]
    throttle_classes = [OTPVerifyThrottle]

    def post(self, request):
        raw_token = (request.data.get("two_fa_token") or "").strip()
        raw_code = (request.data.get("recovery_code") or "").strip()

        if not raw_token or not raw_code:
            return Response(
                {"detail": "two_fa_token and recovery_code are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = _decode_two_fa_token(raw_token)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)

        rec = TOTPRecoveryCode.redeem(user, raw_code)
        if rec is None:
            log_auth_event("otp_failed", request=request, user=user, metadata={"source": "totp_recovery"})
            return Response({"detail": "Invalid or already-used recovery code."}, status=status.HTTP_400_BAD_REQUEST)

        log_auth_event("otp_verified", request=request, user=user, metadata={"source": "totp_recovery"})
        return Response(_issue_full_tokens(user))


class TOTPResetRequestView(APIView):
    """
    POST /auth/2fa/reset/request/
    Body: { email: "..." }
    AllowAny.  Sends an email with a one-use reset link that lets a user
    bypass TOTP using an existing recovery code.

    The email contains a password-reset-style UID+token.  The frontend then
    calls /auth/2fa/reset/confirm/ with UID, token, and a recovery code.
    """
    permission_classes = [AllowAny]
    throttle_classes = [AuthAnonThrottle]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        # Always return 200 to avoid enumeration
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return Response({"detail": "If that email is registered, a reset link has been sent."})

        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        base_url = getattr(settings, "SIGNING_PUBLIC_APP_BASE_URL", "") or "http://localhost:5173"
        reset_url = f"{base_url}/2fa-reset?uid={uid}&token={token}"

        try:
            from apps.notifications.services.email import send_template_email
            send_template_email(
                "2fa_reset",
                to_emails=email,
                context={
                    "recipient_name": user.first_name or user.email.split("@")[0],
                    "reset_url": reset_url,
                },
            )
        except Exception:
            pass

        return Response({"detail": "If that email is registered, a reset link has been sent."})


class TOTPResetConfirmView(APIView):
    """
    POST /auth/2fa/reset/confirm/
    Body: { uid, token, recovery_code }
    AllowAny.  Validates email link AND a recovery code, then deactivates
    TOTP so the user can re-enroll on next login.
    """
    permission_classes = [AllowAny]
    throttle_classes = [AuthAnonThrottle]

    def post(self, request):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_decode

        uid = request.data.get("uid", "")
        token = request.data.get("token", "")
        recovery_code = (request.data.get("recovery_code") or "").strip()

        if not all([uid, token, recovery_code]):
            return Response(
                {"detail": "uid, token, and recovery_code are all required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_id = urlsafe_base64_decode(uid).decode()
            user = User.objects.get(pk=user_id, is_active=True)
        except Exception:
            return Response({"detail": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({"detail": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)

        # Verify recovery code
        rec = TOTPRecoveryCode.redeem(user, recovery_code)
        if rec is None:
            log_auth_event("otp_failed", request=request, user=user, metadata={"source": "totp_reset"})
            return Response({"detail": "Invalid or already-used recovery code."}, status=status.HTTP_400_BAD_REQUEST)

        # Deactivate TOTP — user must re-enroll
        try:
            totp_rec = user.totp
            totp_rec.is_active = False
            totp_rec.enrolled_at = None
            totp_rec.secret = ""
            # Restart grace period
            if user.role in TOTP_REQUIRED_ROLES:
                totp_rec.grace_deadline = timezone.now() + timedelta(days=TOTP_GRACE_PERIOD_DAYS)
            totp_rec.save()
        except UserTOTP.DoesNotExist:
            pass

        log_auth_event("otp_verified", request=request, user=user, metadata={"source": "totp_reset"})
        return Response({"detail": "2FA has been reset. Please re-enroll on your next login."})
