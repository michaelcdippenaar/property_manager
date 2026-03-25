"""Thin facade so callers can import `send_sms_otp` without depending on app paths."""


def send_sms_otp(phone: str, code: str) -> None:
    """Send OTP code via SMS (Twilio when configured; see apps.notifications)."""
    from apps.notifications.services import deliver_otp_sms

    deliver_otp_sms(phone, code)
