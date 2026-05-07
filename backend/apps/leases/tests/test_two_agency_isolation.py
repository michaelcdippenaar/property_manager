"""
Phase 2.4 — two-agency isolation tests for the leases app viewsets.

Confirms that the AgencyScopedQuerysetMixin + AgencyStampedCreateMixin (now
applied to every leases viewset) prevent cross-tenant data leakage in
production code paths for Lease, LeaseTemplate, and ReusableClause endpoints.

Setup: two agencies, each with one AGENCY_ADMIN + one Property + Unit + Lease
+ LeaseTemplate. We exercise list / retrieve / create from each tenant's
perspective and from an ADMIN perspective.

The mixin filters on `agency_id`. Existing role/property scoping (where
present) layers on top — defence in depth.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Agency, User
from apps.leases.models import Lease, LeaseTemplate, ReusableClause
from apps.properties.models import Property, Unit


@pytest.mark.django_db
class TwoAgencyLeaseIsolationTestBase(TestCase):
    """Two agencies, two agency-admins, two property/unit/lease/template sets."""

    def setUp(self):
        self.agency_a = Agency.objects.create(name="Agency LA")
        self.agency_b = Agency.objects.create(name="Agency LB")

        self.user_a = User.objects.create_user(
            email="leasestaff_a@x.com", password="pass", role=User.Role.AGENCY_ADMIN,
        )
        self.user_a.agency = self.agency_a
        self.user_a.save(update_fields=["agency"])

        self.user_b = User.objects.create_user(
            email="leasestaff_b@x.com", password="pass", role=User.Role.AGENCY_ADMIN,
        )
        self.user_b.agency = self.agency_b
        self.user_b.save(update_fields=["agency"])

        self.admin = User.objects.create_user(
            email="leaseadmin@x.com", password="pass", role=User.Role.ADMIN,
        )

        # Agency A — property + unit + lease + template + clause
        self.prop_a = Property.objects.create(
            agency=self.agency_a, agent=self.user_a, name="LA House",
            property_type="house", address="1 LA St", city="C", province="WC",
            postal_code="0001",
        )
        self.unit_a = Unit.objects.create(
            agency=self.agency_a, property=self.prop_a, unit_number="1",
            rent_amount=Decimal("5000"),
        )
        self.lease_a = Lease.objects.create(
            agency=self.agency_a, unit=self.unit_a,
            start_date=date.today(), end_date=date.today() + timedelta(days=365),
            monthly_rent=Decimal("5000"), deposit=Decimal("10000"),
            status=Lease.Status.ACTIVE,
            notice_period_days=30,
            escalation_clause="CPI annual.",
            renewal_clause="By mutual written agreement.",
            domicilium_address="1 LA St, C, 0001",
        )
        self.template_a = LeaseTemplate.objects.create(
            agency=self.agency_a, name="LA Template", content_html="<p>A</p>",
        )
        self.clause_a = ReusableClause.objects.create(
            agency=self.agency_a, created_by=self.user_a,
            title="A Clause", category="general", html="<p>A clause</p>",
        )

        # Agency B
        self.prop_b = Property.objects.create(
            agency=self.agency_b, agent=self.user_b, name="LB House",
            property_type="house", address="1 LB St", city="C", province="WC",
            postal_code="0002",
        )
        self.unit_b = Unit.objects.create(
            agency=self.agency_b, property=self.prop_b, unit_number="1",
            rent_amount=Decimal("6000"),
        )
        self.lease_b = Lease.objects.create(
            agency=self.agency_b, unit=self.unit_b,
            start_date=date.today(), end_date=date.today() + timedelta(days=365),
            monthly_rent=Decimal("6000"), deposit=Decimal("12000"),
            status=Lease.Status.ACTIVE,
            notice_period_days=30,
            escalation_clause="CPI annual.",
            renewal_clause="By mutual written agreement.",
            domicilium_address="1 LB St, C, 0002",
        )
        self.template_b = LeaseTemplate.objects.create(
            agency=self.agency_b, name="LB Template", content_html="<p>B</p>",
        )
        self.clause_b = ReusableClause.objects.create(
            agency=self.agency_b, created_by=self.user_b,
            title="B Clause", category="general", html="<p>B clause</p>",
        )

        self.client = APIClient(HTTP_ACCEPT="application/json")


def _ids(resp):
    body = resp.json()
    if isinstance(body, dict) and "results" in body:
        body = body["results"]
    return [row["id"] for row in body]


class LeaseViewSetIsolationTest(TwoAgencyLeaseIsolationTestBase):
    URL = "/api/v1/leases/"

    def test_user_a_lists_only_a_leases(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(_ids(resp), [self.lease_a.id])

    def test_user_a_cannot_retrieve_b_lease(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(f"{self.URL}{self.lease_b.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_sees_all_leases(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(self.URL)
        self.assertEqual(
            sorted(_ids(resp)), sorted([self.lease_a.id, self.lease_b.id])
        )

    def test_create_stamps_users_agency_ignoring_payload(self):
        """User A POSTs lease with agency=B in payload — server forces agency=A."""
        self.client.force_authenticate(self.user_a)
        resp = self.client.post(self.URL, {
            "unit": self.unit_a.id,
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=365)),
            "monthly_rent": "5000.00",
            "deposit": "10000.00",
            "status": "pending",
            "notice_period_days": 30,
            "escalation_clause": "CPI annual.",
            "renewal_clause": "By mutual.",
            "domicilium_address": "1 LA St, C, 0001",
            "agency": self.agency_b.id,  # malicious override
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        new_lease = Lease.objects.get(pk=resp.json()["id"])
        self.assertEqual(new_lease.agency_id, self.agency_a.id)


class LeaseTemplateViewIsolationTest(TwoAgencyLeaseIsolationTestBase):
    URL = "/api/v1/leases/templates/"

    def test_user_a_lists_only_a_templates(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(_ids(resp), [self.template_a.id])

    def test_user_a_cannot_retrieve_b_template(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(f"{self.URL}{self.template_b.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_sees_all_templates(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(self.URL)
        ids = _ids(resp)
        self.assertIn(self.template_a.id, ids)
        self.assertIn(self.template_b.id, ids)

    def test_create_stamps_users_agency(self):
        """User A creates a blank template — agency_id must be A's, even if
        the request body claims agency=B."""
        self.client.force_authenticate(self.user_a)
        resp = self.client.post(self.URL, {
            "name": "Forced template A",
            "content_html": "<p>x</p>",
            "agency": self.agency_b.id,
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        new_tmpl = LeaseTemplate.objects.get(name="Forced template A")
        self.assertEqual(new_tmpl.agency_id, self.agency_a.id)


class ReusableClauseViewIsolationTest(TwoAgencyLeaseIsolationTestBase):
    URL = "/api/v1/leases/clauses/"

    def test_user_a_lists_only_a_clauses(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = _ids(resp)
        self.assertEqual(ids, [self.clause_a.id])

    def test_user_a_cannot_retrieve_b_clause_via_destroy(self):
        # The destroy endpoint also gates retrieve via the queryset filter.
        self.client.force_authenticate(self.user_a)
        resp = self.client.delete(f"{self.URL}{self.clause_b.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_stamps_users_agency(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.post(self.URL, {
            "title": "Forced clause",
            "category": "general",
            "html": "<p>y</p>",
            "agency": self.agency_b.id,
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        new_clause = ReusableClause.objects.get(title="Forced clause")
        self.assertEqual(new_clause.agency_id, self.agency_a.id)


# ---------------------------------------------------------------------------
# Post-review regression tests — cross-agency Person leak fixes
# ---------------------------------------------------------------------------

from apps.accounts.models import Person


class ImportLeasePersonScopingTest(TwoAgencyLeaseIsolationTestBase):
    """Regression for Bug 2 — _get_or_create_person scoping in import."""

    def test_import_does_not_reuse_other_agency_person_by_id_number(self):
        # Agency B already has a Person with this ID number. Agency A's
        # import must NOT reuse that Person (it would silently leak the row).
        from apps.leases.import_view import _get_or_create_person

        Person.objects.create(
            agency=self.agency_b, full_name="Bob Foreigner",
            id_number="9001015009087",
        )
        person = _get_or_create_person(
            {
                "full_name": "Alice Local",
                "id_number": "9001015009087",  # collides with agency B's row
            },
            agency_id=self.agency_a.id,
        )
        self.assertEqual(person.agency_id, self.agency_a.id)
        self.assertEqual(person.full_name, "Alice Local")

    def test_import_creates_person_with_caller_agency_id(self):
        from apps.leases.import_view import _get_or_create_person

        person = _get_or_create_person(
            {"full_name": "Fresh Tenant", "id_number": "8501015009088"},
            agency_id=self.agency_a.id,
        )
        self.assertIsNotNone(person.agency_id)
        self.assertEqual(person.agency_id, self.agency_a.id)


class AddTenantCrossAgencyTest(TwoAgencyLeaseIsolationTestBase):
    """Regression for Bug 3 — add_tenant must not attach foreign Persons."""

    def test_add_tenant_rejects_cross_agency_person_pk(self):
        person_b = Person.objects.create(
            agency=self.agency_b, full_name="Foreign Tenant",
        )
        self.client.force_authenticate(self.user_a)
        resp = self.client.post(
            f"/api/v1/leases/{self.lease_a.id}/tenants/",
            {"person_id": person_b.id},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_tenant_with_new_person_stamps_agency(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.post(
            f"/api/v1/leases/{self.lease_a.id}/tenants/",
            {"person": {"full_name": "Brand New Co-tenant", "person_type": "individual"}},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        new_person = Person.objects.get(full_name="Brand New Co-tenant")
        self.assertEqual(new_person.agency_id, self.agency_a.id)
