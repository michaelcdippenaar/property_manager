"""
Phase 3.2 — agency onboarding completion endpoint tests.

POST /api/v1/auth/agency/onboarding/complete/
- AGENCY_ADMIN can call → stamps `onboarding_completed_at`
- ADMIN can call (IsAdminOrAgencyAdmin allows it)
- Non-admin role (agent) is forbidden
- Idempotent — second call does NOT change the timestamp
- Unauthenticated → 401
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Agency, User


class AgencyOnboardingCompleteTests(APITestCase):
    def setUp(self):
        self.agency = Agency.objects.create(
            name="Test Estates",
            account_type=Agency.AccountType.AGENCY,
        )
        # Sanity: a freshly-created agency is not onboarded yet.
        self.assertIsNone(self.agency.onboarding_completed_at)

        self.admin_user = User.objects.create_user(
            email="agencyadmin@test.co.za",
            password="S3cure!Passw0rd",
            first_name="Admin",
            last_name="Tester",
            role=User.Role.AGENCY_ADMIN,
            agency=self.agency,
        )
        self.agent_user = User.objects.create_user(
            email="agent@test.co.za",
            password="S3cure!Passw0rd",
            first_name="Agent",
            last_name="Tester",
            role=User.Role.AGENT,
            agency=self.agency,
        )
        self.url = reverse("agency-onboarding-complete")

    def test_agency_admin_can_complete_onboarding(self):
        self.client.force_authenticate(user=self.admin_user)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.agency.refresh_from_db()
        self.assertIsNotNone(self.agency.onboarding_completed_at)
        # Response includes the field.
        self.assertIsNotNone(resp.data.get("onboarding_completed_at"))

    def test_agent_role_forbidden(self):
        self.client.force_authenticate(user=self.agent_user)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.agency.refresh_from_db()
        self.assertIsNone(self.agency.onboarding_completed_at)

    def test_unauthenticated_rejected(self):
        resp = self.client.post(self.url)
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_idempotent_does_not_overwrite_timestamp(self):
        self.client.force_authenticate(user=self.admin_user)
        resp1 = self.client.post(self.url)
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)
        self.agency.refresh_from_db()
        first_ts = self.agency.onboarding_completed_at
        self.assertIsNotNone(first_ts)

        # Second call must not move the timestamp.
        resp2 = self.client.post(self.url)
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.agency.refresh_from_db()
        self.assertEqual(self.agency.onboarding_completed_at, first_ts)
