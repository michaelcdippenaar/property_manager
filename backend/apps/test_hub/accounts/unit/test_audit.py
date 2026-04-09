"""
Unit tests for the authentication audit logging helper.

Source file under test: apps/accounts/audit.py :: log_auth_event
"""
from unittest.mock import MagicMock

import pytest

from apps.accounts.audit import log_auth_event
from apps.accounts.models import AuthAuditLog
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


class LogAuthEventTests(TremlyAPITestCase):
    """log_auth_event must persist an AuthAuditLog row with the extracted request info."""

    def _make_request(self, remote_addr="1.2.3.4", user_agent="pytest-agent/1.0", xff=None):
        req = MagicMock()
        meta = {"REMOTE_ADDR": remote_addr, "HTTP_USER_AGENT": user_agent}
        if xff is not None:
            meta["HTTP_X_FORWARDED_FOR"] = xff
        req.META = meta
        return req

    def test_creates_audit_log_row(self):
        user = self.create_tenant()
        before = AuthAuditLog.objects.count()
        log_auth_event("login_success", request=self._make_request(), user=user)
        self.assertEqual(AuthAuditLog.objects.count(), before + 1)

    def test_captures_event_type(self):
        user = self.create_tenant()
        entry = log_auth_event("login_failed", request=self._make_request(), user=user)
        self.assertEqual(entry.event_type, "login_failed")

    def test_captures_remote_addr_when_no_xff_header(self):
        user = self.create_tenant()
        entry = log_auth_event("login_success", request=self._make_request(remote_addr="10.0.0.1"), user=user)
        self.assertEqual(str(entry.ip_address), "10.0.0.1")

    def test_prefers_first_x_forwarded_for_address(self):
        user = self.create_tenant()
        req = self._make_request(xff="203.0.113.7, 10.0.0.1, 192.168.1.1")
        entry = log_auth_event("login_success", request=req, user=user)
        self.assertEqual(str(entry.ip_address), "203.0.113.7")

    def test_captures_user_agent(self):
        user = self.create_tenant()
        entry = log_auth_event(
            "login_success",
            request=self._make_request(user_agent="Mozilla/5.0 Safari"),
            user=user,
        )
        self.assertEqual(entry.user_agent, "Mozilla/5.0 Safari")

    def test_without_request_uses_null_ip_and_empty_ua(self):
        user = self.create_tenant()
        entry = log_auth_event("logout", request=None, user=user)
        self.assertIsNone(entry.ip_address)
        self.assertEqual(entry.user_agent, "")

    def test_metadata_defaults_to_empty_dict(self):
        user = self.create_tenant()
        entry = log_auth_event("register", request=None, user=user)
        self.assertEqual(entry.metadata, {})

    def test_metadata_is_persisted(self):
        user = self.create_tenant()
        entry = log_auth_event(
            "register",
            request=None,
            user=user,
            metadata={"referrer": "google", "campaign": "launch"},
        )
        self.assertEqual(entry.metadata, {"referrer": "google", "campaign": "launch"})

    def test_user_may_be_none_for_anonymous_events(self):
        """Failed logins by unknown email shouldn't need a user FK."""
        entry = log_auth_event(
            "login_failed",
            request=self._make_request(),
            user=None,
            metadata={"email_attempted": "ghost@example.com"},
        )
        self.assertIsNone(entry.user_id)
        self.assertEqual(entry.metadata["email_attempted"], "ghost@example.com")
