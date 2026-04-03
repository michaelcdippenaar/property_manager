"""Tests for TenantsListView, PersonViewSet, PersonDetailView."""
from django.urls import reverse
from apps.accounts.models import Person
from apps.leases.models import LeaseTenant
from tests.base import TremlyAPITestCase


class TenantsListViewTests(TremlyAPITestCase):
    url = reverse("tenants-list")

    def setUp(self):
        self.agent = self.create_agent()
        self.tenant_user = self.create_tenant()
        prop = self.create_property(agent=self.agent)
        unit = self.create_unit(property_obj=prop)
        self.person_on_lease = self.create_person(full_name="Leased Person")
        self.person_not_on_lease = self.create_person(full_name="Not On Lease")
        self.lease = self.create_lease(unit=unit, primary_tenant=self.person_on_lease)

    def test_tenants_list_returns_persons_on_leases(self):
        self.authenticate(self.agent)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        names = [p["full_name"] for p in resp.data["results"]]
        self.assertIn("Leased Person", names)

    def test_tenants_list_excludes_non_lease_persons(self):
        self.authenticate(self.agent)
        resp = self.client.get(self.url)
        names = [p["full_name"] for p in resp.data["results"]]
        self.assertNotIn("Not On Lease", names)

    def test_tenants_list_unauthenticated(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 401)

    def test_tenant_blocked_from_tenants_list(self):
        """
        SECURITY FIX: Tenant role is now blocked by IsAgentOrAdmin permission.
        Previously any authenticated user could list all tenants (vuln #7).
        """
        self.authenticate(self.tenant_user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)


class PersonViewSetTests(TremlyAPITestCase):
    url = reverse("persons-list")

    def setUp(self):
        self.agent = self.create_agent()
        self.tenant = self.create_tenant()
        self.p1 = self.create_person(full_name="Alice Smith")
        self.p2 = self.create_person(full_name="Bob Jones")

    def test_list_persons(self):
        self.authenticate(self.agent)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data["results"]), 2)

    def test_list_persons_search(self):
        self.authenticate(self.agent)
        resp = self.client.get(self.url, {"q": "Alice"})
        self.assertEqual(resp.status_code, 200)
        names = [p["full_name"] for p in resp.data["results"]]
        self.assertIn("Alice Smith", names)
        self.assertNotIn("Bob Jones", names)

    def test_create_person(self):
        self.authenticate(self.agent)
        resp = self.client.post(self.url, {
            "full_name": "New Person",
            "phone": "0821111111",
            "email": "new@person.com",
        })
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(Person.objects.filter(full_name="New Person").exists())

    def test_create_person_company(self):
        self.authenticate(self.agent)
        resp = self.client.post(self.url, {
            "full_name": "Corp Inc",
            "person_type": "company",
            "company_reg": "2024/123456/07",
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["person_type"], "company")

    def test_tenant_blocked_from_persons(self):
        """
        SECURITY FIX: Tenant role is now blocked by IsAgentOrAdmin permission.
        Previously any authenticated user could list all persons (vuln #6).
        """
        self.authenticate(self.tenant)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)


class PersonDetailViewTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.person = self.create_person(full_name="Detail Person", phone="0820000000")

    def test_retrieve_person(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("persons-detail", args=[self.person.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["full_name"], "Detail Person")

    def test_update_person(self):
        self.authenticate(self.agent)
        resp = self.client.patch(reverse("persons-detail", args=[self.person.pk]), {"phone": "0829999999"})
        self.assertEqual(resp.status_code, 200)
        self.person.refresh_from_db()
        self.assertEqual(self.person.phone, "0829999999")

    def test_retrieve_nonexistent(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("persons-detail", args=[99999]))
        self.assertEqual(resp.status_code, 404)
