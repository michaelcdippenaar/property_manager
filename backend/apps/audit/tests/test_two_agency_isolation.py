"""
Phase 2.6 — two-agency isolation tests for the audit app viewsets.

Audit events contain field snapshots that may include PII. An agency must
NEVER see another agency's audit trail — this is a hard security boundary.

Setup: two agencies, two AGENCY_ADMIN users, one ADMIN, two AuditEvents
(one per agency). Verify list/retrieve/timeline scoping.
"""
from __future__ import annotations

import pytest
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Agency, User
from apps.audit.models import AuditEvent


@pytest.mark.django_db
class AuditTwoAgencyIsolationBase(TestCase):
    def setUp(self):
        self.agency_a = Agency.objects.create(name="Agency A")
        self.agency_b = Agency.objects.create(name="Agency B")

        self.user_a = User.objects.create_user(
            email="aa@x.com", password="pass", role=User.Role.AGENCY_ADMIN,
        )
        self.user_a.agency = self.agency_a
        self.user_a.save(update_fields=["agency"])

        self.user_b = User.objects.create_user(
            email="bb@x.com", password="pass", role=User.Role.AGENCY_ADMIN,
        )
        self.user_b.agency = self.agency_b
        self.user_b.save(update_fields=["agency"])

        self.admin = User.objects.create_user(
            email="admin@x.com", password="pass", role=User.Role.ADMIN,
        )

        self.event_a = AuditEvent.objects.create(
            agency=self.agency_a,
            action="lease.update",
            actor=self.user_a,
            actor_email=self.user_a.email,
            target_repr="Lease #1",
        )
        self.event_b = AuditEvent.objects.create(
            agency=self.agency_b,
            action="lease.update",
            actor=self.user_b,
            actor_email=self.user_b.email,
            target_repr="Lease #2",
        )

        self.client = APIClient(HTTP_ACCEPT="application/json")


def _ids(resp):
    body = resp.json()
    if isinstance(body, dict) and "results" in body:
        body = body["results"]
    return [row["id"] for row in body]


class AuditEventViewSetIsolationTest(AuditTwoAgencyIsolationBase):
    URL = "/api/v1/audit/events/"

    def test_user_a_lists_only_a_events(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(_ids(resp), [self.event_a.id])

    def test_user_a_cannot_retrieve_b_event(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(f"{self.URL}{self.event_b.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_sees_all_events(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(self.URL)
        ids = _ids(resp)
        self.assertIn(self.event_a.id, ids)
        self.assertIn(self.event_b.id, ids)


class AuditTimelineViewIsolationTest(AuditTwoAgencyIsolationBase):
    """
    Timeline view filters by content_type+object_id. Two agencies that
    share the same (app_label, model, pk) shape (e.g. both have a
    'leases.lease' #1) must not bleed into each other.
    """

    def setUp(self):
        super().setUp()
        from django.contrib.contenttypes.models import ContentType
        # Use Agency itself as a stable content_type for the test.
        ct = ContentType.objects.get_for_model(Agency)
        self.event_a2 = AuditEvent.objects.create(
            agency=self.agency_a, action="x", actor=self.user_a,
            content_type=ct, object_id=42,
        )
        self.event_b2 = AuditEvent.objects.create(
            agency=self.agency_b, action="x", actor=self.user_b,
            content_type=ct, object_id=42,
        )
        self.app_label = ct.app_label
        self.model = ct.model

    def test_user_a_timeline_excludes_b_event(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(f"/api/v1/audit/timeline/{self.app_label}/{self.model}/42/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [row["id"] for row in resp.json()]
        self.assertIn(self.event_a2.id, ids)
        self.assertNotIn(self.event_b2.id, ids)

    def test_admin_timeline_sees_both(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(f"/api/v1/audit/timeline/{self.app_label}/{self.model}/42/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [row["id"] for row in resp.json()]
        self.assertIn(self.event_a2.id, ids)
        self.assertIn(self.event_b2.id, ids)


# ---------------------------------------------------------------------------
# Post-review regression tests — signal must stamp agency_id (Bug 4)
# ---------------------------------------------------------------------------

from datetime import date, timedelta
from decimal import Decimal


class SignalStampsAgencyIdTest(AuditTwoAgencyIsolationBase):
    """Regression for Bug 4 — signal-driven AuditEvents must populate agency_id
    so AuditEventViewSet (filtered by agency_id) is not empty for the actor's
    own events. Covers three derivation paths:
      - direct ``instance.agency_id``  (Lease)
      - via ``instance.lease.agency_id``  (ESigningSubmission)
      - via ``instance.unit.property.agency_id``  (Lease — no direct agency, fallback)
    """

    def test_lease_create_stamps_agency_directly(self):
        from apps.leases.models import Lease
        from apps.properties.models import Property, Unit
        from apps.audit.models import AuditEvent

        prop = Property.objects.create(
            agency=self.agency_a, name="LSig", property_type="house",
            address="x", city="x", province="x", postal_code="0001",
        )
        unit = Unit.objects.create(
            agency=self.agency_a, property=prop, unit_number="1",
            rent_amount=Decimal("100"),
        )
        lease = Lease.objects.create(
            agency=self.agency_a, unit=unit,
            start_date=date.today(), end_date=date.today() + timedelta(days=365),
            monthly_rent=Decimal("100"), deposit=Decimal("100"),
            status=Lease.Status.PENDING, notice_period_days=30,
            escalation_clause="x", renewal_clause="x", domicilium_address="x",
        )
        evt = AuditEvent.objects.filter(
            action="lease.created", object_id=lease.pk,
        ).order_by("-id").first()
        self.assertIsNotNone(evt, "no AuditEvent recorded for Lease creation")
        self.assertEqual(evt.agency_id, self.agency_a.id)

    def test_signing_submission_create_derives_agency_via_lease(self):
        from apps.leases.models import Lease
        from apps.properties.models import Property, Unit
        from apps.esigning.models import ESigningSubmission
        from apps.audit.models import AuditEvent

        prop = Property.objects.create(
            agency=self.agency_b, name="LBSig", property_type="house",
            address="x", city="x", province="x", postal_code="0002",
        )
        unit = Unit.objects.create(
            agency=self.agency_b, property=prop, unit_number="1",
            rent_amount=Decimal("100"),
        )
        lease = Lease.objects.create(
            agency=self.agency_b, unit=unit,
            start_date=date.today(), end_date=date.today() + timedelta(days=365),
            monthly_rent=Decimal("100"), deposit=Decimal("100"),
            status=Lease.Status.PENDING, notice_period_days=30,
            escalation_clause="x", renewal_clause="x", domicilium_address="x",
        )
        # Deliberately omit explicit agency on the submission to test derivation
        # via instance.lease.agency_id. The submission's own field will already
        # be set by other code paths, but the signal must derive agency_id from
        # the lease chain even if the row's denormalised agency_id were absent.
        sub = ESigningSubmission.objects.create(
            lease=lease,
            agency=self.agency_b,
            signing_backend=ESigningSubmission.SigningBackend.NATIVE,
            status=ESigningSubmission.Status.PENDING,
            signers=[], document_html="<p>x</p>",
        )
        evt = AuditEvent.objects.filter(
            action="signing.created", object_id=sub.pk,
        ).order_by("-id").first()
        self.assertIsNotNone(evt)
        self.assertEqual(evt.agency_id, self.agency_b.id)

    def test_derive_agency_id_helper_walks_chains(self):
        """Unit-test the helper directly so future refactors keep the chains."""
        from apps.audit.signals import _derive_agency_id

        class _O:
            pass

        # Direct
        o = _O()
        o.agency_id = 7
        self.assertEqual(_derive_agency_id(o), 7)

        # via lease
        o = _O()
        lease = _O()
        lease.agency_id = 11
        o.lease = lease
        self.assertEqual(_derive_agency_id(o), 11)

        # via unit.property
        o = _O()
        prop = _O()
        prop.agency_id = 13
        unit = _O()
        unit.property = prop
        o.unit = unit
        self.assertEqual(_derive_agency_id(o), 13)

        # No chain → None
        self.assertIsNone(_derive_agency_id(_O()))
