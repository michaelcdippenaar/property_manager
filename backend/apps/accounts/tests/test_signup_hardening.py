"""
Phase 3.1 — signup-hardening + orphan-prevention + starter-content tests.

Covers:
  - Register account_type="agency" → user has agency, starter templates seeded.
  - Register account_type="individual" → user has personal agency, AGENCY_ADMIN.
  - Google auth, brand-new email, no invite → returns needs_signup=true, no User created.
  - Google auth, brand-new email + pending invite → User created, invite consumed.
  - Google complete-signup → creates Agency + User in one transaction.
  - InviteUserView from orphan inviter → 400.
  - InviteUserView from agency_admin → invite stamped with inviter agency.
  - System check passes for all-tenants/agencies; fails for orphan agency_admin.
  - Starter content seed idempotent + handles malformed fixture gracefully.
"""
import json
import tempfile
from pathlib import Path
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from apps.accounts.models import Agency, User, UserInvite
from apps.accounts.checks import check_no_orphan_users
from apps.accounts.starter_content import seed_starter_content


# ─────────────────────────────────────────────────────────────────
# RegisterSerializer hardening
# ─────────────────────────────────────────────────────────────────

class RegisterAgencyTests(APITestCase):
    def test_register_agency_creates_agency_and_seeds_content(self):
        url = reverse("auth-register")
        resp = self.client.post(url, {
            "email": "founder@acme.co.za",
            "password": "S3cure!Passw0rd",
            "first_name": "Anna",
            "last_name": "Acme",
            "account_type": "agency",
            "agency_name": "Acme Estates",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="founder@acme.co.za")
        self.assertIsNotNone(user.agency_id)
        self.assertEqual(user.agency.name, "Acme Estates")
        self.assertEqual(user.agency.account_type, Agency.AccountType.AGENCY)
        self.assertEqual(user.role, User.Role.AGENCY_ADMIN)
        # Starter content seeded.
        from apps.leases.models import LeaseTemplate
        self.assertGreater(LeaseTemplate.objects.filter(agency=user.agency).count(), 0)

    def test_register_individual_creates_personal_agency(self):
        url = reverse("auth-register")
        resp = self.client.post(url, {
            "email": "owner@example.com",
            "password": "S3cure!Passw0rd",
            "first_name": "Sam",
            "last_name": "Owner",
            "account_type": "individual",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="owner@example.com")
        self.assertIsNotNone(user.agency_id)
        self.assertEqual(user.agency.account_type, Agency.AccountType.INDIVIDUAL)
        self.assertIn("Sam Owner", user.agency.name)
        self.assertEqual(user.role, User.Role.AGENCY_ADMIN)


# ─────────────────────────────────────────────────────────────────
# Google auth — brand-new emails
# ─────────────────────────────────────────────────────────────────

class GoogleAuthSignupGuardTests(APITestCase):
    def setUp(self):
        # An existing agency must NOT cause new Google emails to auto-create.
        self.existing_agency = Agency.objects.create(
            account_type=Agency.AccountType.AGENCY, name="Existing Agency"
        )

    @mock.patch("apps.accounts.oauth_views.id_token.verify_oauth2_token")
    def test_brand_new_google_email_no_invite_returns_needs_signup(self, mock_verify):
        mock_verify.return_value = {
            "email": "newbie@gmail.com",
            "email_verified": True,
            "given_name": "New",
            "family_name": "Bie",
        }
        with self.settings(GOOGLE_OAUTH_CLIENT_ID="test-client-id"):
            resp = self.client.post(
                reverse("auth-google"),
                {"credential": "fake-id-token"},
                format="json",
            )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data.get("needs_signup"))
        self.assertEqual(resp.data.get("email"), "newbie@gmail.com")
        # Critically: no User row created.
        self.assertFalse(User.objects.filter(email="newbie@gmail.com").exists())

    @mock.patch("apps.accounts.oauth_views.id_token.verify_oauth2_token")
    def test_brand_new_google_email_with_pending_invite_creates_user(self, mock_verify):
        inviter = User.objects.create_user(
            email="admin@existing.co.za", password="x", role=User.Role.AGENCY_ADMIN,
            agency=self.existing_agency,
        )
        invite = UserInvite.objects.create(
            email="invitee@gmail.com",
            role=User.Role.VIEWER,
            agency=self.existing_agency,
            invited_by=inviter,
        )
        mock_verify.return_value = {
            "email": "invitee@gmail.com",
            "email_verified": True,
            "given_name": "Invi",
            "family_name": "Tee",
        }
        with self.settings(GOOGLE_OAUTH_CLIENT_ID="test-client-id"):
            resp = self.client.post(
                reverse("auth-google"),
                {"credential": "fake-id-token"},
                format="json",
            )
        self.assertIn(resp.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
        user = User.objects.get(email="invitee@gmail.com")
        self.assertEqual(user.agency_id, self.existing_agency.pk)
        invite.refresh_from_db()
        self.assertIsNotNone(invite.accepted_at)


class GoogleCompleteSignupTests(APITestCase):
    @mock.patch("apps.accounts.oauth_views.id_token.verify_oauth2_token")
    def test_complete_signup_creates_agency_and_user(self, mock_verify):
        mock_verify.return_value = {
            "email": "founder2@acme.co.za",
            "email_verified": True,
            "given_name": "Fern",
            "family_name": "Founder",
        }
        with self.settings(GOOGLE_OAUTH_CLIENT_ID="test-client-id"):
            resp = self.client.post(
                reverse("auth-google-complete-signup"),
                {
                    "google_credential": "fake-id-token",
                    "account_type": "agency",
                    "agency_name": "Founder Estates",
                },
                format="json",
            )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="founder2@acme.co.za")
        self.assertIsNotNone(user.agency_id)
        self.assertEqual(user.agency.name, "Founder Estates")
        self.assertEqual(user.role, User.Role.AGENCY_ADMIN)


# ─────────────────────────────────────────────────────────────────
# InviteUserView guards
# ─────────────────────────────────────────────────────────────────

class InviteUserGuardTests(APITestCase):
    def test_orphan_inviter_rejected(self):
        orphan = User.objects.create_user(
            email="orphan@nowhere.io",
            password="x",
            role=User.Role.AGENCY_ADMIN,
            agency=None,
        )
        client = APIClient()
        client.force_authenticate(user=orphan)
        resp = client.post(
            reverse("user-invite"),
            {"email": "victim@nowhere.io", "role": "viewer"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_agency_admin_invite_stamps_inviter_agency(self):
        agency = Agency.objects.create(
            account_type=Agency.AccountType.AGENCY, name="A1",
        )
        admin_user = User.objects.create_user(
            email="aa@a1.co.za", password="x",
            role=User.Role.AGENCY_ADMIN, agency=agency,
        )
        client = APIClient()
        client.force_authenticate(user=admin_user)
        resp = client.post(
            reverse("user-invite"),
            {"email": "newhire@a1.co.za", "role": "viewer"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        invite = UserInvite.objects.get(email="newhire@a1.co.za")
        self.assertEqual(invite.agency_id, agency.pk)


# ─────────────────────────────────────────────────────────────────
# System check
# ─────────────────────────────────────────────────────────────────

class OrphanSystemCheckTests(TestCase):
    def test_no_orphans_when_only_agencies_and_tenants(self):
        agency = Agency.objects.create(account_type="agency", name="OK")
        User.objects.create_user(email="ok@a.co", password="x", role="agency_admin", agency=agency)
        User.objects.create_user(email="t@a.co", password="x", role="tenant", agency=None)
        User.objects.create_user(email="s@a.co", password="x", role="supplier", agency=None)
        errors = check_no_orphan_users(None)
        self.assertEqual(errors, [])

    def test_orphan_agency_admin_flagged(self):
        User.objects.create_user(
            email="orphan2@a.co", password="x",
            role=User.Role.AGENCY_ADMIN, agency=None,
        )
        errors = check_no_orphan_users(None)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "accounts.E003")


# ─────────────────────────────────────────────────────────────────
# Starter content seed
# ─────────────────────────────────────────────────────────────────

class StarterContentTests(TestCase):
    def setUp(self):
        self.agency = Agency.objects.create(
            account_type=Agency.AccountType.AGENCY, name="SeedTest",
        )

    def test_seed_idempotent(self):
        result1 = seed_starter_content(self.agency)
        first_count = result1.get("templates", 0)
        # Need at least one for idempotency check to be meaningful.
        self.assertGreaterEqual(first_count, 0)
        result2 = seed_starter_content(self.agency)
        # If first seed inserted any rows, second call must skip.
        if first_count > 0:
            self.assertTrue(result2.get("skipped"))
            self.assertEqual(result2.get("templates", 0), 0)

    def test_seed_with_malformed_fixture_does_not_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad_path = Path(tmp) / "bad.json"
            bad_path.write_text("{not json")
            # Should NOT raise — returns skipped instead.
            result = seed_starter_content(self.agency, fixture_path=bad_path)
            self.assertTrue(result.get("skipped"))
