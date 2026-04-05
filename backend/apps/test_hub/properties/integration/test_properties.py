"""Tests for PropertyViewSet, PropertyGroupViewSet."""
import pytest
from django.urls import reverse
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


class PropertyViewSetTests(TremlyAPITestCase):

    def setUp(self):
        self.agent1 = self.create_agent(email="agent1@test.com")
        self.agent2 = self.create_agent(email="agent2@test.com")
        self.admin = self.create_admin()
        self.tenant = self.create_tenant()
        self.prop1 = self.create_property(agent=self.agent1, name="Agent1 Property")
        self.prop2 = self.create_property(agent=self.agent2, name="Agent2 Property")
        self.prop3 = self.create_property(agent=self.admin, name="Admin Property")

    def test_agent_sees_own_properties(self):
        self.authenticate(self.agent1)
        resp = self.client.get(reverse("property-list"))
        self.assertEqual(resp.status_code, 200)
        names = [p["name"] for p in resp.data["results"]]
        self.assertIn("Agent1 Property", names)
        self.assertNotIn("Agent2 Property", names)

    def test_admin_sees_own_assigned_properties(self):
        self.authenticate(self.admin)
        resp = self.client.get(reverse("property-list"))
        names = [p["name"] for p in resp.data["results"]]
        self.assertIn("Admin Property", names)
        self.assertNotIn("Agent1 Property", names)

    def test_idor_tenant_blocked_from_properties(self):
        """
        SECURITY AUDIT (vuln #1 — FIXED): Non-agent/admin users are now blocked
        by IsAgentOrAdmin permission. Tenant gets 403.
        """
        self.authenticate(self.tenant)
        resp = self.client.get(reverse("property-list"))
        self.assertEqual(resp.status_code, 403)

    def test_create_property_sets_agent(self):
        self.authenticate(self.agent1)
        resp = self.client.post(reverse("property-list"), {
            "name": "New Prop",
            "property_type": "house",
            "address": "456 New St",
            "city": "Johannesburg",
            "province": "Gauteng",
            "postal_code": "2000",
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["agent"], self.agent1.pk)

    def test_create_property_valid(self):
        self.authenticate(self.agent1)
        resp = self.client.post(reverse("property-list"), {
            "name": "Valid Prop",
            "property_type": "apartment",
            "address": "789 Main",
            "city": "Durban",
            "province": "KZN",
            "postal_code": "4001",
        })
        self.assertEqual(resp.status_code, 201)

    def test_update_property(self):
        self.authenticate(self.agent1)
        resp = self.client.patch(
            reverse("property-detail", args=[self.prop1.pk]),
            {"name": "Updated Name"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["name"], "Updated Name")

    def test_delete_property(self):
        self.authenticate(self.agent1)
        resp = self.client.delete(reverse("property-detail", args=[self.prop1.pk]))
        self.assertEqual(resp.status_code, 204)

    def test_unauthenticated(self):
        resp = self.client.get(reverse("property-list"))
        self.assertEqual(resp.status_code, 401)

    def test_property_includes_units(self):
        self.create_unit(property_obj=self.prop1, unit_number="101")
        self.authenticate(self.agent1)
        resp = self.client.get(reverse("property-detail", args=[self.prop1.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("units", resp.data)
        self.assertEqual(len(resp.data["units"]), 1)


class PropertyGroupViewSetTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.prop1 = self.create_property(agent=self.agent, name="Prop A")
        self.prop2 = self.create_property(agent=self.agent, name="Prop B")

    def test_create_group(self):
        self.authenticate(self.agent)
        resp = self.client.post(reverse("property-group-list"), {
            "name": "Test Group",
            "property_ids": [self.prop1.pk, self.prop2.pk],
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["property_count"], 2)

    def test_list_groups(self):
        self.authenticate(self.agent)
        from apps.properties.models import PropertyGroup
        g = PropertyGroup.objects.create(name="G1")
        g.properties.set([self.prop1])
        resp = self.client.get(reverse("property-group-list"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data["results"]), 1)

    def test_update_group_properties(self):
        self.authenticate(self.agent)
        from apps.properties.models import PropertyGroup
        g = PropertyGroup.objects.create(name="G2")
        g.properties.set([self.prop1])
        resp = self.client.patch(
            reverse("property-group-detail", args=[g.pk]),
            {"property_ids": [self.prop2.pk]},
        )
        self.assertEqual(resp.status_code, 200)

    def test_delete_group(self):
        self.authenticate(self.agent)
        from apps.properties.models import PropertyGroup
        g = PropertyGroup.objects.create(name="G3")
        resp = self.client.delete(reverse("property-group-detail", args=[g.pk]))
        self.assertEqual(resp.status_code, 204)
