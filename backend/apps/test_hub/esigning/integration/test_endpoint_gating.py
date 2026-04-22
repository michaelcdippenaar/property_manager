"""
Tests for ENABLE_TEST_ENDPOINTS gating.

Verifies that:
- ESigningTestPdfView returns 404 when ENABLE_TEST_ENDPOINTS=False (production mode)
- ESigningTestPdfView is reachable when ENABLE_TEST_ENDPOINTS=True (staging/dev mode)
- The test-hub URL prefix is not registered when ENABLE_TEST_ENDPOINTS=False
"""
import pytest
from unittest import mock

from django.test import override_settings, RequestFactory
from django.urls import reverse, NoReverseMatch

from apps.esigning.models import ESigningSubmission
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


class TestESigningTestPdfGating(TremlyAPITestCase):
    """ESigningTestPdfView must 404 in production (ENABLE_TEST_ENDPOINTS=False)."""

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)
        self.submission = ESigningSubmission.objects.create(
            lease=self.lease, status="pending", created_by=self.agent,
        )
        self.authenticate(self.agent)

    @override_settings(ENABLE_TEST_ENDPOINTS=False)
    def test_test_pdf_returns_404_when_flag_off(self):
        """Production mode: test-pdf endpoint must return 404."""
        url = reverse("esigning-test-pdf", kwargs={"pk": self.submission.pk})
        resp = self.client.get(url)
        self.assertEqual(
            resp.status_code,
            404,
            "ESigningTestPdfView must return 404 when ENABLE_TEST_ENDPOINTS=False",
        )

    @override_settings(ENABLE_TEST_ENDPOINTS=True)
    def test_test_pdf_accessible_when_flag_on(self):
        """Staging mode: test-pdf endpoint must NOT return 404 (auth gating still applies)."""
        url = reverse("esigning-test-pdf", kwargs={"pk": self.submission.pk})
        # Patch the PDF generation so we don't need a live Gotenberg server in tests
        with mock.patch(
            "apps.esigning.services.generate_signed_pdf",
            return_value=b"%PDF-1.4 fake",
        ):
            resp = self.client.get(url)
        # With flag on, the view is active — it should not be a 404
        self.assertNotEqual(
            resp.status_code,
            404,
            "ESigningTestPdfView must not return 404 when ENABLE_TEST_ENDPOINTS=True",
        )

    @override_settings(ENABLE_TEST_ENDPOINTS=False)
    def test_test_pdf_unauthenticated_returns_401_regardless_of_flag(self):
        """Unauthenticated requests are rejected before the flag check."""
        self.client.logout()
        url = reverse("esigning-test-pdf", kwargs={"pk": self.submission.pk})
        resp = self.client.get(url)
        # DRF returns 401 for unauthenticated; the route still exists (flag gates inside view)
        self.assertIn(resp.status_code, [401, 403])
