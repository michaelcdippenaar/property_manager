"""Integration tests for POST /auth/welcome/ (MarkWelcomeSeenView)."""
import pytest

from django.urls import reverse
from django.utils import timezone

from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]

URL = reverse("auth-welcome")


class MarkWelcomeSeenTests(TremlyAPITestCase):

    def test_first_call_stamps_seen_welcome_at(self):
        """POSTing welcome/ sets seen_welcome_at on a user who hasn't seen it yet."""
        tenant = self.create_tenant(email="tenant-welcome@test.com")
        self.assertIsNone(tenant.seen_welcome_at)
        self.authenticate(tenant)

        resp = self.client.post(URL)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("seen_welcome_at", resp.data)
        self.assertIsNotNone(resp.data["seen_welcome_at"])

        tenant.refresh_from_db()
        self.assertIsNotNone(tenant.seen_welcome_at)

    def test_idempotent_second_call_does_not_overwrite(self):
        """A second call must not reset seen_welcome_at to a later timestamp."""
        tenant = self.create_tenant(email="tenant-welcome2@test.com")
        self.authenticate(tenant)

        self.client.post(URL)
        tenant.refresh_from_db()
        first_stamp = tenant.seen_welcome_at

        self.client.post(URL)
        tenant.refresh_from_db()
        second_stamp = tenant.seen_welcome_at

        self.assertEqual(first_stamp, second_stamp)

    def test_unauthenticated_returns_401(self):
        """Endpoint must be protected — anonymous callers get 401."""
        resp = self.client.post(URL)
        self.assertEqual(resp.status_code, 401)

    def test_response_includes_user_profile(self):
        """Response body contains a full user profile so the client can update its store."""
        tenant = self.create_tenant(email="tenant-welcome3@test.com")
        self.authenticate(tenant)

        resp = self.client.post(URL)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("email", resp.data)
        self.assertIn("role", resp.data)

    def test_new_user_seen_welcome_at_is_null(self):
        """Freshly created tenant has seen_welcome_at = null — welcome screen should appear."""
        tenant = self.create_tenant(email="tenant-new-welcome@test.com")
        self.authenticate(tenant)

        resp = self.client.get(reverse("auth-me"))

        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.data.get("seen_welcome_at"))
