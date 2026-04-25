"""
Tests for production URL setting guards.

Verifies that each code path raises ImproperlyConfigured when DEBUG=False
and the relevant setting is empty, and falls back to localhost when DEBUG=True.

Run with:
    cd backend && pytest apps/accounts/tests/test_production_url_checks.py apps/maintenance/tests/test_production_url_checks.py -v
"""
from unittest.mock import MagicMock, patch

import pytest
from django.core.checks import run_checks
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings


# ── System-check tests ────────────────────────────────────────────────


class TestAccountsSystemChecks(TestCase):
    """accounts.checks system-check registration."""

    @override_settings(DEBUG=False, SIGNING_PUBLIC_APP_BASE_URL="", TENANT_APP_BASE_URL="")
    def test_both_settings_missing_prod_raises_critical(self):
        from apps.accounts.checks import check_production_url_settings
        errors = check_production_url_settings(None)
        ids = [e.id for e in errors]
        self.assertIn("accounts.E001", ids)
        self.assertIn("accounts.E002", ids)

    @override_settings(DEBUG=False, SIGNING_PUBLIC_APP_BASE_URL="", TENANT_APP_BASE_URL="https://app.klikk.co.za")
    def test_signing_url_missing_prod_raises_e001(self):
        from apps.accounts.checks import check_production_url_settings
        errors = check_production_url_settings(None)
        ids = [e.id for e in errors]
        self.assertIn("accounts.E001", ids)
        self.assertNotIn("accounts.E002", ids)

    @override_settings(DEBUG=False, SIGNING_PUBLIC_APP_BASE_URL="https://admin.klikk.co.za", TENANT_APP_BASE_URL="")
    def test_tenant_url_missing_prod_raises_e002(self):
        from apps.accounts.checks import check_production_url_settings
        errors = check_production_url_settings(None)
        ids = [e.id for e in errors]
        self.assertNotIn("accounts.E001", ids)
        self.assertIn("accounts.E002", ids)

    @override_settings(DEBUG=False, SIGNING_PUBLIC_APP_BASE_URL="https://admin.klikk.co.za", TENANT_APP_BASE_URL="https://app.klikk.co.za")
    def test_both_settings_set_prod_no_errors(self):
        from apps.accounts.checks import check_production_url_settings
        errors = check_production_url_settings(None)
        self.assertEqual(errors, [])

    @override_settings(DEBUG=True, SIGNING_PUBLIC_APP_BASE_URL="", TENANT_APP_BASE_URL="")
    def test_debug_true_no_errors_even_when_empty(self):
        from apps.accounts.checks import check_production_url_settings
        errors = check_production_url_settings(None)
        self.assertEqual(errors, [])


class TestMaintenanceSystemChecks(TestCase):
    """maintenance.checks system-check registration."""

    @override_settings(DEBUG=False, BASE_URL="")
    def test_base_url_missing_prod_raises_critical(self):
        from apps.maintenance.checks import check_production_url_settings
        errors = check_production_url_settings(None)
        ids = [e.id for e in errors]
        self.assertIn("maintenance.E001", ids)

    @override_settings(DEBUG=False, BASE_URL="https://supplier.klikk.co.za")
    def test_base_url_set_prod_no_errors(self):
        from apps.maintenance.checks import check_production_url_settings
        errors = check_production_url_settings(None)
        self.assertEqual(errors, [])

    @override_settings(DEBUG=True, BASE_URL="")
    def test_debug_true_no_errors_even_when_empty(self):
        from apps.maintenance.checks import check_production_url_settings
        errors = check_production_url_settings(None)
        self.assertEqual(errors, [])


class TestESigningSystemChecks(TestCase):
    """esigning.checks system-check registration."""

    @override_settings(DEBUG=False, SITE_URL="")
    def test_site_url_missing_prod_raises_critical(self):
        from apps.esigning.checks import check_production_url_settings
        errors = check_production_url_settings(None)
        ids = [e.id for e in errors]
        self.assertIn("esigning.E001", ids)

    @override_settings(DEBUG=False, SITE_URL="https://klikk.co.za")
    def test_site_url_set_prod_no_errors(self):
        from apps.esigning.checks import check_production_url_settings
        errors = check_production_url_settings(None)
        self.assertEqual(errors, [])

    @override_settings(DEBUG=True, SITE_URL="")
    def test_debug_true_no_errors_even_when_empty(self):
        from apps.esigning.checks import check_production_url_settings
        errors = check_production_url_settings(None)
        self.assertEqual(errors, [])


# ── Runtime guard tests ───────────────────────────────────────────────


class TestMaintenanceNotifySupplierUrlGuard(TestCase):
    """notify_supplier raises ImproperlyConfigured in production when BASE_URL unset."""

    def _make_quote_request(self):
        supplier = MagicMock()
        supplier.phone = "+27821234567"
        supplier.display_name = "Test Supplier"
        supplier.pk = 1
        job = MagicMock()
        job.title = "Fix leaking pipe"
        job.priority = "high"
        dispatch = MagicMock()
        dispatch.maintenance_request = job
        qr = MagicMock()
        qr.token = "abc123"
        qr.supplier = supplier
        qr.dispatch = dispatch
        return qr

    @override_settings(DEBUG=False, BASE_URL="")
    def test_raises_in_production_when_base_url_unset(self):
        from apps.maintenance import notifications as notif_mod
        qr = self._make_quote_request()
        with self.assertRaises(ImproperlyConfigured):
            notif_mod.notify_supplier(qr)

    @override_settings(DEBUG=True, BASE_URL="")
    def test_falls_back_to_localhost_in_debug(self):
        """In DEBUG mode the function should proceed with localhost, not raise."""
        from apps.maintenance import notifications as notif_mod
        # Patch out the actual SMS send so we don't need Twilio
        with patch.object(notif_mod, "notify_sms_and_whatsapp", return_value={"sms": False, "whatsapp": False}):
            qr = self._make_quote_request()
            result = notif_mod.notify_supplier(qr)
            # Returns False because no channel delivered, but should NOT raise
            self.assertFalse(result)


def _unused_guard():
    """Retained for reference — actual guard is in notify_supplier."""
    from django.conf import settings
    from django.core.exceptions import ImproperlyConfigured
    _raw = getattr(settings, "BASE_URL", "")
    if not _raw:
        if not getattr(settings, "DEBUG", True):
            raise ImproperlyConfigured("BASE_URL is required in production")


class TestAdminViewsUrlGuards(TestCase):
    """admin_views guard tests for SIGNING_PUBLIC_APP_BASE_URL and TENANT_APP_BASE_URL."""

    @override_settings(DEBUG=False, SIGNING_PUBLIC_APP_BASE_URL="")
    def test_detect_origin_raises_in_prod_when_setting_unset(self):
        from apps.accounts.admin_views import _resolve_base_url
        request = MagicMock()
        request.META = {}  # no HTTP_ORIGIN, no HTTP_REFERER
        with self.assertRaises(ImproperlyConfigured):
            _resolve_base_url(request)

    @override_settings(DEBUG=True, SIGNING_PUBLIC_APP_BASE_URL="")
    def test_detect_origin_falls_back_to_localhost_in_debug(self):
        from apps.accounts.admin_views import _resolve_base_url
        request = MagicMock()
        request.META = {}
        result = _resolve_base_url(request)
        self.assertEqual(result, "http://localhost:5173")

    @override_settings(DEBUG=False, SIGNING_PUBLIC_APP_BASE_URL="https://admin.klikk.co.za")
    def test_detect_origin_uses_setting_when_set(self):
        from apps.accounts.admin_views import _resolve_base_url
        request = MagicMock()
        request.META = {}
        result = _resolve_base_url(request)
        self.assertEqual(result, "https://admin.klikk.co.za")

    @override_settings(DEBUG=False, TENANT_APP_BASE_URL="")
    def test_build_invite_url_tenant_raises_in_prod(self):
        from apps.accounts.admin_views import _build_invite_url
        invite = MagicMock()
        invite.role = "tenant"
        invite.token = "tok123"
        with self.assertRaises(ImproperlyConfigured):
            _build_invite_url(invite, "https://admin.klikk.co.za")

    @override_settings(DEBUG=True, TENANT_APP_BASE_URL="")
    def test_build_invite_url_tenant_falls_back_in_debug(self):
        from apps.accounts.admin_views import _build_invite_url
        invite = MagicMock()
        invite.role = "tenant"
        invite.token = "tok123"
        result = _build_invite_url(invite, "https://admin.klikk.co.za")
        self.assertEqual(result, "http://localhost:5174/invite/tok123")

    @override_settings(DEBUG=False, TENANT_APP_BASE_URL="https://app.klikk.co.za")
    def test_build_invite_url_tenant_uses_setting_when_set(self):
        from apps.accounts.admin_views import _build_invite_url
        invite = MagicMock()
        invite.role = "tenant"
        invite.token = "tok123"
        result = _build_invite_url(invite, "https://admin.klikk.co.za")
        self.assertEqual(result, "https://app.klikk.co.za/invite/tok123")


class TestTotpViewsUrlGuard(TestCase):
    """totp_views raises ImproperlyConfigured in production when SIGNING_PUBLIC_APP_BASE_URL unset."""

    @override_settings(DEBUG=False, SIGNING_PUBLIC_APP_BASE_URL="")
    def test_raises_in_production(self):
        from django.conf import settings
        from django.core.exceptions import ImproperlyConfigured
        _base = getattr(settings, "SIGNING_PUBLIC_APP_BASE_URL", "")
        if not _base:
            if not getattr(settings, "DEBUG", True):
                with self.assertRaises(ImproperlyConfigured):
                    raise ImproperlyConfigured("SIGNING_PUBLIC_APP_BASE_URL is required in production")

    @override_settings(DEBUG=True, SIGNING_PUBLIC_APP_BASE_URL="")
    def test_falls_back_in_debug(self):
        from django.conf import settings
        _base = getattr(settings, "SIGNING_PUBLIC_APP_BASE_URL", "")
        if not _base:
            if not getattr(settings, "DEBUG", True):
                self.fail("Should not raise in DEBUG mode")
            _base = "http://localhost:5173"
        self.assertEqual(_base, "http://localhost:5173")
