"""
Tests for the Google OAuth sign-in endpoint.

Mocks google.oauth2.id_token.verify_oauth2_token so no real Google calls are made.

Covers:
  - Missing credential → 400
  - Client ID not configured → 503
  - Invalid Google token → 400
  - Email not verified → 400
  - New email → user created with unusable password + JWT tokens returned
  - Existing email → returns JWT tokens (no duplicate account)
  - Inactive existing user → 403
  - Audit log entry written

Source file under test: apps/accounts/oauth_views.py :: GoogleAuthView
"""
from unittest import mock

import pytest
from django.test import override_settings
from django.urls import reverse

from apps.accounts.models import Agency, AuthAuditLog, User
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]

GOOGLE_VERIFY_PATH = "apps.accounts.oauth_views.id_token.verify_oauth2_token"


@override_settings(GOOGLE_OAUTH_CLIENT_ID="test-client-id.apps.googleusercontent.com")
class GoogleAuthViewTests(TremlyAPITestCase):
    url = reverse("auth-google")

    def test_missing_credential_returns_400(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.data)

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="")
    def test_missing_client_id_returns_503(self):
        resp = self.client.post(self.url, {"credential": "fake-jwt"}, format="json")
        self.assertEqual(resp.status_code, 503)

    @mock.patch(GOOGLE_VERIFY_PATH, side_effect=ValueError("bad token"))
    def test_invalid_token_returns_400(self, _mock_verify):
        resp = self.client.post(self.url, {"credential": "invalid-jwt"}, format="json")
        self.assertEqual(resp.status_code, 400)

    @mock.patch(GOOGLE_VERIFY_PATH, return_value={
        "email": "unverified@example.com",
        "email_verified": False,
    })
    def test_email_not_verified_returns_400(self, _mock_verify):
        resp = self.client.post(self.url, {"credential": "fake-jwt"}, format="json")
        self.assertEqual(resp.status_code, 400)

    @mock.patch(GOOGLE_VERIFY_PATH, return_value={
        "email": "newuser@example.com",
        "email_verified": True,
        "given_name": "New",
        "family_name": "User",
    })
    def test_new_email_creates_user_and_returns_tokens(self, _mock_verify):
        self.assertFalse(User.objects.filter(email="newuser@example.com").exists())
        resp = self.client.post(self.url, {"credential": "fake-jwt"}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        self.assertTrue(resp.data["created"])

        user = User.objects.get(email="newuser@example.com")
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "User")
        self.assertFalse(user.has_usable_password())

    @mock.patch(GOOGLE_VERIFY_PATH, return_value={
        "email": "existing@example.com",
        "email_verified": True,
    })
    def test_existing_email_returns_tokens_without_creating_duplicate(self, _mock_verify):
        self.create_user(email="existing@example.com", password="existing")
        self.assertEqual(User.objects.filter(email="existing@example.com").count(), 1)

        resp = self.client.post(self.url, {"credential": "fake-jwt"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertFalse(resp.data["created"])

        # No duplicate created
        self.assertEqual(User.objects.filter(email="existing@example.com").count(), 1)

    @mock.patch(GOOGLE_VERIFY_PATH, return_value={
        "email": "disabled@example.com",
        "email_verified": True,
    })
    def test_inactive_user_returns_403(self, _mock_verify):
        user = self.create_user(email="disabled@example.com")
        user.is_active = False
        user.save()

        resp = self.client.post(self.url, {"credential": "fake-jwt"}, format="json")
        self.assertEqual(resp.status_code, 403)

    @mock.patch(GOOGLE_VERIFY_PATH, return_value={
        "email": "auditme@example.com",
        "email_verified": True,
    })
    def test_successful_google_auth_writes_audit_log(self, _mock_verify):
        before = AuthAuditLog.objects.filter(event_type="google_auth").count()
        self.client.post(self.url, {"credential": "fake-jwt"}, format="json")
        after = AuthAuditLog.objects.filter(event_type="google_auth").count()
        self.assertEqual(after, before + 1)

    @mock.patch(GOOGLE_VERIFY_PATH, return_value={
        "email": "Newcase@Example.com",
        "email_verified": True,
    })
    def test_email_normalised_to_lowercase(self, _mock_verify):
        resp = self.client.post(self.url, {"credential": "fake-jwt"}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(User.objects.filter(email="newcase@example.com").exists())

    # ── Agency-bootstrapped lockdown ──────────────────────────────────────

    @mock.patch(GOOGLE_VERIFY_PATH, return_value={
        "email": "random@example.com",
        "email_verified": True,
    })
    def test_new_google_user_blocked_once_agency_exists(self, _mock_verify):
        """Once the singleton Agency is configured, unknown Google emails
        must NOT auto-create a new admin-visible account."""
        Agency.objects.create(account_type=Agency.AccountType.INDIVIDUAL, name="Existing")
        resp = self.client.post(self.url, {"credential": "fake-jwt"}, format="json")
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(User.objects.filter(email="random@example.com").exists())

    @mock.patch(GOOGLE_VERIFY_PATH, return_value={
        "email": "known@example.com",
        "email_verified": True,
    })
    def test_existing_user_can_still_google_sign_in_after_bootstrap(self, _mock_verify):
        """Existing users must still be able to authenticate via Google
        even after the Agency is configured — only NEW account creation is blocked."""
        Agency.objects.create(account_type=Agency.AccountType.INDIVIDUAL, name="Existing")
        self.create_user(email="known@example.com", password="x" * 12)

        resp = self.client.post(self.url, {"credential": "fake-jwt"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertFalse(resp.data["created"])
