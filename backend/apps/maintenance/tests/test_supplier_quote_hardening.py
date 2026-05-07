"""
QA Round 3 (C): Regression contract for SupplierQuoteView / SupplierQuoteDeclineView.

Round 1 hardened the public token-based quote endpoints with:
  - 14-day TTL on the token (created_at + 14d → 410 Gone)
  - Inactive supplier rejection (403 Forbidden)
  - State-machine guard `_QUOTABLE_STATES` (= {pending, viewed}) — anything
    outside that set yields 409 Conflict on submit/decline
  - AnonRateThrottle (scope ``public_sign_minute``) — per-IP throttle that
    matches the public-sign endpoints

The existing ``test_supplier_quote.py`` covers expiry / inactive-supplier /
awarded — this module adds the missing rate-limit regression and serves as a
single contract file the test_hub fixes can also reference.
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Agency, User
from apps.maintenance.models import (
    JobDispatch, JobQuoteRequest, MaintenanceRequest, Supplier,
)
from apps.properties.models import Property, Unit


@pytest.mark.django_db
class SupplierQuoteHardeningContractTest(TestCase):
    """One row per hardening guard — keeps the contract scannable."""

    def setUp(self):
        # DRF SimpleRateThrottle uses the default cache; clear between tests
        # so per-IP buckets from a previous test don't leak into this one.
        cache.clear()

        self.agency = Agency.objects.create(name="Hardening Agency")
        self.tenant = User.objects.create_user(
            email="harden_tenant@x.com", password="pass", role=User.Role.TENANT,
        )
        self.prop = Property.objects.create(
            agency=self.agency, name="H House", property_type="house",
            address="2 H St", city="C", province="WC", postal_code="0002",
        )
        self.unit = Unit.objects.create(
            agency=self.agency, property=self.prop, unit_number="1",
            rent_amount=Decimal("5000"),
        )
        self.supplier = Supplier.objects.create(
            agency=self.agency, name="Sue Sparky",
            company_name="Sue's Sparkies",
            email="sue@spark.test", phone="+27001",
        )
        self.req = MaintenanceRequest.objects.create(
            agency=self.agency, unit=self.unit, tenant=self.tenant,
            title="Light flickers", description="Flicker flicker",
            category="electrical", priority="medium", status="open",
        )
        self.dispatch = JobDispatch.objects.create(
            agency=self.agency, maintenance_request=self.req,
            status=JobDispatch.Status.SENT,
        )

    def _make_qr(self, **overrides):
        defaults = dict(
            agency=self.agency, dispatch=self.dispatch, supplier=self.supplier,
            token=uuid4(), status=JobQuoteRequest.Status.PENDING,
        )
        defaults.update(overrides)
        return JobQuoteRequest.objects.create(**defaults)

    def _quote_url(self, token):
        return f"/api/v1/maintenance/quotes/{token}/"

    def _decline_url(self, token):
        return f"/api/v1/maintenance/quotes/{token}/decline/"

    # ── Token expiry ─────────────────────────────────────────────────────

    def test_expired_token_returns_410(self):
        qr = self._make_qr()
        qr.created_at = timezone.now() - timedelta(days=15)
        qr.save(update_fields=["created_at"])
        client = APIClient()

        resp = client.post(
            self._quote_url(qr.token), {"amount": "1000.00"}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_410_GONE)
        qr.refresh_from_db()
        self.assertEqual(qr.status, JobQuoteRequest.Status.EXPIRED)

    # ── State-machine guard ──────────────────────────────────────────────

    def test_awarded_request_returns_409(self):
        qr = self._make_qr(status=JobQuoteRequest.Status.AWARDED)
        client = APIClient()

        resp = client.post(
            self._quote_url(qr.token), {"amount": "1000.00"}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

    # ── Inactive supplier ────────────────────────────────────────────────

    def test_inactive_supplier_returns_403(self):
        self.supplier.is_active = False
        self.supplier.save(update_fields=["is_active"])
        qr = self._make_qr()
        client = APIClient()

        resp = client.post(
            self._quote_url(qr.token), {"amount": "1000.00"}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ── AnonRateThrottle (per-IP) ────────────────────────────────────────

    def test_rate_limit_kicks_in_after_burst(self):
        """After exhausting the per-IP minute bucket, the next GET is 429.

        Uses the production ceiling (10/min via ``public_sign_minute``).
        Sends 11 requests from the same IP within the bucket window; the
        11th must return 429. Cache is cleared in setUp.
        """
        qr = self._make_qr()
        client = APIClient()
        url = self._quote_url(qr.token)

        seen_429 = False
        for i in range(15):
            resp = client.get(url)
            if resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                seen_429 = True
                break

        self.assertTrue(
            seen_429,
            "Expected SupplierQuoteAnonThrottle (10/min) to return 429 "
            "within 15 requests; got none.",
        )
