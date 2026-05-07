"""
Phase 2.6 — two-agency isolation tests for the esigning app views.

Authenticated staff endpoints (submission list / detail / signer status /
download / documents / public-link create) layer agency_id on top of the
existing property/lease scoping. Agency A staff must never see agency B's
ESigningSubmission rows.

Public/anonymous signing endpoints (resolved by UUID token) intentionally
have NO mixin — they authenticate by token validity, not by request.user.
We do not test those in this file (they are covered by lease-flow tests).
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Agency, User
from apps.esigning.models import ESigningSubmission
from apps.leases.models import Lease
from apps.properties.models import Property, Unit


@pytest.mark.django_db
class ESigningTwoAgencyIsolationBase(TestCase):
    def setUp(self):
        self.agency_a = Agency.objects.create(name="Agency EA")
        self.agency_b = Agency.objects.create(name="Agency EB")

        self.user_a = User.objects.create_user(
            email="esa@x.com", password="pass", role=User.Role.AGENCY_ADMIN,
        )
        self.user_a.agency = self.agency_a
        self.user_a.save(update_fields=["agency"])

        self.user_b = User.objects.create_user(
            email="esb@x.com", password="pass", role=User.Role.AGENCY_ADMIN,
        )
        self.user_b.agency = self.agency_b
        self.user_b.save(update_fields=["agency"])

        self.admin = User.objects.create_user(
            email="esadmin@x.com", password="pass", role=User.Role.ADMIN,
        )

        # Agency A — property + unit + lease + submission
        self.prop_a = Property.objects.create(
            agency=self.agency_a, agent=self.user_a, name="EA House",
            property_type="house", address="1 EA St", city="C", province="WC",
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
            status=Lease.Status.ACTIVE, notice_period_days=30,
            escalation_clause="x", renewal_clause="x",
            domicilium_address="1 EA St",
        )
        self.sub_a = ESigningSubmission.objects.create(
            agency=self.agency_a, lease=self.lease_a,
            signing_backend=ESigningSubmission.SigningBackend.NATIVE,
            status=ESigningSubmission.Status.PENDING,
            signers=[],
            document_html="<p>A</p>",
        )

        # Agency B
        self.prop_b = Property.objects.create(
            agency=self.agency_b, agent=self.user_b, name="EB House",
            property_type="house", address="1 EB St", city="C", province="WC",
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
            status=Lease.Status.ACTIVE, notice_period_days=30,
            escalation_clause="x", renewal_clause="x",
            domicilium_address="1 EB St",
        )
        self.sub_b = ESigningSubmission.objects.create(
            agency=self.agency_b, lease=self.lease_b,
            signing_backend=ESigningSubmission.SigningBackend.NATIVE,
            status=ESigningSubmission.Status.PENDING,
            signers=[],
            document_html="<p>B</p>",
        )

        self.client = APIClient(HTTP_ACCEPT="application/json")


def _ids(resp):
    body = resp.json()
    if isinstance(body, dict) and "results" in body:
        body = body["results"]
    return [row["id"] for row in body]


class ESigningSubmissionListIsolationTest(ESigningTwoAgencyIsolationBase):
    URL = "/api/v1/esigning/submissions/"

    def test_user_a_lists_only_a_submissions(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = _ids(resp)
        self.assertIn(self.sub_a.id, ids)
        self.assertNotIn(self.sub_b.id, ids)

    def test_user_a_cannot_retrieve_b_submission(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(f"{self.URL}{self.sub_b.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_sees_all(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(self.URL)
        ids = _ids(resp)
        self.assertIn(self.sub_a.id, ids)
        self.assertIn(self.sub_b.id, ids)

    def test_user_a_cross_tenant_signer_status_404(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(f"{self.URL}{self.sub_b.id}/signer-status/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_a_cross_tenant_documents_blocked(self):
        """Either 404 (scope-filtered) or 403 (role-blocked) is acceptable —
        both prevent agency A from reading agency B's documents."""
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(f"{self.URL}{self.sub_b.id}/documents/")
        self.assertIn(
            resp.status_code,
            (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
        )
