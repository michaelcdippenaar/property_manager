"""
Send email, SMS, and WhatsApp notifications.

**Gmail / SMTP:** see `apps/notifications/NOTIFICATIONS.md`.

Configure in Django settings (`config.settings.base`):
  EMAIL_* / DEFAULT_FROM_EMAIL — Django email (SMTP or console in dev)
  TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN — Twilio client
  TWILIO_SMS_FROM — E.164 sender for SMS (e.g. +27123456789)
  TWILIO_WHATSAPP_FROM — WhatsApp sender (e.g. whatsapp:+14155238886)

Phone numbers: E.164 preferred. Leading 0 is rewritten using
NOTIFICATIONS_DEFAULT_DIAL_CODE (default +27).
"""
from __future__ import annotations

import logging
import re
from typing import Sequence

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import DatabaseError

from .models import NotificationChannel, NotificationLog, NotificationStatus

logger = logging.getLogger(__name__)

_BODY_LOG_MAX = 10000


def normalize_phone_e164(phone: str) -> str:
    p = re.sub(r"[\s\-()]", "", (phone or "").strip())
    if not p:
        return ""
    dial = getattr(settings, "NOTIFICATIONS_DEFAULT_DIAL_CODE", "+27").strip()
    if not dial.startswith("+"):
        dial = f"+{dial}"
    if p.startswith("+"):
        return p
    if p.startswith("0"):
        return f"{dial}{p[1:]}"
    national = dial.lstrip("+")
    if p.startswith(national):
        return f"+{p}"
    return f"{dial}{p}"


def _twilio_client():
    sid = (getattr(settings, "TWILIO_ACCOUNT_SID", None) or "").strip()
    token = (getattr(settings, "TWILIO_AUTH_TOKEN", None) or "").strip()
    if not sid or not token:
        return None
    from twilio.rest import Client

    return Client(sid, token)


def _truncate_body(body: str) -> str:
    if len(body) <= _BODY_LOG_MAX:
        return body
    return body[: _BODY_LOG_MAX] + "…"


def _log(
    channel: str,
    to_address: str,
    subject: str,
    body: str,
    status: str,
    provider_message_id: str = "",
    error_message: str = "",
) -> NotificationLog | None:
    if not getattr(settings, "NOTIFICATIONS_ENABLE_LOG", True):
        return None
    try:
        return NotificationLog.objects.create(
            channel=channel,
            to_address=to_address[:320],
            subject=(subject or "")[:255],
            body=_truncate_body(body),
            status=status,
            provider_message_id=provider_message_id[:128] if provider_message_id else "",
            error_message=error_message[:2000] if error_message else "",
        )
    except DatabaseError as exc:
        logger.warning("NotificationLog write skipped: %s", exc)
        return None


def send_email(
    subject: str,
    body: str,
    to_emails: str | Sequence[str],
    *,
    html_body: str | None = None,
    from_email: str | None = None,
) -> bool:
    if isinstance(to_emails, str):
        recipients: list[str] = [to_emails]
    else:
        recipients = list(to_emails)
    if not recipients:
        logger.warning("send_email: no recipients")
        return False

    from_addr = from_email or getattr(
        settings, "DEFAULT_FROM_EMAIL", "noreply@localhost"
    )
    primary = recipients[0]
    msg = EmailMultiAlternatives(
        subject=subject,
        body=body or "",
        from_email=from_addr,
        to=[primary],
        cc=recipients[1:] if len(recipients) > 1 else None,
    )
    if html_body:
        msg.attach_alternative(html_body, "text/html")

    try:
        msg.send(fail_silently=False)
        for addr in recipients:
            _log(
                NotificationChannel.EMAIL,
                addr,
                subject,
                body or html_body or "",
                NotificationStatus.SENT,
            )
        return True
    except Exception as exc:
        logger.exception("send_email failed: %s", exc)
        for addr in recipients:
            _log(
                NotificationChannel.EMAIL,
                addr,
                subject,
                body or html_body or "",
                NotificationStatus.FAILED,
                error_message=str(exc),
            )
        return False


def send_sms(to_phone: str, body: str) -> bool:
    to_e164 = normalize_phone_e164(to_phone)
    if not to_e164:
        logger.warning("send_sms: empty phone")
        return False

    from_num = (getattr(settings, "TWILIO_SMS_FROM", None) or "").strip()
    client = _twilio_client()
    if not client or not from_num:
        logger.info(
            "[SMS stub] To: %s\n%s",
            to_e164,
            body,
        )
        reason = "Twilio not configured (missing SID/token or TWILIO_SMS_FROM)"
        _log(
            NotificationChannel.SMS,
            to_e164,
            "",
            body,
            NotificationStatus.FAILED,
            error_message=reason,
        )
        return False

    try:
        msg = client.messages.create(to=to_e164, from_=from_num, body=body)
        _log(
            NotificationChannel.SMS,
            to_e164,
            "",
            body,
            NotificationStatus.SENT,
            provider_message_id=getattr(msg, "sid", "") or "",
        )
        return True
    except Exception as exc:
        logger.exception("send_sms failed: %s", exc)
        _log(
            NotificationChannel.SMS,
            to_e164,
            "",
            body,
            NotificationStatus.FAILED,
            error_message=str(exc),
        )
        return False


def send_whatsapp(to_phone: str, body: str) -> bool:
    to_e164 = normalize_phone_e164(to_phone)
    if not to_e164:
        logger.warning("send_whatsapp: empty phone")
        return False

    wa_from = (getattr(settings, "TWILIO_WHATSAPP_FROM", None) or "").strip()
    if wa_from and not wa_from.lower().startswith("whatsapp:"):
        wa_from = f"whatsapp:{wa_from}"
    to_wa = (
        to_e164
        if to_e164.lower().startswith("whatsapp:")
        else f"whatsapp:{to_e164}"
    )

    client = _twilio_client()
    if not client or not wa_from:
        logger.info(
            "[WhatsApp stub] To: %s\n%s",
            to_wa,
            body,
        )
        reason = "Twilio not configured (missing SID/token or TWILIO_WHATSAPP_FROM)"
        _log(
            NotificationChannel.WHATSAPP,
            to_wa,
            "",
            body,
            NotificationStatus.FAILED,
            error_message=reason,
        )
        return False

    try:
        msg = client.messages.create(to=to_wa, from_=wa_from, body=body)
        _log(
            NotificationChannel.WHATSAPP,
            to_wa,
            "",
            body,
            NotificationStatus.SENT,
            provider_message_id=getattr(msg, "sid", "") or "",
        )
        return True
    except Exception as exc:
        logger.exception("send_whatsapp failed: %s", exc)
        _log(
            NotificationChannel.WHATSAPP,
            to_wa,
            "",
            body,
            NotificationStatus.FAILED,
            error_message=str(exc),
        )
        return False


def deliver_otp_sms(phone: str, code: str) -> bool:
    body = f"Your verification code is: {code}. It expires in 10 minutes."
    return send_sms(phone, body)


def notify_sms_and_whatsapp(to_phone: str, body: str) -> dict[str, bool]:
    """Send the same text via SMS and WhatsApp; returns per-channel results."""
    return {
        "sms": send_sms(to_phone, body),
        "whatsapp": send_whatsapp(to_phone, body),
    }
