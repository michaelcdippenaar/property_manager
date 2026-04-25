"""
Email OTP 2FA views — RNT-SEC-050

New endpoints:
  POST /auth/2fa/email-send/   — send a 6-digit OTP to the user's email address.
  POST /auth/2fa/email-verify/ — verify the code and exchange for full tokens.

Both endpoints accept a ``two_fa_token`` (partial auth JWT) to identify the
partially-authenticated user without exposing full session credentials.

The OTP is issued / verified via the existing OTPService with purpose="login_2fa".
Audit events written: 2fa_email_sent, 2fa_email_verified, 2fa_email_failed.
"""

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import log_auth_event
from .throttles import OTPSendThrottle, OTPVerifyThrottle
from .totp_views import _decode_two_fa_token, _issue_full_tokens

_PURPOSE = "login_2fa"


class Email2FASendView(APIView):
    """
    POST /auth/2fa/email-send/
    Body: { two_fa_token: "..." }
    AllowAny, throttled by OTPSendThrottle.
    Issues a 6-digit OTP via OTPService (email channel) and returns HTTP 200.
    """
    permission_classes = [AllowAny]
    throttle_classes = [OTPSendThrottle]

    def post(self, request):
        raw_token = (request.data.get("two_fa_token") or "").strip()
        if not raw_token:
            return Response(
                {"detail": "two_fa_token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = _decode_two_fa_token(raw_token)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)

        from apps.accounts.otp.service import OTPService, OTPRateLimitExceeded
        try:
            OTPService.send(user, purpose=_PURPOSE)
        except OTPRateLimitExceeded:
            log_auth_event(
                "2fa_email_failed",
                request=request,
                user=user,
                metadata={"reason": "rate_limited"},
            )
            return Response(
                {"detail": "Too many OTP requests. Please wait before trying again."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except Exception as exc:
            log_auth_event(
                "2fa_email_failed",
                request=request,
                user=user,
                metadata={"reason": str(exc)},
            )
            return Response(
                {"detail": "Failed to send OTP. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        log_auth_event(
            "2fa_email_sent",
            request=request,
            user=user,
            metadata={"email": user.email},
        )
        return Response(
            {"detail": "OTP sent to your registered email address."},
            status=status.HTTP_200_OK,
        )


class Email2FAVerifyView(APIView):
    """
    POST /auth/2fa/email-verify/
    Body: { two_fa_token: "...", code: "123456" }
    AllowAny, throttled by OTPVerifyThrottle.
    Verifies the 6-digit OTP and returns full access + refresh tokens on success.
    """
    permission_classes = [AllowAny]
    throttle_classes = [OTPVerifyThrottle]

    def post(self, request):
        raw_token = (request.data.get("two_fa_token") or "").strip()
        code = (request.data.get("code") or "").strip()

        if not raw_token or not code:
            return Response(
                {"detail": "two_fa_token and code are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = _decode_two_fa_token(raw_token)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)

        from apps.accounts.otp.service import OTPService, OTPMaxAttemptsExceeded
        try:
            verified = OTPService.verify(user, code=code, purpose=_PURPOSE)
        except OTPMaxAttemptsExceeded:
            log_auth_event(
                "2fa_email_failed",
                request=request,
                user=user,
                metadata={"reason": "max_attempts_exceeded"},
            )
            return Response(
                {"detail": "Too many failed attempts. Please request a new OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not verified:
            log_auth_event(
                "2fa_email_failed",
                request=request,
                user=user,
                metadata={"reason": "invalid_code"},
            )
            return Response(
                {"detail": "Invalid or expired OTP code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        log_auth_event(
            "2fa_email_verified",
            request=request,
            user=user,
            metadata={"email": user.email},
        )
        return Response(_issue_full_tokens(user), status=status.HTTP_200_OK)
