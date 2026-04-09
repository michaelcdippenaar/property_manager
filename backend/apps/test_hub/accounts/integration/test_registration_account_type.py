"""
Tests for the account-type aware registration flow.

Covers the Agency onboarding feature added for alpha/beta launch:
  - Registering as an Estate Agency → creates Agency(account_type=agency, name=<agency_name>)
  - Registering as an Individual Owner → creates Agency(account_type=individual, name=full name)
  - Agency account without agency_name is rejected
  - First registered user becomes ADMIN (not TENANT) so they can configure the agency
  - Subsequent registrations do NOT overwrite the singleton Agency

Source file under test: apps/accounts/serializers.py :: RegisterSerializer
"""
import pytest
from django.urls import reverse

from apps.accounts.models import Agency, User
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


class RegisterAsAgencyTests(TremlyAPITestCase):
    """POST /auth/register/ with account_type=agency creates an Agency record."""

    url = reverse("auth-register")

    def test_agency_registration_creates_agency_record(self):
        resp = self.client.post(self.url, {
            "email": "admin@pam-golding.co.za",
            "password": "strongpass123",
            "first_name": "Pam",
            "last_name": "Golding",
            "account_type": "agency",
            "agency_name": "Pam Golding Properties",
        })
        self.assertEqual(resp.status_code, 201)

        agency = Agency.get_solo()
        self.assertIsNotNone(agency)
        self.assertEqual(agency.account_type, Agency.AccountType.AGENCY)
        self.assertEqual(agency.name, "Pam Golding Properties")

    def test_agency_registration_without_agency_name_is_rejected(self):
        resp = self.client.post(self.url, {
            "email": "agent@test.com",
            "password": "strongpass123",
            "first_name": "Pam",
            "last_name": "Golding",
            "account_type": "agency",
            # intentionally omit agency_name
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn("agency_name", resp.data)

    def test_first_registered_user_is_admin(self):
        """So that they can log in and configure their agency."""
        resp = self.client.post(self.url, {
            "email": "first@test.com",
            "password": "strongpass123",
            "account_type": "agency",
            "agency_name": "Test Agency",
        })
        self.assertEqual(resp.status_code, 201)
        user = User.objects.get(email="first@test.com")
        self.assertEqual(user.role, User.Role.ADMIN)


class RegisterAsIndividualOwnerTests(TremlyAPITestCase):
    """POST /auth/register/ with account_type=individual → Agency(name = full name)."""

    url = reverse("auth-register")

    def test_individual_registration_creates_agency_with_full_name(self):
        resp = self.client.post(self.url, {
            "email": "solo@owner.com",
            "password": "strongpass123",
            "first_name": "John",
            "last_name": "Owner",
            "account_type": "individual",
        })
        self.assertEqual(resp.status_code, 201)

        agency = Agency.get_solo()
        self.assertIsNotNone(agency)
        self.assertEqual(agency.account_type, Agency.AccountType.INDIVIDUAL)
        self.assertEqual(agency.name, "John Owner")

    def test_individual_registration_agency_name_is_ignored(self):
        """For individuals we derive the name from first + last."""
        resp = self.client.post(self.url, {
            "email": "solo@owner.com",
            "password": "strongpass123",
            "first_name": "Jane",
            "last_name": "Owner",
            "account_type": "individual",
            "agency_name": "Should Be Ignored",
        })
        self.assertEqual(resp.status_code, 201)
        agency = Agency.get_solo()
        self.assertEqual(agency.name, "Jane Owner")

    def test_individual_without_name_falls_back_to_email(self):
        resp = self.client.post(self.url, {
            "email": "noname@owner.com",
            "password": "strongpass123",
            "account_type": "individual",
        })
        self.assertEqual(resp.status_code, 201)
        agency = Agency.get_solo()
        self.assertEqual(agency.name, "noname@owner.com")


class ReRegistrationAfterSoftDeleteTests(TremlyAPITestCase):
    """Regression tests for the soft-delete re-registration bug.

    Admin soft-deletes set is_active=False but keep the row. Re-registration with the
    same email must therefore be allowed — the old row is renamed to free the unique
    constraint while preserving audit/lease history.
    """

    url = reverse("auth-register")

    def test_re_registration_after_soft_delete_is_allowed(self):
        # Soft-delete a user (mirrors what UserDetailView.delete does)
        user = self.create_user(email="comeback@test.com", password="oldpass123")
        user.is_active = False
        user.save()

        # Now try to register with the same email
        resp = self.client.post(self.url, {
            "email": "comeback@test.com",
            "password": "newpass12345",
            "first_name": "Come",
            "last_name": "Back",
            "account_type": "agency",
            "agency_name": "Second Chance Realty",
        })
        self.assertEqual(resp.status_code, 201)

    def test_re_registration_preserves_old_row(self):
        """The soft-deleted row is renamed, not deleted — audit history stays."""
        old = self.create_user(email="preserve@test.com")
        old.is_active = False
        old.save()
        old_id = old.id

        self.client.post(self.url, {
            "email": "preserve@test.com",
            "password": "freshpass123",
            "account_type": "individual",
        })

        # Old row still exists but its email has been rewritten
        old.refresh_from_db()
        self.assertNotEqual(old.email, "preserve@test.com")
        self.assertTrue(old.email.endswith("_preserve@test.com"))
        self.assertFalse(old.is_active)
        # And the new row lives under the freed email
        new = User.objects.get(email="preserve@test.com")
        self.assertNotEqual(new.id, old_id)
        self.assertTrue(new.is_active)

    def test_active_email_still_rejected(self):
        """Defence-in-depth: an active duplicate must still be rejected."""
        self.create_user(email="taken@test.com", password="x" * 12)
        resp = self.client.post(self.url, {
            "email": "taken@test.com",
            "password": "anotherpass123",
            "account_type": "individual",
        })
        self.assertEqual(resp.status_code, 400)


class AgencySingletonDuringRegistrationTests(TremlyAPITestCase):
    """Subsequent registrations must be blocked once the Agency singleton exists.

    This is the regression guard for the bug where a freshly registered
    user silently joined the existing Agency as another admin and inherited
    full visibility of the original landlord's dashboard.
    """

    url = reverse("auth-register")

    def test_second_registration_is_blocked_with_403(self):
        # First registration creates the singleton
        first = self.client.post(self.url, {
            "email": "first@test.com",
            "password": "strongpass123",
            "first_name": "First",
            "last_name": "Admin",
            "account_type": "agency",
            "agency_name": "First Agency",
        })
        self.assertEqual(first.status_code, 201)
        self.assertEqual(Agency.objects.count(), 1)

        # Second registration — must be rejected, no silent admin grant
        second = self.client.post(self.url, {
            "email": "second@test.com",
            "password": "strongpass123",
            "first_name": "Second",
            "last_name": "Admin",
            "account_type": "agency",
            "agency_name": "Hostile Takeover Agency",
        })
        self.assertEqual(second.status_code, 403)
        # Singleton untouched
        self.assertEqual(Agency.objects.count(), 1)
        self.assertEqual(Agency.get_solo().name, "First Agency")
        # And no second user was created
        self.assertFalse(User.objects.filter(email="second@test.com").exists())

    def test_second_registration_blocked_even_as_individual(self):
        """Individual-owner registrations are blocked too — the Agency singleton
        already controls the deployment."""
        self.client.post(self.url, {
            "email": "landlord@test.com",
            "password": "strongpass123",
            "account_type": "individual",
        })
        resp = self.client.post(self.url, {
            "email": "newbie@test.com",
            "password": "strongpass123",
            "account_type": "individual",
        })
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(User.objects.filter(email="newbie@test.com").exists())
