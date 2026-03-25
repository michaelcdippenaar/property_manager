"""Tests for OwnerDashboardView, OwnerPropertiesView."""
from django.urls import reverse
from tests.base import TremlyAPITestCase


class OwnerDashboardTests(TremlyAPITestCase):

    def setUp(self):
        self.owner = self.create_owner_user()
        self.person = self.create_person(full_name="Owner Person", linked_user=self.owner)
        self.prop = self.create_property(name="Owner Prop", owner=self.person)
        self.unit = self.create_unit(property_obj=self.prop, status="occupied")
        self.mr = self.create_maintenance_request(unit=self.unit)

    def test_dashboard_with_properties(self):
        self.authenticate(self.owner)
        resp = self.client.get(reverse("owner-dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total_properties"], 1)
        self.assertEqual(resp.data["total_units"], 1)
        self.assertEqual(resp.data["occupied_units"], 1)
        self.assertEqual(resp.data["active_issues"], 1)

    def test_dashboard_no_person_profile(self):
        user = self.create_user(email="noprofile@test.com")
        self.authenticate(user)
        resp = self.client.get(reverse("owner-dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total_properties"], 0)

    def test_dashboard_unauthenticated(self):
        resp = self.client.get(reverse("owner-dashboard"))
        self.assertEqual(resp.status_code, 401)


class OwnerPropertiesTests(TremlyAPITestCase):

    def setUp(self):
        self.owner = self.create_owner_user()
        self.person = self.create_person(full_name="Owner Person", linked_user=self.owner)
        self.prop = self.create_property(name="Owner Prop", owner=self.person)
        self.create_unit(property_obj=self.prop)

    def test_list_owned_properties(self):
        self.authenticate(self.owner)
        resp = self.client.get(reverse("owner-properties"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["name"], "Owner Prop")
        self.assertEqual(resp.data[0]["unit_count"], 1)

    def test_no_person_profile(self):
        user = self.create_user(email="noprofile@test.com")
        self.authenticate(user)
        resp = self.client.get(reverse("owner-properties"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, [])

    def test_only_owned_properties(self):
        other_prop = self.create_property(name="Not Owned")
        self.authenticate(self.owner)
        resp = self.client.get(reverse("owner-properties"))
        names = [p["name"] for p in resp.data]
        self.assertNotIn("Not Owned", names)
