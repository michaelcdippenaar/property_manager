"""Integration tests for GET/POST /auth/push-preferences/ (PushPreferenceView)."""
import pytest
from django.urls import reverse

from apps.notifications.models import PushPreference
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]

URL = reverse("push-preferences")

VALID_CATEGORIES = [c[0] for c in PushPreference.Category.choices]


class PushPreferenceGetTests(TremlyAPITestCase):
    """GET /auth/push-preferences/"""

    def test_unauthenticated_returns_401(self):
        resp = self.client.get(URL)
        self.assertEqual(resp.status_code, 401)

    def test_returns_all_categories_with_defaults(self):
        user = self.create_user()
        self.authenticate(user)
        resp = self.client.get(URL)
        self.assertEqual(resp.status_code, 200)
        categories_returned = {item["category"] for item in resp.data}
        self.assertEqual(categories_returned, set(VALID_CATEGORIES))
        # Default (no saved rows) should be True for all
        for item in resp.data:
            self.assertTrue(item["enabled"])

    def test_returns_saved_preference(self):
        user = self.create_user()
        self.authenticate(user)
        PushPreference.objects.create(user=user, category="rent", enabled=False)
        resp = self.client.get(URL)
        self.assertEqual(resp.status_code, 200)
        rent = next(i for i in resp.data if i["category"] == "rent")
        self.assertFalse(rent["enabled"])
        # Other categories still default True
        lease = next(i for i in resp.data if i["category"] == "lease")
        self.assertTrue(lease["enabled"])


class PushPreferencePostTests(TremlyAPITestCase):
    """POST /auth/push-preferences/"""

    def test_unauthenticated_returns_401(self):
        resp = self.client.post(URL, {"category": "rent", "enabled": False}, format="json")
        self.assertEqual(resp.status_code, 401)

    def test_creates_preference(self):
        user = self.create_user()
        self.authenticate(user)
        resp = self.client.post(URL, {"category": "lease", "enabled": False}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["category"], "lease")
        self.assertFalse(resp.data["enabled"])
        self.assertFalse(
            PushPreference.objects.get(user=user, category="lease").enabled
        )

    def test_updates_existing_preference(self):
        user = self.create_user()
        self.authenticate(user)
        PushPreference.objects.create(user=user, category="chat", enabled=False)
        resp = self.client.post(URL, {"category": "chat", "enabled": True}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["enabled"])
        self.assertTrue(
            PushPreference.objects.get(user=user, category="chat").enabled
        )

    def test_invalid_category_returns_400(self):
        user = self.create_user()
        self.authenticate(user)
        resp = self.client.post(URL, {"category": "invalid_cat", "enabled": True}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_missing_enabled_returns_400(self):
        user = self.create_user()
        self.authenticate(user)
        resp = self.client.post(URL, {"category": "rent"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_enabled_as_string_returns_400(self):
        user = self.create_user()
        self.authenticate(user)
        resp = self.client.post(URL, {"category": "rent", "enabled": "yes"}, format="json")
        self.assertEqual(resp.status_code, 400)
