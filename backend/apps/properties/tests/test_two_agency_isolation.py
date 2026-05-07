"""
Phase 2.3 — two-agency isolation tests for the properties app viewsets.

Confirms that the AgencyScopedQuerysetMixin + AgencyStampedCreateMixin (now
applied to every properties viewset) actually prevent cross-tenant data
leakage in production code paths.

Setup: two agencies, each with one AGENCY_ADMIN user and one Property +
Landlord + Unit + ownership. We then exercise the Property, Unit,
Landlord, and PropertyOwnership endpoints from each tenant's perspective
and from an ADMIN perspective.

The mixin filters on `agency_id`. The existing role-based filter
(`get_accessible_property_ids`) layers on top, so cross-tenant rows are
blocked by *both* layers (defence in depth).
"""
from __future__ import annotations

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from django.test import TestCase

from apps.accounts.models import Agency, User
from apps.properties.models import (
    Landlord, Property, PropertyOwnership, Unit,
)


@pytest.mark.django_db
class TwoAgencyIsolationTestBase(TestCase):
    """Two agencies, two agency-admins, two property/landlord/unit triplets."""

    def setUp(self):
        self.agency_a = Agency.objects.create(name="Agency A")
        self.agency_b = Agency.objects.create(name="Agency B")

        self.user_a = User.objects.create_user(
            email="staff_a@x.com", password="pass", role=User.Role.AGENCY_ADMIN,
        )
        self.user_a.agency = self.agency_a
        self.user_a.save(update_fields=["agency"])

        self.user_b = User.objects.create_user(
            email="staff_b@x.com", password="pass", role=User.Role.AGENCY_ADMIN,
        )
        self.user_b.agency = self.agency_b
        self.user_b.save(update_fields=["agency"])

        self.admin = User.objects.create_user(
            email="admin@x.com", password="pass", role=User.Role.ADMIN,
        )

        # Property A + landlord A + unit + ownership — owned/managed by user_a
        self.prop_a = Property.objects.create(
            agency=self.agency_a, agent=self.user_a, name="A House",
            property_type="house", address="1 A St", city="C", province="WC",
            postal_code="0001",
        )
        self.landlord_a = Landlord.objects.create(
            agency=self.agency_a, name="Landlord A", landlord_type="individual",
            email="ll_a@x.com",
        )
        PropertyOwnership.objects.create(
            agency=self.agency_a, property=self.prop_a, landlord=self.landlord_a,
            is_current=True, owner_name="Owner", start_date="2025-01-01",
        )
        self.unit_a = Unit.objects.create(
            agency=self.agency_a, property=self.prop_a, unit_number="1",
            rent_amount=1000,
        )

        # Property B + landlord B + unit + ownership — owned/managed by user_b
        self.prop_b = Property.objects.create(
            agency=self.agency_b, agent=self.user_b, name="B House",
            property_type="house", address="1 B St", city="C", province="WC",
            postal_code="0002",
        )
        self.landlord_b = Landlord.objects.create(
            agency=self.agency_b, name="Landlord B", landlord_type="individual",
            email="ll_b@x.com",
        )
        PropertyOwnership.objects.create(
            agency=self.agency_b, property=self.prop_b, landlord=self.landlord_b,
            is_current=True, owner_name="Owner", start_date="2025-01-01",
        )
        self.unit_b = Unit.objects.create(
            agency=self.agency_b, property=self.prop_b, unit_number="1",
            rent_amount=2000,
        )

        # Force JSON to keep response handling clean.
        self.client = APIClient(HTTP_ACCEPT="application/json")


def _ids(resp):
    """Pull ids out of a DRF list response (paginated or not)."""
    body = resp.json()
    if isinstance(body, dict) and "results" in body:
        body = body["results"]
    return [row["id"] for row in body]


class PropertyViewSetIsolationTest(TwoAgencyIsolationTestBase):
    URL = "/api/v1/properties/"

    def test_user_a_lists_only_a_properties(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(_ids(resp), [self.prop_a.id])

    def test_user_a_cannot_retrieve_b_property(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(f"{self.URL}{self.prop_b.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_sees_all_properties(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(self.URL)
        self.assertEqual(
            sorted(_ids(resp)), sorted([self.prop_a.id, self.prop_b.id])
        )

    def test_create_stamps_users_agency_ignoring_payload(self):
        """User A POSTs with agency=B — server forces agency=A."""
        self.client.force_authenticate(self.user_a)
        resp = self.client.post(self.URL, {
            "name": "Forced", "property_type": "house",
            "address": "1 New St", "city": "C", "province": "WC",
            "postal_code": "0003",
            "agency": self.agency_b.id,
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        new_prop = Property.objects.get(name="Forced")
        self.assertEqual(new_prop.agency_id, self.agency_a.id)


class UnitViewSetIsolationTest(TwoAgencyIsolationTestBase):
    URL = "/api/v1/properties/units/"

    def test_user_a_lists_only_a_units(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(self.URL)
        self.assertEqual(_ids(resp), [self.unit_a.id])

    def test_user_a_cannot_retrieve_b_unit(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(f"{self.URL}{self.unit_b.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_sees_all_units(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(self.URL)
        self.assertEqual(
            sorted(_ids(resp)), sorted([self.unit_a.id, self.unit_b.id])
        )


class LandlordViewSetIsolationTest(TwoAgencyIsolationTestBase):
    URL = "/api/v1/properties/landlords/"

    def test_user_a_lists_only_a_landlords(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(self.URL)
        self.assertEqual(_ids(resp), [self.landlord_a.id])

    def test_user_a_cannot_retrieve_b_landlord(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(f"{self.URL}{self.landlord_b.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_sees_all_landlords(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(self.URL)
        self.assertEqual(
            sorted(_ids(resp)), sorted([self.landlord_a.id, self.landlord_b.id])
        )

    def test_create_landlord_stamps_users_agency(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.post(self.URL, {
            "name": "New Landlord",
            "landlord_type": "individual",
            "email": "new@x.com",
            "agency": self.agency_b.id,  # malicious override
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        new_ll = Landlord.objects.get(name="New Landlord")
        self.assertEqual(new_ll.agency_id, self.agency_a.id)


class PropertyOwnershipViewSetIsolationTest(TwoAgencyIsolationTestBase):
    URL = "/api/v1/properties/ownerships/"

    def test_user_a_lists_only_a_ownerships(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(self.URL)
        ids = _ids(resp)
        # Should only include ownership for prop_a/landlord_a, not B
        for pid in ids:
            row = PropertyOwnership.objects.get(pk=pid)
            self.assertEqual(row.agency_id, self.agency_a.id)

    def test_admin_sees_all_ownerships(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(self.URL)
        # At least the two we created — both visible.
        ids = _ids(resp)
        self.assertGreaterEqual(len(ids), 2)
