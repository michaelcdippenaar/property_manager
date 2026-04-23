"""
RNT-SEC-028 — GotenbergHealthView access control.

Asserts that:
- A non-admin agent receives HTTP 403 on GET /api/v1/esigning/gotenberg/health/
- A system admin can reach the endpoint (non-403 response)
- An unauthenticated request receives HTTP 401/403
"""
import pytest
from unittest import mock

from django.urls import reverse

from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]

_HEALTH_URL = "gotenberg-health"

_FAKE_HEALTH = {
    "status": "up",
    "details": {
        "chromium": {"status": "up"},
        "uno": {"status": "up"},
    },
}


class TestGotenbergHealthAccessControl(TremlyAPITestCase):
    """GotenbergHealthView must be restricted to system admins only."""

    def setUp(self):
        self.agent = self.create_agent()
        self.admin = self.create_admin()
        self.url = reverse(_HEALTH_URL)

    # ── Non-admin agent must be denied ──────────────────────────────────── #

    def test_agent_receives_403(self):
        """A non-admin agent must receive HTTP 403 — infrastructure disclosure prevented."""
        self.authenticate(self.agent)
        resp = self.client.get(self.url)
        self.assertEqual(
            resp.status_code,
            403,
            "Agent must not be able to access GotenbergHealthView (infrastructure disclosure risk).",
        )

    # ── Admin user must be permitted ─────────────────────────────────────── #

    def test_admin_can_access(self):
        """System admin must be able to access the health endpoint for operational monitoring."""
        self.authenticate(self.admin)
        with mock.patch(
            "apps.esigning.gotenberg.health_check",
            return_value=_FAKE_HEALTH,
        ):
            resp = self.client.get(self.url)
        self.assertNotEqual(
            resp.status_code,
            403,
            "Admin must not be blocked from GotenbergHealthView.",
        )
        # Successful response returns 200
        self.assertEqual(resp.status_code, 200)

    # ── Unauthenticated request ───────────────────────────────────────────── #

    def test_unauthenticated_denied(self):
        """Unauthenticated requests must be rejected (401 or 403)."""
        resp = self.client.get(self.url)
        self.assertIn(
            resp.status_code,
            [401, 403],
            "Unauthenticated access to GotenbergHealthView must be rejected.",
        )
