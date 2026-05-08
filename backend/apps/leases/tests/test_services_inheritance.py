"""
Feature 3 — Property services & facilities inherit to lease at create time.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.test import TestCase

from apps.accounts.models import Agency
from apps.leases.models import Lease
from apps.properties.models import Property, Unit


@pytest.mark.django_db
class TestServicesInheritance(TestCase):
    def setUp(self):
        self.agency = Agency.objects.create(name="Test Agency")
        self.prop = Property.objects.create(
            agency=self.agency, name="Test", property_type="house",
            address="1 Test St", city="C", province="WC", postal_code="0001",
            water_arrangement="included",
            electricity_arrangement="prepaid",
            gardening_service_included=True,
            wifi_included=True,
            security_service_included=True,
        )
        self.unit = Unit.objects.create(
            agency=self.agency, property=self.prop, unit_number="1",
            rent_amount=Decimal("5000"),
        )

    def _make_lease(self, **kw):
        return Lease.objects.create(
            agency=self.agency, unit=self.unit,
            start_date=date.today(), end_date=date.today() + timedelta(days=365),
            monthly_rent=Decimal("5000"),
            **kw,
        )

    def test_lease_inherits_property_services(self):
        lease = self._make_lease()
        self.assertEqual(lease.water_arrangement, "included")
        self.assertEqual(lease.electricity_arrangement, "prepaid")
        self.assertTrue(lease.gardening_service_included)
        self.assertTrue(lease.wifi_included)
        self.assertTrue(lease.security_service_included)

    def test_lease_post_create_override_persists(self):
        # Inheritance only fires on first save (no pk). Subsequent edits stick.
        lease = self._make_lease()
        self.assertEqual(lease.water_arrangement, "included")
        lease.water_arrangement = "not_included"
        lease.electricity_arrangement = "eskom_direct"
        lease.gardening_service_included = False
        lease.save()
        lease.refresh_from_db()
        self.assertEqual(lease.water_arrangement, "not_included")
        self.assertEqual(lease.electricity_arrangement, "eskom_direct")
        self.assertFalse(lease.gardening_service_included)

    def test_lease_with_no_property_defaults_uses_field_defaults(self):
        plain_prop = Property.objects.create(
            agency=self.agency, name="Plain", property_type="house",
            address="2 Plain St", city="C", province="WC", postal_code="0001",
        )
        plain_unit = Unit.objects.create(
            agency=self.agency, property=plain_prop, unit_number="1",
            rent_amount=Decimal("5000"),
        )
        lease = Lease.objects.create(
            agency=self.agency, unit=plain_unit,
            start_date=date.today(), end_date=date.today() + timedelta(days=365),
            monthly_rent=Decimal("5000"),
        )
        self.assertEqual(lease.water_arrangement, "not_included")
        self.assertEqual(lease.electricity_arrangement, "not_included")
        self.assertFalse(lease.gardening_service_included)
        self.assertFalse(lease.wifi_included)
        self.assertFalse(lease.security_service_included)
