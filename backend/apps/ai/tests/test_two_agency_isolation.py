"""
Phase 2.7 — two-agency isolation tests for the ai app viewsets.

The only viewset that received agency scoping in this app is
MaintenanceSkillDetailView (other ai viewsets are admin-only registry
endpoints or AI action endpoints with no DB read scope). This test
confirms cross-agency detail lookups return 404 while global
(agency=null) skills remain accessible to everyone.
"""
from __future__ import annotations

import pytest
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Agency, User
from apps.maintenance.models import MaintenanceSkill


@pytest.mark.django_db
class MaintenanceSkillDetailIsolationTest(TestCase):
    def setUp(self):
        self.agency_a = Agency.objects.create(name="Agency A (ai)")
        self.agency_b = Agency.objects.create(name="Agency B (ai)")

        self.staff_a = User.objects.create_user(
            email="ai_a@x.com", password="pass", role=User.Role.AGENCY_ADMIN,
        )
        self.staff_a.agency = self.agency_a
        self.staff_a.save(update_fields=["agency"])

        self.admin = User.objects.create_user(
            email="ai_admin@x.com", password="pass", role=User.Role.ADMIN,
        )

        self.skill_a = MaintenanceSkill.objects.create(
            agency=self.agency_a, name="A skill", trade="plumbing",
        )
        self.skill_b = MaintenanceSkill.objects.create(
            agency=self.agency_b, name="B skill", trade="plumbing",
        )
        self.skill_global = MaintenanceSkill.objects.create(
            agency=None, name="Global skill", trade="electrical",
        )

        self.client = APIClient(HTTP_ACCEPT="application/json")

    def _url(self, pk):
        return f"/api/v1/ai/skills/maintenance/{pk}/"

    def test_staff_a_can_fetch_a_skill(self):
        self.client.force_authenticate(self.staff_a)
        resp = self.client.get(self._url(self.skill_a.pk))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_staff_a_cannot_fetch_b_skill(self):
        self.client.force_authenticate(self.staff_a)
        resp = self.client.get(self._url(self.skill_b.pk))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_staff_a_can_fetch_global_skill(self):
        self.client.force_authenticate(self.staff_a)
        resp = self.client.get(self._url(self.skill_global.pk))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_admin_can_fetch_any_skill(self):
        self.client.force_authenticate(self.admin)
        for pk in (self.skill_a.pk, self.skill_b.pk, self.skill_global.pk):
            resp = self.client.get(self._url(pk))
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
