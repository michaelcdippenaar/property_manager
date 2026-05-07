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
