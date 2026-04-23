"""
Unit tests for apps.accounts.otp.service — OTPService.

Covers:
  - send: happy path, rate limiting, channel delivery
  - verify: happy path, wrong code, TTL expiry, cross-purpose isolation,
    max attempts lock-out, replay prevention (consumed code)
"""
import hashlib
import hmac
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.otp.models import OTPCodeV1, OTPAuditLog
from apps.accounts.otp.service import (
    OTPMaxAttemptsExceeded,
    OTPRateLimitExceeded,
    OTPService,
    _generate_code,
    _hash_code,
    _get_ttl,
    _get_max_attempts,
    _get_max_issues_per_hour,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_user(email="otp@example.com", phone="+27820001111"):
    return User.objects.create_user(email=email, password="pw", phone=phone)


def _hash(user, purpose, code):
    return _hash_code(user.pk, purpose, code)


# ── _generate_code ────────────────────────────────────────────────────────────

class TestGenerateCode(TestCase):
    def test_is_six_digits(self):
        for _ in range(50):
            code = _generate_code()
            assert len(code) == 6
            assert code.isdigit()

    def test_uniqueness(self):
        codes = {_generate_code() for _ in range(200)}
        # With 1M possibilities, 200 draws should yield > 190 unique values.
        assert len(codes) > 150


# ── _hash_code ────────────────────────────────────────────────────────────────

class TestHashCode(TestCase):
    def test_deterministic(self):
        h1 = _hash_code(42, "registration", "123456")
        h2 = _hash_code(42, "registration", "123456")
        assert h1 == h2

    def test_different_user(self):
        assert _hash_code(1, "registration", "123456") != _hash_code(2, "registration", "123456")

    def test_different_purpose(self):
        assert _hash_code(1, "registration", "123456") != _hash_code(1, "password_reset", "123456")

    def test_different_code(self):
        assert _hash_code(1, "registration", "000000") != _hash_code(1, "registration", "111111")

    def test_is_hex_string(self):
        h = _hash_code(1, "test", "654321")
        assert len(h) == 64  # SHA-256 hex digest
        int(h, 16)  # should not raise


# ── OTPService.send ───────────────────────────────────────────────────────────

@override_settings(OTP_CHANNELS=["email"], OTP_MAX_ISSUES_PER_HOUR=5)
class TestOTPServiceSend(TestCase):
    def setUp(self):
        self.user = _make_user()

    @patch("apps.accounts.otp.channels.email.EmailChannel.send")
    def test_send_creates_otp_record(self, mock_send):
        OTPService.send(self.user, purpose="registration")

        otp = OTPCodeV1.objects.get(user=self.user, purpose="registration")
        assert otp.channel_used == "email"
        assert otp.consumed_at is None
        assert otp.attempt_count == 0
        assert otp.expires_at > timezone.now()

    @patch("apps.accounts.otp.channels.email.EmailChannel.send")
    def test_send_writes_audit_log(self, mock_send):
        OTPService.send(self.user, purpose="registration")

        log = OTPAuditLog.objects.get(user=self.user, purpose="registration")
        assert log.event_type == OTPAuditLog.EventType.ISSUED
        assert log.channel == "email"

    @patch("apps.accounts.otp.channels.email.EmailChannel.send")
    def test_send_calls_email_channel(self, mock_send):
        OTPService.send(self.user, purpose="registration")

        mock_send.assert_called_once()
        args = mock_send.call_args
        recipient = args[1].get("recipient") or args[0][0]
        assert recipient == self.user.email

    @patch("apps.accounts.otp.channels.email.EmailChannel.send")
    def test_send_code_not_stored_plaintext(self, mock_send):
        OTPService.send(self.user, purpose="registration")

        otp = OTPCodeV1.objects.get(user=self.user)
        # The code_hash field should not equal the plaintext code delivered.
        delivered_code = mock_send.call_args[1].get("code") or mock_send.call_args[0][1]
        assert otp.code_hash != delivered_code

    @override_settings(OTP_MAX_ISSUES_PER_HOUR=3)
    @patch("apps.accounts.otp.channels.email.EmailChannel.send")
    def test_rate_limit_exceeded(self, mock_send):
        for _ in range(3):
            OTPService.send(self.user, purpose="registration")

        with pytest.raises(OTPRateLimitExceeded):
            OTPService.send(self.user, purpose="registration")

    @override_settings(OTP_MAX_ISSUES_PER_HOUR=3)
    @patch("apps.accounts.otp.channels.email.EmailChannel.send")
    def test_rate_limit_writes_audit_log(self, mock_send):
        for _ in range(3):
            OTPService.send(self.user, purpose="registration")

        try:
            OTPService.send(self.user, purpose="registration")
        except OTPRateLimitExceeded:
            pass

        rate_logs = OTPAuditLog.objects.filter(
            user=self.user, event_type=OTPAuditLog.EventType.RATE_LIMITED
        )
        assert rate_logs.exists()

    @override_settings(OTP_CHANNELS=["sms", "email"])
    @patch("apps.accounts.otp.channels.email.EmailChannel.send")
    @patch("apps.accounts.otp.channels.sms.SMSChannel.send", side_effect=NotImplementedError("stub"))
    def test_fallback_to_next_channel(self, mock_sms, mock_email):
        OTPService.send(self.user, purpose="registration")

        otp = OTPCodeV1.objects.get(user=self.user, purpose="registration")
        assert otp.channel_used == "email"
        mock_email.assert_called_once()

    @override_settings(OTP_CODE_TTL_SECONDS=600)
    @patch("apps.accounts.otp.channels.email.EmailChannel.send")
    def test_ttl_applied_correctly(self, mock_send):
        before = timezone.now()
        OTPService.send(self.user, purpose="registration")
        after = timezone.now()

        otp = OTPCodeV1.objects.get(user=self.user)
        # expires_at should be ~10 min from now (600s).
        expected_min = before + timedelta(seconds=600)
        expected_max = after + timedelta(seconds=600)
        assert expected_min <= otp.expires_at <= expected_max


# ── OTPService.verify ─────────────────────────────────────────────────────────

@override_settings(OTP_CHANNELS=["email"], OTP_MAX_ATTEMPTS=3)
class TestOTPServiceVerify(TestCase):
    def setUp(self):
        self.user = _make_user("verify@example.com")

    def _create_otp(self, code="123456", purpose="registration", expired=False):
        now = timezone.now()
        delta = timedelta(minutes=-1) if expired else timedelta(minutes=5)
        otp = OTPCodeV1.objects.create(
            user=self.user,
            purpose=purpose,
            code_hash=_hash(self.user, purpose, code),
            channel_used="email",
            expires_at=now + delta,
        )
        return otp

    def test_verify_correct_code_returns_true(self):
        self._create_otp(code="654321")
        result = OTPService.verify(self.user, code="654321", purpose="registration")
        assert result is True

    def test_verify_correct_code_consumes_otp(self):
        otp = self._create_otp(code="654321")
        OTPService.verify(self.user, code="654321", purpose="registration")
        otp.refresh_from_db()
        assert otp.consumed_at is not None

    def test_verify_correct_code_writes_success_audit(self):
        self._create_otp(code="654321")
        OTPService.verify(self.user, code="654321", purpose="registration")
        log = OTPAuditLog.objects.get(
            user=self.user,
            purpose="registration",
            event_type=OTPAuditLog.EventType.VERIFY_SUCCESS,
        )
        assert log is not None

    def test_verify_wrong_code_returns_false(self):
        self._create_otp(code="111111")
        result = OTPService.verify(self.user, code="999999", purpose="registration")
        assert result is False

    def test_verify_wrong_code_increments_attempt_count(self):
        otp = self._create_otp(code="111111")
        OTPService.verify(self.user, code="999999", purpose="registration")
        otp.refresh_from_db()
        assert otp.attempt_count == 1

    def test_verify_wrong_code_writes_fail_audit(self):
        self._create_otp(code="111111")
        OTPService.verify(self.user, code="999999", purpose="registration")
        assert OTPAuditLog.objects.filter(
            user=self.user, event_type=OTPAuditLog.EventType.VERIFY_FAIL
        ).exists()

    def test_verify_expired_code_returns_false(self):
        self._create_otp(code="123456", expired=True)
        result = OTPService.verify(self.user, code="123456", purpose="registration")
        assert result is False

    def test_verify_expired_code_writes_fail_audit(self):
        self._create_otp(code="123456", expired=True)
        OTPService.verify(self.user, code="123456", purpose="registration")
        assert OTPAuditLog.objects.filter(
            user=self.user,
            purpose="registration",
            event_type=OTPAuditLog.EventType.VERIFY_FAIL,
        ).exists()

    def test_verify_consumed_code_returns_false(self):
        otp = self._create_otp(code="123456")
        # Consume the code first.
        OTPService.verify(self.user, code="123456", purpose="registration")
        # Try again — should fail (no active code).
        result = OTPService.verify(self.user, code="123456", purpose="registration")
        assert result is False

    # ── Cross-purpose isolation ───────────────────────────────────────────────

    def test_cross_purpose_code_rejected(self):
        """Code issued for 'registration' must not verify 'password_reset'."""
        self._create_otp(code="123456", purpose="registration")
        result = OTPService.verify(self.user, code="123456", purpose="password_reset")
        assert result is False

    def test_cross_purpose_correct_purpose_still_works(self):
        self._create_otp(code="123456", purpose="registration")
        self._create_otp(code="654321", purpose="password_reset")
        assert OTPService.verify(self.user, code="123456", purpose="registration") is True
        assert OTPService.verify(self.user, code="654321", purpose="password_reset") is True

    # ── Max attempts / lockout ────────────────────────────────────────────────

    @override_settings(OTP_MAX_ATTEMPTS=3)
    def test_max_attempts_lockout_raises(self):
        self._create_otp(code="123456")
        OTPService.verify(self.user, code="000000", purpose="registration")
        OTPService.verify(self.user, code="000000", purpose="registration")
        # Third wrong attempt locks the code.
        with pytest.raises(OTPMaxAttemptsExceeded):
            OTPService.verify(self.user, code="000000", purpose="registration")

    @override_settings(OTP_MAX_ATTEMPTS=3)
    def test_max_attempts_lockout_writes_locked_audit(self):
        self._create_otp(code="123456")
        OTPService.verify(self.user, code="000000", purpose="registration")
        OTPService.verify(self.user, code="000000", purpose="registration")
        try:
            OTPService.verify(self.user, code="000000", purpose="registration")
        except OTPMaxAttemptsExceeded:
            pass
        assert OTPAuditLog.objects.filter(
            user=self.user, event_type=OTPAuditLog.EventType.LOCKED
        ).exists()

    @override_settings(OTP_MAX_ATTEMPTS=3)
    def test_already_locked_code_raises_on_next_attempt(self):
        otp = self._create_otp(code="123456")
        otp.attempt_count = 3
        otp.save(update_fields=["attempt_count"])

        with pytest.raises(OTPMaxAttemptsExceeded):
            OTPService.verify(self.user, code="123456", purpose="registration")

    # ── Settings helpers ──────────────────────────────────────────────────────

    @override_settings(OTP_CODE_TTL_SECONDS=900)
    def test_get_ttl_reads_setting(self):
        assert _get_ttl() == 900

    @override_settings(OTP_MAX_ATTEMPTS=5)
    def test_get_max_attempts_reads_setting(self):
        assert _get_max_attempts() == 5

    @override_settings(OTP_MAX_ISSUES_PER_HOUR=10)
    def test_get_max_issues_per_hour_reads_setting(self):
        assert _get_max_issues_per_hour() == 10
