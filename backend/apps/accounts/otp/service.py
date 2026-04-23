"""
OTPService — channel-abstracted OTP issue/verify for Klikk Rentals v1.

Design decisions:
  - Codes hashed with HMAC-SHA256 keyed on (user PK + purpose). Plaintext never stored.
  - Channel selection driven by settings.OTP_CHANNELS (ordered list, first-working wins).
  - Rate limits: 5 issues per user per hour; 3 verify attempts per code.
  - Per-purpose scoping: code issued for "registration" cannot verify "password_reset".
  - Audit trail: OTPAuditLog row on every send / verify-success / verify-fail.
"""
import hashlib
import hmac
import secrets
from datetime import timedelta
from typing import TYPE_CHECKING

from django.conf import settings
from django.utils import timezone

if TYPE_CHECKING:
    from apps.accounts.models import User


# ── Constants (overrideable via settings) ────────────────────────────────────

def _get_ttl() -> int:
    return getattr(settings, "OTP_CODE_TTL_SECONDS", 300)  # 5 min


def _get_max_attempts() -> int:
    return getattr(settings, "OTP_MAX_ATTEMPTS", 3)


def _get_max_issues_per_hour() -> int:
    return getattr(settings, "OTP_MAX_ISSUES_PER_HOUR", 5)


def _get_channels() -> list[str]:
    return getattr(settings, "OTP_CHANNELS", ["email"])


# ── Exceptions ────────────────────────────────────────────────────────────────

class OTPRateLimitExceeded(Exception):
    """Raised when a user has exceeded the hourly OTP issue limit."""


class OTPMaxAttemptsExceeded(Exception):
    """Raised when verify attempts on the active code are exhausted."""


# ── Internal helpers ──────────────────────────────────────────────────────────

def _generate_code() -> str:
    """Return a cryptographically random 6-digit numeric string."""
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_code(user_pk: int, purpose: str, code: str) -> str:
    """
    HMAC-SHA256 of the plaintext code, keyed by (user_pk + purpose).
    Provides per-user, per-purpose domain separation so an attacker who
    extracts one hash cannot reuse it for a different user or purpose.
    """
    key = f"{user_pk}:{purpose}:{settings.SECRET_KEY}".encode()
    return hmac.new(key, code.encode(), hashlib.sha256).hexdigest()


def _get_channel(name: str):
    """Lazy-import and instantiate a channel by name."""
    if name == "email":
        from apps.accounts.otp.channels.email import EmailChannel
        return EmailChannel()
    if name == "sms":
        from apps.accounts.otp.channels.sms import SMSChannel
        return SMSChannel()
    raise ValueError(f"Unknown OTP channel: {name!r}")


# ── Service ───────────────────────────────────────────────────────────────────

class OTPService:
    """
    Main entry point for OTP operations.

    Usage:
        OTPService.send(user, purpose="registration")
        success = OTPService.verify(user, code="123456", purpose="registration")
    """

    @staticmethod
    def send(user: "User", purpose: str) -> None:
        """
        Issue a new OTP code for `user` and `purpose`, then deliver it
        via the first successfully working channel in settings.OTP_CHANNELS.

        Raises:
            OTPRateLimitExceeded: when hourly issue limit is hit.
        """
        from apps.accounts.otp.models import OTPCodeV1 as OTPCode, OTPAuditLog

        now = timezone.now()
        hour_ago = now - timedelta(hours=1)

        # Rate-limit: max N issues per user per hour (across all purposes).
        recent_count = OTPCode.objects.filter(
            user=user,
            created_at__gte=hour_ago,
        ).count()

        if recent_count >= _get_max_issues_per_hour():
            OTPAuditLog.objects.create(
                user=user,
                purpose=purpose,
                event_type=OTPAuditLog.EventType.RATE_LIMITED,
                metadata={"recent_count": recent_count},
            )
            raise OTPRateLimitExceeded(
                f"OTP rate limit exceeded for user {user.pk} "
                f"({recent_count} codes issued in the last hour)."
            )

        plaintext = _generate_code()
        code_hash = _hash_code(user.pk, purpose, plaintext)
        ttl_seconds = _get_ttl()
        expires_at = now + timedelta(seconds=ttl_seconds)

        # Try channels in order — first one that doesn't raise wins.
        channel_names = _get_channels()
        used_channel: str | None = None
        last_error: Exception | None = None

        for name in channel_names:
            try:
                ch = _get_channel(name)
                recipient = _pick_recipient(user, name)
                ch.send(
                    recipient=recipient,
                    code=plaintext,
                    context={
                        "purpose": purpose,
                        "ttl_minutes": ttl_seconds // 60,
                    },
                )
                used_channel = name
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue

        if used_channel is None:
            raise RuntimeError(
                f"All OTP channels failed to deliver code for user {user.pk}. "
                f"Last error: {last_error}"
            ) from last_error

        otp_code = OTPCode.objects.create(
            user=user,
            purpose=purpose,
            code_hash=code_hash,
            channel_used=used_channel,
            expires_at=expires_at,
        )

        OTPAuditLog.objects.create(
            user=user,
            purpose=purpose,
            event_type=OTPAuditLog.EventType.ISSUED,
            channel=used_channel,
            metadata={"otp_code_id": otp_code.pk},
        )

    @staticmethod
    def verify(user: "User", code: str, purpose: str) -> bool:
        """
        Verify an OTP code for `user` and `purpose`.

        Returns True on success, False on failure.

        Side effects:
          - Increments attempt_count on failure.
          - Sets consumed_at on success.
          - Writes an OTPAuditLog row on every call.

        Raises:
            OTPMaxAttemptsExceeded: when the active code's attempt limit is hit.
        """
        from apps.accounts.otp.models import OTPCodeV1 as OTPCode, OTPAuditLog

        now = timezone.now()

        # Find the most recent unconsumed, unexpired code for this user+purpose.
        otp = (
            OTPCode.objects.filter(
                user=user,
                purpose=purpose,
                consumed_at__isnull=True,
                expires_at__gt=now,
            )
            .order_by("-created_at")
            .first()
        )

        if otp is None:
            # Could be expired, already consumed, or wrong purpose — all fail.
            OTPAuditLog.objects.create(
                user=user,
                purpose=purpose,
                event_type=OTPAuditLog.EventType.VERIFY_FAIL,
                metadata={"reason": "no_active_code"},
            )
            return False

        # Check if already locked (too many bad attempts).
        if otp.is_locked:
            OTPAuditLog.objects.create(
                user=user,
                purpose=purpose,
                event_type=OTPAuditLog.EventType.LOCKED,
                metadata={"otp_code_id": otp.pk},
            )
            raise OTPMaxAttemptsExceeded(
                f"OTP code for user {user.pk} / purpose '{purpose}' is locked "
                f"after {otp.attempt_count} failed attempts. Request a new code."
            )

        expected_hash = _hash_code(user.pk, purpose, code)

        if not hmac.compare_digest(otp.code_hash, expected_hash):
            otp.attempt_count += 1
            otp.save(update_fields=["attempt_count"])

            event = (
                OTPAuditLog.EventType.LOCKED
                if otp.is_locked
                else OTPAuditLog.EventType.VERIFY_FAIL
            )
            OTPAuditLog.objects.create(
                user=user,
                purpose=purpose,
                event_type=event,
                channel=otp.channel_used,
                metadata={"otp_code_id": otp.pk, "attempt_count": otp.attempt_count},
            )

            if otp.is_locked:
                raise OTPMaxAttemptsExceeded(
                    f"OTP code for user {user.pk} / purpose '{purpose}' is now locked "
                    f"after {otp.attempt_count} failed attempts. Request a new code."
                )
            return False

        # Success — consume the code.
        otp.consumed_at = now
        otp.save(update_fields=["consumed_at"])

        OTPAuditLog.objects.create(
            user=user,
            purpose=purpose,
            event_type=OTPAuditLog.EventType.VERIFY_SUCCESS,
            channel=otp.channel_used,
            metadata={"otp_code_id": otp.pk},
        )
        return True


def _pick_recipient(user: "User", channel: str) -> str:
    """Return the delivery address for the given channel."""
    if channel == "email":
        return user.email
    if channel == "sms":
        phone = getattr(user, "phone", "")
        if not phone:
            raise ValueError(f"User {user.pk} has no phone number for SMS channel.")
        return phone
    raise ValueError(f"Unknown channel {channel!r}")
