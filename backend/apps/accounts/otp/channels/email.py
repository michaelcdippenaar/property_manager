"""
Email delivery channel for OTP codes.

Uses the configured Django email backend (console in dev, SES in production).
"""
from typing import Any

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from apps.accounts.otp.channels.base import Channel


class EmailChannel(Channel):
    """Delivers OTP codes via email using Django's email backend."""

    def send(self, recipient: str, code: str, context: dict[str, Any]) -> None:
        """
        Send OTP code to the given email address.

        Args:
            recipient: Recipient email address.
            code:      Plaintext 6-digit OTP code.
            context:   Dict with at least {"purpose": str, "ttl_minutes": int}.
        """
        purpose = context.get("purpose", "verification")
        ttl_minutes = context.get("ttl_minutes", 5)

        subject = "Your Klikk verification code"

        message = render_to_string(
            "otp/email.txt",
            {
                "code": code,
                "purpose": purpose,
                "ttl_minutes": ttl_minutes,
            },
        )

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@klikk.co.za")

        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[recipient],
            fail_silently=False,
        )
