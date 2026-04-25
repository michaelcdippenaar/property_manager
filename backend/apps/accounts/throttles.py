import logging

from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle

logger = logging.getLogger(__name__)


class AuthAnonThrottle(AnonRateThrottle):
    """Rate limit for login, register, and Google OAuth endpoints -- 5/min per IP."""
    scope = "anon_auth"


class OTPSendThrottle(AnonRateThrottle):
    """Stricter rate limit for OTP send (prevents SMS abuse) -- 3/min per IP."""
    scope = "otp_send"


class OTPVerifyThrottle(AnonRateThrottle):
    """Rate limit for OTP verification (prevents brute force) -- 5/min per IP."""
    scope = "otp_verify"


class InviteAcceptThrottle(AnonRateThrottle):
    """Rate limit for tenant-invite acceptance -- 5/min per IP."""
    scope = "invite_accept"


class PasswordChangeThrottle(SimpleRateThrottle):
    """
    Per-user rate limit for password change -- 5/min keyed on user PK.
    Applied to ChangePasswordView to prevent brute-forcing current_password
    via a stolen short-lived access token (account takeover risk).
    """
    scope = "password_change"

    def get_cache_key(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return None
        ident = self.cache_format % {
            "scope": self.scope,
            "ident": request.user.pk,
        }
        return ident


class LoginHourlyThrottle(SimpleRateThrottle):
    """
    Per-user hourly rate limit for login -- 20/hr keyed on email address.
    Applied alongside AuthAnonThrottle which handles per-IP minute-level limiting.
    """
    scope = "login_hourly_user"

    def get_cache_key(self, request, view):
        email = (request.data.get("email") or "").strip().lower()
        if not email:
            return None  # No key -> no per-user limit when email absent
        ident = self.cache_format % {
            "scope": self.scope,
            "ident": email,
        }
        return ident
