"""
Security tests for authentication hardening endpoints.

Covers:
- Role escalation prevention on /auth/me/
- Account lockout after failed login attempts
- Change password validation
- Logout and token blacklisting
- Password reset flow (request + confirm)
"""
import pytest
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.accounts.models import LoginAttempt
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


# ---------------------------------------------------------------------------
# P0 — Role Escalation Prevention
# ---------------------------------------------------------------------------


class RoleEscalationPreventionTests(TremlyAPITestCase):
    """Ensure PATCH /auth/me/ cannot modify protected fields (role, email)."""

    url = reverse("auth-me")

    def setUp(self):
        self.agent = self.create_agent(email="agent@test.com", first_name="Original")

    def test_patch_role_to_admin_is_ignored(self):
        """Attempting to escalate role via PATCH must leave the role unchanged."""
        self.authenticate(self.agent)
        resp = self.client.patch(self.url, {"role": "admin"})
        self.assertEqual(resp.status_code, 200)
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.role, "agent")

    def test_patch_email_is_ignored(self):
        """Attempting to change email via PATCH must leave the email unchanged."""
        self.authenticate(self.agent)
        resp = self.client.patch(self.url, {"email": "hacker@x.com"})
        self.assertEqual(resp.status_code, 200)
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.email, "agent@test.com")

    def test_patch_first_name_works(self):
        """Writable fields like first_name should update normally."""
        self.authenticate(self.agent)
        resp = self.client.patch(self.url, {"first_name": "New"})
        self.assertEqual(resp.status_code, 200)
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.first_name, "New")

    def test_patch_unauthenticated_returns_401(self):
        resp = self.client.patch(self.url, {"first_name": "Nope"})
        self.assertEqual(resp.status_code, 401)


# ---------------------------------------------------------------------------
# P5 — Account Lockout
# ---------------------------------------------------------------------------


class AccountLockoutTests(TremlyAPITestCase):
    """Account lockout after repeated failed login attempts."""

    url = reverse("auth-login")

    def setUp(self):
        self.user = self.create_user(email="lockout@test.com", password="correctpass123")

    def test_lockout_after_5_failures(self):
        """After 5 failed LoginAttempt records, the 6th login returns 429."""
        # Seed 5 failed attempts directly in the DB
        for _ in range(5):
            LoginAttempt.objects.create(
                email="lockout@test.com",
                ip_address="127.0.0.1",
                succeeded=False,
            )

        resp = self.client.post(self.url, {
            "email": "lockout@test.com",
            "password": "correctpass123",
        })
        self.assertEqual(resp.status_code, 429)

    def test_successful_login_after_fewer_than_threshold_failures(self):
        """3 failures followed by a success — subsequent login still works."""
        for _ in range(3):
            LoginAttempt.objects.create(
                email="lockout@test.com",
                ip_address="127.0.0.1",
                succeeded=False,
            )

        # Successful login (resets the failure window via a success record)
        resp = self.client.post(self.url, {
            "email": "lockout@test.com",
            "password": "correctpass123",
        })
        self.assertEqual(resp.status_code, 200)

        # Another login should still work (total failures still < threshold)
        resp = self.client.post(self.url, {
            "email": "lockout@test.com",
            "password": "correctpass123",
        })
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# P5 — Change Password
# ---------------------------------------------------------------------------


class ChangePasswordTests(TremlyAPITestCase):
    """POST /auth/change-password/ validation and security."""

    url = reverse("auth-change-password")

    def setUp(self):
        self.user = self.create_user(email="chpwd@test.com", password="oldpass12345")
        self.authenticate(self.user)

    def test_change_password_success(self):
        resp = self.client.post(self.url, {
            "current_password": "oldpass12345",
            "new_password": "newstrongpass789",
        })
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newstrongpass789"))

    def test_change_password_wrong_current(self):
        resp = self.client.post(self.url, {
            "current_password": "wrongcurrent",
            "new_password": "newstrongpass789",
        })
        self.assertEqual(resp.status_code, 400)

    def test_change_password_weak_new_password(self):
        resp = self.client.post(self.url, {
            "current_password": "oldpass12345",
            "new_password": "123",
        })
        self.assertEqual(resp.status_code, 400)


# ---------------------------------------------------------------------------
# P5 — Logout
# ---------------------------------------------------------------------------


class LogoutTests(TremlyAPITestCase):
    """POST /auth/logout/ blacklists refresh token."""

    url = reverse("auth-logout")

    def setUp(self):
        self.user = self.create_user(email="logout@test.com")

    def test_logout_with_refresh_token(self):
        """Posting a valid refresh token returns 204 and blacklists the token."""
        tokens = self.get_tokens(self.user)
        self.authenticate(self.user)
        resp = self.client.post(self.url, {"refresh": tokens["refresh"]})
        self.assertEqual(resp.status_code, 204)

        # The refresh token should now be blacklisted — refreshing it should fail
        refresh_url = reverse("token-refresh")
        resp = self.client.post(refresh_url, {"refresh": tokens["refresh"]})
        self.assertEqual(resp.status_code, 401)

    def test_logout_without_refresh_token(self):
        """Posting without a refresh token still returns 204 (graceful)."""
        self.authenticate(self.user)
        resp = self.client.post(self.url, {})
        self.assertEqual(resp.status_code, 204)


# ---------------------------------------------------------------------------
# P5 — Password Reset
# ---------------------------------------------------------------------------


class PasswordResetRequestTests(TremlyAPITestCase):
    """POST /auth/password-reset/ — request a reset link."""

    url = reverse("auth-password-reset")

    def setUp(self):
        self.user = self.create_user(email="reset@test.com", password="oldpass12345")

    def test_valid_email_returns_200(self):
        resp = self.client.post(self.url, {"email": "reset@test.com"})
        self.assertEqual(resp.status_code, 200)

    def test_unknown_email_returns_200_no_info_leak(self):
        """Unknown emails must return the same 200 to prevent enumeration."""
        resp = self.client.post(self.url, {"email": "nobody@nowhere.com"})
        self.assertEqual(resp.status_code, 200)


class PasswordResetConfirmTests(TremlyAPITestCase):
    """POST /auth/password-reset/confirm/ — confirm a reset with uid+token."""

    url = reverse("auth-password-reset-confirm")

    def setUp(self):
        self.user = self.create_user(email="resetconfirm@test.com", password="oldpass12345")
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = default_token_generator.make_token(self.user)

    def test_valid_token_resets_password(self):
        resp = self.client.post(self.url, {
            "uid": self.uid,
            "token": self.token,
            "new_password": "brandnewpass456",
        })
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("brandnewpass456"))

    def test_invalid_token_returns_400(self):
        resp = self.client.post(self.url, {
            "uid": self.uid,
            "token": "bad-token-value",
            "new_password": "brandnewpass456",
        })
        self.assertEqual(resp.status_code, 400)
