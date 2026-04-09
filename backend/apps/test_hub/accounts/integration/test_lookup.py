"""
Tests for the cross-entity lookup endpoint.

Source file under test: apps/accounts/lookup_views.py :: EntityLookupView

GET /api/v1/auth/lookup/?id_number=<id>
GET /api/v1/auth/lookup/?registration_number=<reg>

Returns all system records (User, Person, Landlord) matching the given
identifier. Used by the document classifier skill to detect when a person
or company in an uploaded document is already known to the system.
"""
import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.properties.models import Landlord
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


class EntityLookupPermissionTests(TremlyAPITestCase):
    """Only authenticated agents/admins may call the lookup endpoint."""

    url = reverse("entity-lookup")

    def test_unauthenticated_rejected(self):
        resp = self.client.get(self.url, {"id_number": "8001015800083"})
        self.assertEqual(resp.status_code, 401)

    def test_tenant_forbidden(self):
        self.authenticate(self.create_tenant())
        resp = self.client.get(self.url, {"id_number": "8001015800083"})
        self.assertEqual(resp.status_code, 403)

    def test_supplier_forbidden(self):
        self.authenticate(self.create_supplier_user())
        resp = self.client.get(self.url, {"id_number": "8001015800083"})
        self.assertEqual(resp.status_code, 403)

    def test_agent_allowed(self):
        self.authenticate(self.create_agent())
        resp = self.client.get(self.url, {"id_number": "8001015800083"})
        self.assertEqual(resp.status_code, 200)

    def test_admin_allowed(self):
        self.authenticate(self.create_admin())
        resp = self.client.get(self.url, {"id_number": "8001015800083"})
        self.assertEqual(resp.status_code, 200)


class EntityLookupQueryValidationTests(TremlyAPITestCase):
    """Endpoint must require at least one identifier parameter."""

    url = reverse("entity-lookup")

    def setUp(self):
        self.authenticate(self.create_admin())

    def test_missing_both_params_returns_400(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("id_number", resp.data["detail"])

    def test_empty_string_params_returns_400(self):
        resp = self.client.get(self.url, {"id_number": "", "registration_number": ""})
        self.assertEqual(resp.status_code, 400)

    def test_whitespace_only_params_returns_400(self):
        """Whitespace is stripped, so it must still look empty."""
        resp = self.client.get(self.url, {"id_number": "   "})
        self.assertEqual(resp.status_code, 400)

    def test_query_echoed_in_response(self):
        resp = self.client.get(self.url, {"id_number": "8001015800083"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["query"]["id_number"], "8001015800083")
        self.assertIsNone(resp.data["query"]["registration_number"])

    def test_whitespace_trimmed_before_query(self):
        self.create_user(email="leading@test.com", id_number="8001015800083")
        resp = self.client.get(self.url, {"id_number": "  8001015800083  "})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["query"]["id_number"], "8001015800083")
        self.assertGreaterEqual(resp.data["total_matches"], 1)


class EntityLookupUserMatchTests(TremlyAPITestCase):
    """ID-number matches against User records return the user entry."""

    url = reverse("entity-lookup")

    def setUp(self):
        self.authenticate(self.create_admin(email="root@test.com"))

    def test_no_matches_returns_empty_list(self):
        resp = self.client.get(self.url, {"id_number": "9999999999999"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["matches"], [])
        self.assertEqual(resp.data["total_matches"], 0)

    def test_user_match_by_id_number(self):
        self.create_user(
            email="jane@test.com",
            first_name="Jane",
            last_name="Doe",
            phone="0821234567",
            id_number="8001015800083",
        )
        resp = self.client.get(self.url, {"id_number": "8001015800083"})
        self.assertEqual(resp.status_code, 200)

        users = [m for m in resp.data["matches"] if m["source"] == "User"]
        self.assertEqual(len(users), 1)
        entry = users[0]
        self.assertEqual(entry["full_name"], "Jane Doe")
        self.assertEqual(entry["email"], "jane@test.com")
        self.assertEqual(entry["phone"], "0821234567")
        self.assertTrue(entry["is_active"])
        self.assertEqual(entry["related"], [])

    def test_inactive_user_still_returned(self):
        """Soft-deleted users are still surfaced so the skill can warn."""
        user = self.create_user(email="gone@test.com", id_number="8001015800083")
        user.is_active = False
        user.save()
        resp = self.client.get(self.url, {"id_number": "8001015800083"})
        users = [m for m in resp.data["matches"] if m["source"] == "User"]
        self.assertEqual(len(users), 1)
        self.assertFalse(users[0]["is_active"])

    def test_multiple_users_same_id_number(self):
        """Pathological case — same ID on multiple user rows (e.g. soft-deleted + active)."""
        old = self.create_user(email="old@test.com", id_number="8001015800083")
        old.is_active = False
        old.save()
        self.create_user(email="new@test.com", id_number="8001015800083")
        resp = self.client.get(self.url, {"id_number": "8001015800083"})
        users = [m for m in resp.data["matches"] if m["source"] == "User"]
        self.assertEqual(len(users), 2)

    def test_registration_number_does_not_match_user(self):
        """Users don't have a registration_number field — reg queries skip User table."""
        self.create_user(email="jane@test.com", id_number="8001015800083")
        resp = self.client.get(self.url, {"registration_number": "2020/123456/07"})
        users = [m for m in resp.data["matches"] if m["source"] == "User"]
        self.assertEqual(users, [])


class EntityLookupLandlordMatchTests(TremlyAPITestCase):
    """Landlord matches by both id_number and registration_number."""

    url = reverse("entity-lookup")

    def setUp(self):
        self.authenticate(self.create_admin(email="root@test.com"))

    def test_landlord_match_by_registration_number(self):
        landlord = self.create_landlord(
            name="Acme Properties (Pty) Ltd",
            landlord_type="company",
            registration_number="2020/123456/07",
        )
        resp = self.client.get(self.url, {"registration_number": "2020/123456/07"})
        self.assertEqual(resp.status_code, 200)

        landlords = [m for m in resp.data["matches"] if m["source"] == "Landlord"]
        self.assertEqual(len(landlords), 1)
        entry = landlords[0]
        self.assertEqual(entry["id"], landlord.id)
        self.assertEqual(entry["full_name"], "Acme Properties (Pty) Ltd")
        self.assertEqual(entry["landlord_type"], "company")
        self.assertEqual(entry["registration_number"], "2020/123456/07")

    def test_landlord_match_by_id_number(self):
        landlord = self.create_landlord(
            name="John Doe",
            landlord_type="individual",
            id_number="8001015800083",
            registration_number="",
        )
        resp = self.client.get(self.url, {"id_number": "8001015800083"})
        landlords = [m for m in resp.data["matches"] if m["source"] == "Landlord"]
        self.assertEqual(len(landlords), 1)
        self.assertEqual(landlords[0]["id"], landlord.id)

    def test_landlord_includes_related_properties(self):
        landlord = self.create_landlord(
            name="Acme Properties (Pty) Ltd",
            registration_number="2020/123456/07",
        )
        prop = self.create_property(name="Sunset Views")
        self.create_property_ownership(property_obj=prop, landlord=landlord)

        resp = self.client.get(self.url, {"registration_number": "2020/123456/07"})
        landlords = [m for m in resp.data["matches"] if m["source"] == "Landlord"]
        self.assertEqual(len(landlords), 1)
        related = landlords[0]["related"]
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0]["type"], "Property (landlord)")
        self.assertEqual(related[0]["property_id"], prop.id)

    def test_landlord_no_match_by_wrong_registration(self):
        self.create_landlord(registration_number="2020/123456/07")
        resp = self.client.get(self.url, {"registration_number": "9999/999999/07"})
        landlords = [m for m in resp.data["matches"] if m["source"] == "Landlord"]
        self.assertEqual(landlords, [])

    def test_combined_id_and_registration_query(self):
        """Passing both parameters should OR the results across Landlords."""
        a = self.create_landlord(
            name="Individual John",
            landlord_type="individual",
            id_number="8001015800083",
            registration_number="",
        )
        b = self.create_landlord(
            name="Acme Co",
            landlord_type="company",
            id_number="",
            registration_number="2020/123456/07",
        )
        resp = self.client.get(
            self.url,
            {"id_number": "8001015800083", "registration_number": "2020/123456/07"},
        )
        self.assertEqual(resp.status_code, 200)
        landlord_ids = [
            m["id"] for m in resp.data["matches"] if m["source"] == "Landlord"
        ]
        self.assertIn(a.id, landlord_ids)
        self.assertIn(b.id, landlord_ids)


class EntityLookupPersonMatchTests(TremlyAPITestCase):
    """Person records (lease parties) matched by id_number."""

    url = reverse("entity-lookup")

    def setUp(self):
        self.authenticate(self.create_admin(email="root@test.com"))

    def test_person_match_without_leases(self):
        person = self.create_person(
            full_name="Solo Person",
            id_number="8001015800083",
            phone="0821234567",
            email="solo@test.com",
        )
        resp = self.client.get(self.url, {"id_number": "8001015800083"})
        self.assertEqual(resp.status_code, 200)
        persons = [m for m in resp.data["matches"] if m["source"] == "Person"]
        self.assertEqual(len(persons), 1)
        entry = persons[0]
        self.assertEqual(entry["id"], person.id)
        self.assertEqual(entry["full_name"], "Solo Person")
        self.assertEqual(entry["email"], "solo@test.com")
        self.assertEqual(entry["related"], [])

    def test_person_match_with_primary_lease(self):
        person = self.create_person(full_name="Primary Tenant", id_number="8001015800083")
        unit = self.create_unit()
        lease = self.create_lease(unit=unit, primary_tenant=person)

        resp = self.client.get(self.url, {"id_number": "8001015800083"})
        self.assertEqual(resp.status_code, 200)
        persons = [m for m in resp.data["matches"] if m["source"] == "Person"]
        self.assertEqual(len(persons), 1)
        related = persons[0]["related"]
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0]["type"], "Lease (primary tenant)")
        self.assertEqual(related[0]["lease_id"], lease.id)


class EntityLookupCombinedMatchTests(TremlyAPITestCase):
    """A single id_number can match across User and Landlord tables."""

    url = reverse("entity-lookup")

    def setUp(self):
        self.authenticate(self.create_admin(email="root@test.com"))

    def test_user_and_landlord_same_id_number(self):
        """The document classifier's core use case — same ID in two capacities."""
        self.create_user(
            email="dual@test.com",
            first_name="Dual",
            last_name="Capacity",
            id_number="8001015800083",
        )
        self.create_landlord(
            name="Dual Capacity",
            landlord_type="individual",
            id_number="8001015800083",
            registration_number="",
        )
        resp = self.client.get(self.url, {"id_number": "8001015800083"})
        self.assertEqual(resp.status_code, 200)

        sources = sorted(m["source"] for m in resp.data["matches"])
        self.assertIn("User", sources)
        self.assertIn("Landlord", sources)
        self.assertEqual(resp.data["total_matches"], len(resp.data["matches"]))

    def test_total_matches_matches_list_length(self):
        """total_matches must reflect len(matches) even when zero."""
        resp = self.client.get(self.url, {"id_number": "0000000000000"})
        self.assertEqual(resp.data["total_matches"], len(resp.data["matches"]))

    def test_response_shape_contract(self):
        """Document the response shape for the document classifier skill."""
        resp = self.client.get(self.url, {"id_number": "8001015800083"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("query", resp.data)
        self.assertIn("matches", resp.data)
        self.assertIn("total_matches", resp.data)
        self.assertIsInstance(resp.data["matches"], list)
