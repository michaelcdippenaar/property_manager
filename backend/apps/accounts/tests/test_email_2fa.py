"""
Tests for email OTP 2FA endpoints — RNT-SEC-050

Covers:
  Email2FASendView  (POST /auth/2fa/email-send/)
    - happy path: OTP sent, audit event written
    - missing two_fa_token → 400
    - invalid two_fa_token → 401
    - OTP rate limit hit → 429 + 2fa_email_failed audit

  Email2FAVerifyView  (POST /auth/2fa/email-verify/)
    - happy path: correct code → full tokens returned + 2fa_email_verified audit
    - bad code → 400 + 2fa_email_failed audit
    - expired code → 400 + 2fa_email_failed audit
    - missing fields → 400
    - max attempts exceeded → 400 + 2fa_email_failed audit

  LoginView branch
    - two_fa_method=email + TOTP enrolled → next=email-verify hint returned
    - two_fa_method=totp + TOTP enrolled → next=totp (unchanged)
"""
from datetime import timedelta
from unittest.mock import patch, MagicMock

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User, AuthAuditLog, UserTOTP
from apps.accounts.otp.models import OTPCodeV1, OTPAuditLog
from apps.accounts.otp.service import _hash_code
from apps.accounts.totp_views import _make_two_fa_token


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def email_user(db):
    user = User.objects.create_user(
        email="emailotp@test.com",
        password="SecurePass123!",
        two_fa_method="email",
    )
    return user


@pytest.fixture
def totp_user(db):
    user = User.objects.create_user(
        email="totpuser@test.com",
        password="SecurePass123!",
        two_fa_method="totp",
    )
    return user


@pytest.fixture
def enrolled_totp_user(db):
    """User with TOTP enrolled (is_active=True) and two_fa_method=totp."""
    user = User.objects.create_user(
        email="totpenrolled@test.com",
        password="SecurePass123!",
        role=User.Role.ADMIN,
        two_fa_method="totp",
    )
    UserTOTP.objects.create(user=user, secret="JBSWY3DPEHPK3PXP", is_active=True)
    return user


@pytest.fixture
def enrolled_email_user(db):
    """User with TOTP enrolled but two_fa_method=email (email OTP login)."""
    user = User.objects.create_user(
        email="emailenrolled@test.com",
        password="SecurePass123!",
        role=User.Role.ADMIN,
        two_fa_method="email",
    )
    # TOTP enrollment must still be present for the 2FA gate to fire in LoginView.
    UserTOTP.objects.create(user=user, secret="JBSWY3DPEHPK3PXP", is_active=True)
    return user


def _make_valid_otp(user, purpose="login_2fa", code="123456", offset_seconds=0):
    """Create an unconsumed, unexpired OTPCodeV1 row for `user`."""
    ttl = 300
    code_hash = _hash_code(user.pk, purpose, code)
    otp = OTPCodeV1.objects.create(
        user=user,
        purpose=purpose,
        code_hash=code_hash,
        channel_used="email",
        expires_at=timezone.now() + timedelta(seconds=ttl + offset_seconds),
    )
    return otp


def _make_expired_otp(user, purpose="login_2fa", code="654321"):
    """Create an expired OTPCodeV1 row for `user`."""
    code_hash = _hash_code(user.pk, purpose, code)
    otp = OTPCodeV1.objects.create(
        user=user,
        purpose=purpose,
        code_hash=code_hash,
        channel_used="email",
        expires_at=timezone.now() - timedelta(seconds=1),
    )
    return otp


# ── Email2FASendView tests ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestEmail2FASendView:
    url = "/api/v1/auth/2fa/email-send/"

    def test_happy_path_sends_otp(self, client, email_user):
        token = _make_two_fa_token(email_user)
        with patch("apps.accounts.otp.service.OTPService.send") as mock_send:
            resp = client.post(self.url, {"two_fa_token": token}, format="json")
        assert resp.status_code == 200
        mock_send.assert_called_once_with(email_user, purpose="login_2fa")

    def test_audit_event_written_on_success(self, client, email_user):
        token = _make_two_fa_token(email_user)
        with patch("apps.accounts.otp.service.OTPService.send"):
            client.post(self.url, {"two_fa_token": token}, format="json")
        assert AuthAuditLog.objects.filter(user=email_user, event_type="2fa_email_sent").exists()

    def test_missing_two_fa_token(self, client):
        resp = client.post(self.url, {}, format="json")
        assert resp.status_code == 400

    def test_invalid_two_fa_token(self, client):
        resp = client.post(self.url, {"two_fa_token": "not.a.valid.jwt"}, format="json")
        assert resp.status_code == 401

    def test_rate_limit_returns_429(self, client, email_user):
        from apps.accounts.otp.service import OTPRateLimitExceeded
        token = _make_two_fa_token(email_user)
        with patch(
            "apps.accounts.otp.service.OTPService.send",
            side_effect=OTPRateLimitExceeded("rate limited"),
        ):
            resp = client.post(self.url, {"two_fa_token": token}, format="json")
        assert resp.status_code == 429
        assert AuthAuditLog.objects.filter(
            user=email_user, event_type="2fa_email_failed"
        ).exists()


# ── Email2FAVerifyView tests ───────────────────────────────────────────────────

@pytest.mark.django_db
class TestEmail2FAVerifyView:
    url = "/api/v1/auth/2fa/email-verify/"

    def test_happy_path_returns_tokens(self, client, email_user):
        token = _make_two_fa_token(email_user)
        code = "112233"
        _make_valid_otp(email_user, code=code)
        resp = client.post(
            self.url,
            {"two_fa_token": token, "code": code},
            format="json",
        )
        assert resp.status_code == 200
        assert "access" in resp.data
        assert "refresh" in resp.data

    def test_audit_event_written_on_success(self, client, email_user):
        token = _make_two_fa_token(email_user)
        code = "998877"
        _make_valid_otp(email_user, code=code)
        client.post(self.url, {"two_fa_token": token, "code": code}, format="json")
        assert AuthAuditLog.objects.filter(
            user=email_user, event_type="2fa_email_verified"
        ).exists()

    def test_bad_code_returns_400(self, client, email_user):
        token = _make_two_fa_token(email_user)
        _make_valid_otp(email_user, code="111111")
        resp = client.post(
            self.url,
            {"two_fa_token": token, "code": "999999"},
            format="json",
        )
        assert resp.status_code == 400
        assert AuthAuditLog.objects.filter(
            user=email_user, event_type="2fa_email_failed"
        ).exists()

    def test_expired_code_returns_400(self, client, email_user):
        token = _make_two_fa_token(email_user)
        _make_expired_otp(email_user, code="654321")
        resp = client.post(
            self.url,
            {"two_fa_token": token, "code": "654321"},
            format="json",
        )
        assert resp.status_code == 400

    def test_missing_fields_returns_400(self, client):
        resp = client.post(self.url, {}, format="json")
        assert resp.status_code == 400

    def test_max_attempts_exceeded_returns_400(self, client, email_user):
        from apps.accounts.otp.service import OTPMaxAttemptsExceeded
        token = _make_two_fa_token(email_user)
        with patch(
            "apps.accounts.otp.service.OTPService.verify",
            side_effect=OTPMaxAttemptsExceeded("locked"),
        ):
            resp = client.post(
                self.url,
                {"two_fa_token": token, "code": "000000"},
                format="json",
            )
        assert resp.status_code == 400
        assert AuthAuditLog.objects.filter(
            user=email_user, event_type="2fa_email_failed"
        ).exists()

    def test_invalid_two_fa_token_returns_401(self, client):
        resp = client.post(
            self.url,
            {"two_fa_token": "bad.token.here", "code": "123456"},
            format="json",
        )
        assert resp.status_code == 401


# ── LoginView branch tests ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestLoginViewEmailBranch:
    url = "/api/v1/auth/login/"

    def test_email_method_returns_email_verify_hint(self, client, enrolled_email_user):
        resp = client.post(
            self.url,
            {"email": enrolled_email_user.email, "password": "SecurePass123!"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data.get("two_fa_required") is True
        assert resp.data.get("next") == "email-verify"
        assert "two_fa_token" in resp.data

    def test_totp_method_returns_totp_hint(self, client, enrolled_totp_user):
        resp = client.post(
            self.url,
            {"email": enrolled_totp_user.email, "password": "SecurePass123!"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data.get("two_fa_required") is True
        assert resp.data.get("next") == "totp"
        assert "two_fa_token" in resp.data
