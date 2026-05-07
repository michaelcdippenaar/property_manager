"""
Phase 2.7 — two-agency isolation tests for the accounts app viewsets.

Confirms that AgencyScopedQuerysetMixin (now applied to UserListView,
PersonViewSet, PersonDetailView, PersonDocumentListCreateView,
PersonDocumentDetailView, TenantsListView) and the explicit agency
filter on the invite endpoints + AgencySettingsView prevent cross-tenant
data leakage in production code paths.
"""
from __future__ import annotations

import pytest
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Agency, Person, User, UserInvite


@pytest.mark.django_db
class _TwoAgencyBase(TestCase):
    def setUp(self):
        self.agency_a = Agency.objects.create(name="Agency A (accounts)")
        self.agency_b = Agency.objects.create(name="Agency B (accounts)")

        self.user_a = User.objects.create_user(
            email="acct_a@x.com", password="pass", role=User.Role.AGENCY_ADMIN,
        )
        self.user_a.agency = self.agency_a
        self.user_a.save(update_fields=["agency"])

        self.user_b = User.objects.create_user(
            email="acct_b@x.com", password="pass", role=User.Role.AGENCY_ADMIN,
        )
        self.user_b.agency = self.agency_b
        self.user_b.save(update_fields=["agency"])

        self.admin = User.objects.create_user(
            email="acct_admin@x.com", password="pass", role=User.Role.ADMIN,
        )

        # Person rows in each agency
        self.person_a = Person.objects.create(
            agency=self.agency_a, full_name="Person A", person_type=Person.PersonType.INDIVIDUAL,
        )
        self.person_b = Person.objects.create(
            agency=self.agency_b, full_name="Person B", person_type=Person.PersonType.INDIVIDUAL,
        )

        # Pending invite per agency
        self.invite_a = UserInvite.objects.create(
            email="newuser_a@x.com",
            role="viewer",
            agency=self.agency_a,
            invited_by=self.user_a,
        )
        self.invite_b = UserInvite.objects.create(
            email="newuser_b@x.com",
            role="viewer",
            agency=self.agency_b,
            invited_by=self.user_b,
        )

        self.client = APIClient(HTTP_ACCEPT="application/json")


def _ids(resp):
    body = resp.json()
    if isinstance(body, dict) and "results" in body:
        body = body["results"]
    return [row["id"] for row in body]


class UserListViewIsolationTest(_TwoAgencyBase):
    URL = "/api/v1/auth/users/"

    def test_user_a_lists_only_a_users(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = set(_ids(resp))
        self.assertIn(self.user_a.id, ids)
        self.assertNotIn(self.user_b.id, ids)

    def test_admin_sees_all_users(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = set(_ids(resp))
        self.assertIn(self.user_a.id, ids)
        self.assertIn(self.user_b.id, ids)


class PersonViewSetIsolationTest(_TwoAgencyBase):
    URL = "/api/v1/auth/persons/"

    def test_user_a_lists_only_a_persons(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = _ids(resp)
        self.assertIn(self.person_a.id, ids)
        self.assertNotIn(self.person_b.id, ids)

    def test_user_a_cannot_retrieve_b_person(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(f"/api/v1/auth/persons/{self.person_b.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_sees_all_persons(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(self.URL)
        ids = _ids(resp)
        self.assertIn(self.person_a.id, ids)
        self.assertIn(self.person_b.id, ids)

    def test_create_person_stamps_users_agency(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.post(
            self.URL,
            {
                "full_name": "Forced",
                "person_type": Person.PersonType.INDIVIDUAL,
                "agency": self.agency_b.id,  # malicious override
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        new_person = Person.objects.get(full_name="Forced")
        self.assertEqual(new_person.agency_id, self.agency_a.id)


class PendingInvitesIsolationTest(_TwoAgencyBase):
    URL = "/api/v1/auth/users/invites/"

    def test_user_a_lists_only_a_invites(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        emails = {row["email"] for row in resp.json()}
        self.assertIn(self.invite_a.email, emails)
        self.assertNotIn(self.invite_b.email, emails)

    def test_user_a_cannot_cancel_b_invite(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.delete(f"{self.URL}{self.invite_b.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.invite_b.refresh_from_db()
        self.assertIsNone(self.invite_b.cancelled_at)

    def test_admin_sees_all_invites(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(self.URL)
        emails = {row["email"] for row in resp.json()}
        self.assertIn(self.invite_a.email, emails)
        self.assertIn(self.invite_b.email, emails)


class AgencySettingsIsolationTest(_TwoAgencyBase):
    URL = "/api/v1/auth/agency/"

    def test_user_a_sees_own_agency(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["id"], self.agency_a.id)

    def test_user_b_sees_own_agency(self):
        self.client.force_authenticate(self.user_b)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["id"], self.agency_b.id)
