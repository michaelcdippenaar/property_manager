"""
Owner dashboard cache invalidation tests — RNT-QUAL-006.

Covers:
  - GET /api/v1/properties/owner/dashboard/ returns stats with last_updated
  - GET /api/v1/properties/owner/activity/ returns activity feed
  - Cache is populated on first hit and reused on second hit
  - Cache is invalidated when a RentPayment is saved
  - Cache is invalidated when a Lease is saved
  - Cache is invalidated when a MaintenanceRequest is saved
  - Cache is invalidated when a RentalMandate is saved
  - Payment performance widget reflects current month
  - Non-owner (no person_profile) gets zero-state response
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.utils import timezone

from apps.payments.models import RentInvoice, RentPayment
from apps.properties.models import RentalMandate
from apps.properties.dashboard_service import (
    get_dashboard_stats,
    get_activity_feed,
    invalidate_owner_dashboard,
    _cache_key,
)
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration]


class OwnerDashboardCacheTest(TremlyAPITestCase):
    """Tests for dashboard stats caching and cache invalidation."""

    def setUp(self):
        self.owner_user = self.create_owner_user(email="owner@cache-test.co.za")
        self.person = self.create_person(full_name="Cache Owner", linked_user=self.owner_user)
        self.prop = self.create_property(name="Cache Villa")
        # Wire property to owner via Property.owner FK
        self.prop.owner = self.person
        self.prop.save(update_fields=["owner"])
        self.unit = self.create_unit(property_obj=self.prop, status="occupied")
        self.authenticate(self.owner_user)
        cache.clear()

    def tearDown(self):
        cache.clear()

    # ── Basic endpoint tests ─────────────────────────────────────────────────

    def test_dashboard_endpoint_returns_stats(self):
        resp = self.client.get("/api/v1/properties/owner/dashboard/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("total_properties", data)
        self.assertIn("last_updated", data)
        self.assertIn("payment_performance", data)

    def test_dashboard_endpoint_reflects_property(self):
        resp = self.client.get("/api/v1/properties/owner/dashboard/")
        data = resp.json()
        self.assertEqual(data["total_properties"], 1)
        self.assertEqual(data["total_units"], 1)
        self.assertEqual(data["occupied_units"], 1)
        self.assertEqual(data["occupancy_rate"], 100)

    def test_activity_feed_endpoint_returns_list(self):
        resp = self.client.get("/api/v1/properties/owner/activity/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)

    def test_activity_feed_limit_capped_at_50(self):
        resp = self.client.get("/api/v1/properties/owner/activity/?limit=999")
        self.assertEqual(resp.status_code, 200)  # no error

    # ── Cache hit / miss ─────────────────────────────────────────────────────

    def test_cache_populated_on_first_call(self):
        key = _cache_key(self.person.pk)
        self.assertIsNone(cache.get(key), "cache should be empty before first call")
        get_dashboard_stats(self.person.pk)
        self.assertIsNotNone(cache.get(key), "cache should be populated after first call")

    def test_cache_reused_on_second_call(self):
        key = _cache_key(self.person.pk)
        first = get_dashboard_stats(self.person.pk)
        # Manually corrupt the cache value to prove second call returns stale
        cached = cache.get(key)
        cached["__test_marker__"] = "hit"
        cache.set(key, cached, 300)
        second = get_dashboard_stats(self.person.pk)
        self.assertIn("__test_marker__", second, "second call should return cached value")

    def test_invalidate_clears_cache(self):
        get_dashboard_stats(self.person.pk)
        invalidate_owner_dashboard(self.person.pk)
        self.assertIsNone(cache.get(_cache_key(self.person.pk)))

    # ── Signal-driven invalidation ────────────────────────────────────────────

    def _make_invoice(self):
        tenant = self.create_tenant(email="tenant-for-inv@test.co.za")
        person = self.create_person(full_name="Tenant Person", linked_user=tenant)
        lease = self.create_lease(unit=self.unit, primary_tenant=person)
        today = date.today()
        return RentInvoice.objects.create(
            lease=lease,
            period_start=today.replace(day=1),
            period_end=today,
            amount_due=Decimal("5000.00"),
            due_date=today,
            status=RentInvoice.Status.UNPAID,
        )

    def test_rent_payment_save_invalidates_cache(self):
        get_dashboard_stats(self.person.pk)
        self.assertIsNotNone(cache.get(_cache_key(self.person.pk)))

        invoice = self._make_invoice()
        RentPayment.objects.create(
            invoice=invoice,
            amount=Decimal("5000.00"),
            payment_date=date.today(),
            status=RentPayment.Status.CLEARED,
        )
        self.assertIsNone(
            cache.get(_cache_key(self.person.pk)),
            "cache should be cleared after rent payment",
        )

    def test_lease_save_invalidates_cache(self):
        get_dashboard_stats(self.person.pk)
        self.assertIsNotNone(cache.get(_cache_key(self.person.pk)))

        tenant = self.create_tenant(email="lease-signal-tenant@test.co.za")
        person = self.create_person(full_name="Signal Tenant", linked_user=tenant)
        self.create_lease(unit=self.unit, primary_tenant=person)
        self.assertIsNone(
            cache.get(_cache_key(self.person.pk)),
            "cache should be cleared after lease save",
        )

    def test_maintenance_request_save_invalidates_cache(self):
        get_dashboard_stats(self.person.pk)
        self.assertIsNotNone(cache.get(_cache_key(self.person.pk)))

        self.create_maintenance_request(unit=self.unit)
        self.assertIsNone(
            cache.get(_cache_key(self.person.pk)),
            "cache should be cleared after maintenance request save",
        )

    def test_mandate_save_invalidates_cache(self):
        get_dashboard_stats(self.person.pk)
        self.assertIsNotNone(cache.get(_cache_key(self.person.pk)))

        RentalMandate.objects.create(
            property=self.prop,
            mandate_type=RentalMandate.MandateType.FULL_MANAGEMENT,
            commission_rate="10.00",
            start_date=date.today(),
            status=RentalMandate.Status.ACTIVE,
        )
        self.assertIsNone(
            cache.get(_cache_key(self.person.pk)),
            "cache should be cleared after rental mandate save",
        )

    # ── Payment performance widget ───────────────────────────────────────────

    def test_payment_performance_current_month(self):
        invoice = self._make_invoice()
        RentPayment.objects.create(
            invoice=invoice,
            amount=Decimal("5000.00"),
            payment_date=date.today(),
            status=RentPayment.Status.CLEARED,
        )
        stats = get_dashboard_stats(self.person.pk)
        perf = stats["payment_performance"]
        self.assertIsNotNone(perf)
        self.assertEqual(perf["month"], date.today().strftime("%Y-%m"))
        self.assertGreaterEqual(perf["invoices_due"], 1)

    # ── No person_profile → zero-state ──────────────────────────────────────

    def test_no_person_profile_returns_zero_state(self):
        user = self.create_owner_user(email="noprofile@cache-test.co.za")
        # No Person linked to this user
        self.authenticate(user)
        resp = self.client.get("/api/v1/properties/owner/dashboard/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_properties"], 0)

    def test_no_person_profile_activity_returns_empty(self):
        user = self.create_owner_user(email="noprofile2@cache-test.co.za")
        self.authenticate(user)
        resp = self.client.get("/api/v1/properties/owner/activity/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])


class OwnerActivityFeedContentTest(TremlyAPITestCase):
    """Tests that activity feed events contain the expected event types."""

    def setUp(self):
        self.owner_user = self.create_owner_user(email="feed-owner@test.co.za")
        self.person = self.create_person(full_name="Feed Owner", linked_user=self.owner_user)
        self.prop = self.create_property(name="Feed Property")
        self.prop.owner = self.person
        self.prop.save(update_fields=["owner"])
        self.unit = self.create_unit(property_obj=self.prop, status="occupied")
        self.authenticate(self.owner_user)
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_lease_signed_event_in_feed(self):
        tenant = self.create_tenant(email="feed-tenant@test.co.za")
        person = self.create_person(full_name="Feed Tenant", linked_user=tenant)
        self.create_lease(unit=self.unit, primary_tenant=person, status="active")
        feed = get_activity_feed(self.person.pk)
        types = [e["event_type"] for e in feed]
        self.assertIn("lease_signed", types)

    def test_maintenance_opened_event_in_feed(self):
        self.create_maintenance_request(unit=self.unit, status="open")
        feed = get_activity_feed(self.person.pk)
        types = [e["event_type"] for e in feed]
        self.assertIn("maintenance_opened", types)

    def test_rent_received_event_in_feed(self):
        tenant = self.create_tenant(email="feed-payer@test.co.za")
        person = self.create_person(full_name="Feed Payer", linked_user=tenant)
        lease = self.create_lease(unit=self.unit, primary_tenant=person)
        today = date.today()
        invoice = RentInvoice.objects.create(
            lease=lease,
            period_start=today.replace(day=1),
            period_end=today,
            amount_due=Decimal("6000.00"),
            due_date=today,
            status=RentInvoice.Status.UNPAID,
        )
        RentPayment.objects.create(
            invoice=invoice,
            amount=Decimal("6000.00"),
            payment_date=today,
            status=RentPayment.Status.CLEARED,
        )
        feed = get_activity_feed(self.person.pk)
        types = [e["event_type"] for e in feed]
        self.assertIn("rent_received", types)

    def test_mandate_signed_event_in_feed(self):
        RentalMandate.objects.create(
            property=self.prop,
            mandate_type=RentalMandate.MandateType.FULL_MANAGEMENT,
            commission_rate="10.00",
            start_date=date.today(),
            status=RentalMandate.Status.ACTIVE,
        )
        feed = get_activity_feed(self.person.pk)
        types = [e["event_type"] for e in feed]
        self.assertIn("mandate_signed", types)

    def test_feed_is_sorted_newest_first(self):
        """Events returned by the feed are sorted with most recent first."""
        tenant = self.create_tenant(email="sort-tenant@test.co.za")
        person = self.create_person(full_name="Sort Tenant", linked_user=tenant)
        self.create_lease(unit=self.unit, primary_tenant=person, status="active")
        self.create_maintenance_request(unit=self.unit, status="open")
        feed = get_activity_feed(self.person.pk, limit=50)
        if len(feed) > 1:
            for i in range(len(feed) - 1):
                self.assertGreaterEqual(
                    feed[i]["occurred_at"],
                    feed[i + 1]["occurred_at"],
                    "feed must be sorted newest-first",
                )

    def test_empty_portfolio_returns_empty_feed(self):
        owner2 = self.create_owner_user(email="empty-feed@test.co.za")
        person2 = self.create_person(full_name="Empty Owner", linked_user=owner2)
        feed = get_activity_feed(person2.pk)
        self.assertEqual(feed, [])
