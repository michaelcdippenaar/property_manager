from rest_framework.throttling import AnonRateThrottle


class AuthAnonThrottle(AnonRateThrottle):
    """Rate limit for login, register, and Google OAuth endpoints."""
    scope = "anon_auth"


class OTPSendThrottle(AnonRateThrottle):
    """Stricter rate limit for OTP send (prevents SMS abuse)."""
    scope = "otp_send"


class OTPVerifyThrottle(AnonRateThrottle):
    """Rate limit for OTP verification (prevents brute force)."""
    scope = "otp_verify"
