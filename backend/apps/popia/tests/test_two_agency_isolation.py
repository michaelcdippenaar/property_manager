"""
Phase 2.6 — two-agency isolation tests for the popia app views.

Two flows on the popia endpoints:

  • Subject-side (POST /data-export/, /erasure-request/, GET /my-requests/) —
    a tenant-style data subject creates a DSAR for themselves. The mixin is
    NOT applied here; scoping is by ``requester=request.user``.

  • Reviewer-side (GET /dsar-queue/, GET/POST /dsar-queue/<id>/review/) —
    agency staff reviewing requests against their tenant. Hard agency
    boundary: agency A reviewers must never see agency B's queue.

Setup: two agencies, each with one AGENCY_ADMIN reviewer + one tenant
data subject + one DSARRequest. Plus an ADMIN user that bypasses scoping.
"""
from __future__ import annotations

import pytest
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Agency, User
from apps.popia.models import DSARRequest


@pytest.mark.django_db
class PopiaTwoAgencyIsolationBase(TestCase):
    def setUp(self):
        self.agency_a = Agency.objects.create(name="Agency A")
        self.agency_b = Agency.objects.create(name="Agency B")

        self.reviewer_a = User.objects.create_user(
            email="rev_a@x.com", password="pass", role=User.Role.AGENCY_ADMIN,
        )
        self.reviewer_a.agency = self.agency_a
        self.reviewer_a.save(update_fields=["agency"])

        self.reviewer_b = User.objects.create_user(
            email="rev_b@x.com", password="pass", role=User.Role.AGENCY_ADMIN,
        )
        self.reviewer_b.agency = self.agency_b
        self.reviewer_b.save(update_fields=["agency"])

        self.admin = User.objects.create_user(
            email="admin@x.com", password="pass", role=User.Role.ADMIN,
        )

        # Subject A — agency-staff user; their DSAR carries agency_a
        self.subject_a = User.objects.create_user(
            email="subj_a@x.com", password="pass", role=User.Role.TENANT,
        )
        self.subject_a.agency = self.agency_a
        self.subject_a.save(update_fields=["agency"])

        self.subject_b = User.objects.create_user(
            email="subj_b@x.com", password="pass", role=User.Role.TENANT,
        )
        self.subject_b.agency = self.agency_b
        self.subject_b.save(update_fields=["agency"])

        self.dsar_a = DSARRequest.objects.create(
            requester=self.subject_a,
            requester_email=self.subject_a.email,
            agency=self.agency_a,
            request_type=DSARRequest.RequestType.SAR,
            status=DSARRequest.Status.PENDING,
        )
        self.dsar_b = DSARRequest.objects.create(
            requester=self.subject_b,
            requester_email=self.subject_b.email,
            agency=self.agency_b,
            request_type=DSARRequest.RequestType.SAR,
            status=DSARRequest.Status.PENDING,
        )

        self.client = APIClient(HTTP_ACCEPT="application/json")


def _list_ids(resp):
    body = resp.json()
    if isinstance(body, dict) and "results" in body:
        body = body["results"]
    return [row["id"] for row in body]


class DSARQueueIsolationTest(PopiaTwoAgencyIsolationBase):
    URL = "/api/v1/popia/dsar-queue/"

    def test_reviewer_a_sees_only_a_queue(self):
        self.client.force_authenticate(self.reviewer_a)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = _list_ids(resp)
        self.assertIn(self.dsar_a.id, ids)
        self.assertNotIn(self.dsar_b.id, ids)

    def test_admin_sees_full_queue(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(self.URL)
        ids = _list_ids(resp)
        self.assertIn(self.dsar_a.id, ids)
        self.assertIn(self.dsar_b.id, ids)


class DSARReviewIsolationTest(PopiaTwoAgencyIsolationBase):
    def url(self, pk):
        return f"/api/v1/popia/dsar-queue/{pk}/review/"

    def test_reviewer_a_cross_tenant_review_404(self):
        self.client.force_authenticate(self.reviewer_a)
        resp = self.client.get(self.url(self.dsar_b.id))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_reviewer_a_can_review_own_dsar(self):
        self.client.force_authenticate(self.reviewer_a)
        resp = self.client.get(self.url(self.dsar_a.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_admin_can_review_any_dsar(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(self.url(self.dsar_b.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class SubjectSideAgencyStampTest(PopiaTwoAgencyIsolationBase):
    """
    Subject-side endpoints are scoped by requester=request.user, not by
    agency. Verify that creating a SAR/RTBF stamps the subject's
    agency_id so it later shows up in the right reviewer's queue.
    """

    def test_sar_create_stamps_subjects_agency(self):
        # Clear existing fixtures so the create path runs clean.
        DSARRequest.objects.all().delete()
        self.client.force_authenticate(self.subject_a)
        resp = self.client.post("/api/v1/popia/data-export/", {"reason": "x"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        new = DSARRequest.objects.get(requester=self.subject_a)
        self.assertEqual(new.agency_id, self.agency_a.id)

    def test_my_requests_returns_only_subjects_own(self):
        self.client.force_authenticate(self.subject_a)
        resp = self.client.get("/api/v1/popia/my-requests/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [row["id"] for row in resp.json()]
        self.assertIn(self.dsar_a.id, ids)
        self.assertNotIn(self.dsar_b.id, ids)
