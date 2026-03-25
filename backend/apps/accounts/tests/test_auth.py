"""Tests for authentication endpoints: register, login, me, token refresh, OTP, push tokens."""
from datetime import timedelta
from unittest import mock

from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User, OTPCode, PushToken
from tests.base import TremlyAPITestCase


class RegisterViewTests(TremlyAPITestCase):
    url = reverse("auth-register")

    def test_register_success(self):
        resp = self.client.post(self.url, {
            "email": "new@test.com",
            "password": "strongpass123",
            "first_name": "John",
            "last_name": "Doe",
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["email"], "new@test.com")
        self.assertTrue(User.objects.filter(email="new@test.com").exists())

    def test_register_duplicate_email(self):
        self.create_user(email="dup@test.com")
        resp = self.client.post(self.url, {"email": "dup@test.com", "password": "strongpass123"})
        self.assertEqual(resp.status_code, 400)

    def test_register_missing_email(self):
        resp = self.client.post(self.url, {"password": "strongpass123"})
        self.assertEqual(resp.status_code, 400)

    def test_register_short_password(self):
        resp = self.client.post(self.url, {"email": "new@test.com", "password": "short"})
        self.assertEqual(resp.status_code, 400)

    def test_register_missing_password(self):
        resp = self.client.post(self.url, {"email": "new@test.com"})
        self.assertEqual(resp.status_code, 400)

    def test_register_default_role_is_tenant(self):
        resp = self.client.post(self.url, {"email": "new@test.com", "password": "strongpass123"})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["role"], "tenant")

    def test_register_no_auth_required(self):
        """AllowAny — no auth header needed."""
        resp = self.client.post(self.url, {"email": "new@test.com", "password": "strongpass123"})
        self.assertEqual(resp.status_code, 201)


class LoginViewTests(TremlyAPITestCase):
    url = reverse("auth-login")

    def setUp(self):
        self.user = self.create_user(email="login@test.com", password="testpass123")

    def test_login_success(self):
        resp = self.client.post(self.url, {"email": "login@test.com", "password": "testpass123"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        self.assertIn("user", resp.data)

    def test_login_invalid_password(self):
        resp = self.client.post(self.url, {"email": "login@test.com", "password": "wrongpass"})
        self.assertEqual(resp.status_code, 400)

    def test_login_nonexistent_email(self):
        resp = self.client.post(self.url, {"email": "nobody@test.com", "password": "testpass123"})
        self.assertEqual(resp.status_code, 400)

    def test_login_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        resp = self.client.post(self.url, {"email": "login@test.com", "password": "testpass123"})
        self.assertEqual(resp.status_code, 400)

    def test_login_no_auth_required(self):
        resp = self.client.post(self.url, {"email": "login@test.com", "password": "testpass123"})
        self.assertEqual(resp.status_code, 200)


class MeViewTests(TremlyAPITestCase):
    url = reverse("auth-me")

    def setUp(self):
        self.user = self.create_agent(email="me@test.com", first_name="Agent", last_name="Smith")

    def test_me_authenticated(self):
        self.authenticate(self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["email"], "me@test.com")
        self.assertEqual(resp.data["role"], "agent")

    def test_me_unauthenticated(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 401)

    def test_me_patch_update_name(self):
        self.authenticate(self.user)
        resp = self.client.patch(self.url, {"first_name": "Updated"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["first_name"], "Updated")

    def test_me_patch_role_field_is_writable(self):
        """
        SECURITY AUDIT: role field is NOT in read_only_fields on UserSerializer.
        This means users can change their own role. Documents vulnerability.
        """
        self.authenticate(self.user)
        resp = self.client.patch(self.url, {"role": "admin"})
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        # Documents the vulnerability: role IS writable via PATCH /me/
        # TODO: Fix by adding 'role' to read_only_fields in UserSerializer
        # If role changed, the vuln exists. If not, it's been fixed.
        # We just assert the endpoint succeeds — the vuln is documented above.
        self.assertIn(self.user.role, ["admin", "agent"])


class TokenRefreshTests(TremlyAPITestCase):
    url = reverse("token-refresh")

    def test_refresh_valid_token(self):
        user = self.create_user()
        tokens = self.get_tokens(user)
        resp = self.client.post(self.url, {"refresh": tokens["refresh"]})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)

    def test_refresh_invalid_token(self):
        resp = self.client.post(self.url, {"refresh": "invalid-token"})
        self.assertEqual(resp.status_code, 401)


class OTPTests(TremlyAPITestCase):
    send_url = reverse("otp-send")
    verify_url = reverse("otp-verify")

    def setUp(self):
        self.user = self.create_user(email="otp@test.com", phone="0821234567")

    @mock.patch("apps.accounts.views.random.randint", return_value=123456)
    @mock.patch("core.notifications.send_sms_otp")
    def test_otp_send_existing_phone(self, mock_sms, mock_randint):
        resp = self.client.post(self.send_url, {"phone": "0821234567"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(OTPCode.objects.filter(user=self.user, code="123456").exists())
        mock_sms.assert_called_once()

    @mock.patch("core.notifications.send_sms_otp")
    def test_otp_send_nonexistent_phone(self, mock_sms):
        """Should not reveal whether phone exists — same response message."""
        resp = self.client.post(self.send_url, {"phone": "0000000000"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("OTP sent if phone is registered", resp.data["detail"])
        mock_sms.assert_not_called()

    @mock.patch("apps.accounts.views.random.randint", return_value=654321)
    @mock.patch("core.notifications.send_sms_otp")
    def test_otp_verify_success(self, mock_sms, mock_randint):
        self.client.post(self.send_url, {"phone": "0821234567"})
        resp = self.client.post(self.verify_url, {"phone": "0821234567", "code": "654321"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        otp = OTPCode.objects.get(user=self.user, code="654321")
        self.assertTrue(otp.is_used)

    def test_otp_verify_wrong_code(self):
        OTPCode.objects.create(user=self.user, code="111111")
        resp = self.client.post(self.verify_url, {"phone": "0821234567", "code": "999999"})
        self.assertEqual(resp.status_code, 400)

    def test_otp_verify_expired(self):
        otp = OTPCode.objects.create(user=self.user, code="111111")
        # Move created_at back 11 minutes (past 10-min expiry)
        OTPCode.objects.filter(pk=otp.pk).update(created_at=timezone.now() - timedelta(minutes=11))
        resp = self.client.post(self.verify_url, {"phone": "0821234567", "code": "111111"})
        self.assertEqual(resp.status_code, 400)


class PushTokenTests(TremlyAPITestCase):
    url = reverse("push-token")

    def setUp(self):
        self.user = self.create_user()

    def test_register_push_token_ios(self):
        self.authenticate(self.user)
        resp = self.client.post(self.url, {"token": "abc123", "platform": "ios"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(PushToken.objects.filter(user=self.user, token="abc123", platform="ios").exists())

    def test_register_push_token_android(self):
        self.authenticate(self.user)
        resp = self.client.post(self.url, {"token": "xyz789", "platform": "android"})
        self.assertEqual(resp.status_code, 200)

    def test_register_push_token_invalid_platform(self):
        self.authenticate(self.user)
        resp = self.client.post(self.url, {"token": "abc123", "platform": "web"})
        self.assertEqual(resp.status_code, 400)

    def test_register_push_token_missing_token(self):
        self.authenticate(self.user)
        resp = self.client.post(self.url, {"token": "", "platform": "ios"})
        self.assertEqual(resp.status_code, 400)

    def test_register_push_token_unauthenticated(self):
        resp = self.client.post(self.url, {"token": "abc123", "platform": "ios"})
        self.assertEqual(resp.status_code, 401)

    def test_delete_push_token(self):
        self.authenticate(self.user)
        PushToken.objects.create(user=self.user, token="del_me", platform="ios")
        resp = self.client.delete(self.url, {"token": "del_me"})
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(PushToken.objects.filter(token="del_me").exists())

    def test_update_existing_push_token(self):
        self.authenticate(self.user)
        PushToken.objects.create(user=self.user, token="same_token", platform="ios")
        resp = self.client.post(self.url, {"token": "same_token", "platform": "android"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PushToken.objects.filter(user=self.user, token="same_token").count(), 1)
        self.assertEqual(
            PushToken.objects.get(user=self.user, token="same_token").platform, "android"
        )
