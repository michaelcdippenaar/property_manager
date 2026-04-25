"""
Tests for production URL setting guards via Django system checks.

The system checks (checks.py in each app) fire at startup (manage.py check --deploy)
and catch misconfigured production deployments before they can serve requests
with broken localhost URLs.

Run with:
    cd backend && pytest apps/accounts/tests/test_production_url_checks.py -v
"""
import pytest
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
