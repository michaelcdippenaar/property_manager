"""
Phase 2.7 — two-agency isolation tests for the tenant app viewsets.

Confirms that AgencyScopedQuerysetMixin (now applied to TenantViewSet,
TenantUnitAssignmentViewSet) and the explicit agency filter on the
agency-staff branch of TenantOnboardingViewSet prevent cross-tenant
data leakage.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Agency, Person, User
from apps.leases.models import Lease
from apps.properties.models import Property, Unit
from apps.tenant.models import Tenant, TenantOnboarding


@pytest.mark.django_db
class _TwoAgencyBase(TestCase):
    def setUp(self):
        self.agency_a = Agency.objects.create(name="Agency A (tenant)")
        self.agency_b = Agency.objects.create(name="Agency B (tenant)")

        self.staff_a = User.objects.create_user(
            email="t_a@x.com", password="pass", role=User.Role.AGENCY_ADMIN,
        )
        self.staff_a.agency = self.agency_a
        self.staff_a.save(update_fields=["agency"])

        self.staff_b = User.objects.create_user(
            email="t_b@x.com", password="pass", role=User.Role.AGENCY_ADMIN,
        )
        self.staff_b.agency = self.agency_b
        self.staff_b.save(update_fields=["agency"])

        self.admin = User.objects.create_user(
            email="t_admin@x.com", password="pass", role=User.Role.ADMIN,
        )

        # Person + Tenant for each agency
        self.person_a = Person.objects.create(
            agency=self.agency_a, full_name="Tenant A", person_type=Person.PersonType.INDIVIDUAL,
        )
        self.tenant_a = Tenant.objects.create(agency=self.agency_a, person=self.person_a)
        self.person_b = Person.objects.create(
            agency=self.agency_b, full_name="Tenant B", person_type=Person.PersonType.INDIVIDUAL,
        )
        self.tenant_b = Tenant.objects.create(agency=self.agency_b, person=self.person_b)

        # Lease + onboarding for each agency
        self.prop_a = Property.objects.create(
            agency=self.agency_a, agent=self.staff_a, name="A", property_type="house",
            address="1 A St", city="C", province="WC", postal_code="0001",
        )
        self.unit_a = Unit.objects.create(
            agency=self.agency_a, property=self.prop_a, unit_number="1", rent_amount=Decimal("1000"),
        )
        self.lease_a = Lease.objects.create(
            agency=self.agency_a, unit=self.unit_a, primary_tenant=self.person_a,
            start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
            monthly_rent=Decimal("1000"), status=Lease.Status.ACTIVE,
        )
        # Lease creation may auto-create the onboarding via signals; fall back
        # to a get_or_create so the test setup is idempotent either way.
        self.onb_a, _ = TenantOnboarding.objects.get_or_create(
            lease=self.lease_a, defaults={"agency": self.agency_a},
        )
        if self.onb_a.agency_id is None:
            self.onb_a.agency = self.agency_a
            self.onb_a.save(update_fields=["agency"])

        self.prop_b = Property.objects.create(
            agency=self.agency_b, agent=self.staff_b, name="B", property_type="house",
            address="1 B St", city="C", province="WC", postal_code="0002",
        )
        self.unit_b = Unit.objects.create(
            agency=self.agency_b, property=self.prop_b, unit_number="1", rent_amount=Decimal("2000"),
        )
        self.lease_b = Lease.objects.create(
            agency=self.agency_b, unit=self.unit_b, primary_tenant=self.person_b,
            start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
            monthly_rent=Decimal("2000"), status=Lease.Status.ACTIVE,
        )
        self.onb_b, _ = TenantOnboarding.objects.get_or_create(
            lease=self.lease_b, defaults={"agency": self.agency_b},
        )
        if self.onb_b.agency_id is None:
            self.onb_b.agency = self.agency_b
            self.onb_b.save(update_fields=["agency"])

        self.client = APIClient(HTTP_ACCEPT="application/json")


def _ids(resp):
    body = resp.json()
    if isinstance(body, dict) and "results" in body:
        body = body["results"]
    return [row["id"] for row in body]


class TenantViewSetIsolationTest(_TwoAgencyBase):
    URL = "/api/v1/tenant/tenants/"

    def test_staff_a_lists_only_a_tenants(self):
        self.client.force_authenticate(self.staff_a)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = _ids(resp)
        self.assertIn(self.tenant_a.id, ids)
        self.assertNotIn(self.tenant_b.id, ids)

    def test_staff_a_cannot_retrieve_b_tenant(self):
        self.client.force_authenticate(self.staff_a)
        resp = self.client.get(f"{self.URL}{self.tenant_b.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_sees_all_tenants(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(self.URL)
        ids = _ids(resp)
        self.assertIn(self.tenant_a.id, ids)
        self.assertIn(self.tenant_b.id, ids)


class TenantOnboardingIsolationTest(_TwoAgencyBase):
    URL = "/api/v1/tenant/onboarding/"

    def test_staff_a_lists_only_a_onboardings(self):
        self.client.force_authenticate(self.staff_a)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = _ids(resp)
        self.assertIn(self.onb_a.id, ids)
        self.assertNotIn(self.onb_b.id, ids)
