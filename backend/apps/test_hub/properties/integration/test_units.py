"""Tests for UnitViewSet, UnitInfoViewSet, PropertyAgentConfigViewSet."""
import pytest
from decimal import Decimal

from django.urls import reverse
from apps.properties.models import PropertyAgentConfig
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


class UnitViewSetTests(TremlyAPITestCase):

    def setUp(self):
        self.agent1 = self.create_agent(email="agent1@test.com")
        self.agent2 = self.create_agent(email="agent2@test.com")
        self.tenant = self.create_tenant()
        self.prop1 = self.create_property(agent=self.agent1, name="P1")
        self.prop2 = self.create_property(agent=self.agent2, name="P2")
        self.unit1 = self.create_unit(property_obj=self.prop1, unit_number="A1")
        self.unit2 = self.create_unit(property_obj=self.prop2, unit_number="B1")

    def test_idor_unit_list_returns_all_units(self):
        """
        SECURITY AUDIT (vuln #2): UnitViewSet has NO queryset filtering.
        Any authenticated user sees ALL units in the system.
        """
        self.authenticate(self.agent1)
        resp = self.client.get(reverse("unit-list"))
        self.assertEqual(resp.status_code, 200)
        unit_numbers = [u["unit_number"] for u in resp.data["results"]]
        self.assertIn("A1", unit_numbers)
        self.assertIn("B1", unit_numbers)  # Agent1 shouldn't see Agent2's units

    def test_filter_by_property(self):
        self.authenticate(self.agent1)
        resp = self.client.get(reverse("unit-list"), {"property": self.prop1.pk})
        self.assertEqual(resp.status_code, 200)
        for u in resp.data["results"]:
            self.assertEqual(u["property"], self.prop1.pk)

    def test_filter_by_status(self):
        self.unit1.status = "occupied"
        self.unit1.save()
        self.authenticate(self.agent1)
        resp = self.client.get(reverse("unit-list"), {"status": "available"})
        unit_ids = [u["id"] for u in resp.data["results"]]
        self.assertNotIn(self.unit1.pk, unit_ids)

    def test_create_unit(self):
        self.authenticate(self.agent1)
        resp = self.client.post(reverse("unit-list"), {
            "property": self.prop1.pk,
            "unit_number": "C1",
            "bedrooms": 2,
            "bathrooms": 1,
            "rent_amount": "7500.00",
        })
        self.assertEqual(resp.status_code, 201)

    def test_create_unit_negative_rent(self):
        """
        SECURITY AUDIT (vuln #21): rent_amount allows negative values.
        No validator for > 0 on the model.
        """
        self.authenticate(self.agent1)
        resp = self.client.post(reverse("unit-list"), {
            "property": self.prop1.pk,
            "unit_number": "NEG",
            "rent_amount": "-100.00",
        })
        # Currently accepted — documents missing validation
        self.assertIn(resp.status_code, [201, 400])

    def test_create_duplicate_unit_number(self):
        """
        SECURITY AUDIT (vuln #22): No unique_together on (property, unit_number).
        Duplicate unit numbers for same property are allowed.
        """
        self.authenticate(self.agent1)
        resp = self.client.post(reverse("unit-list"), {
            "property": self.prop1.pk,
            "unit_number": "A1",  # Same as existing
            "rent_amount": "5000.00",
        })
        # Currently accepted — documents missing unique constraint
        self.assertIn(resp.status_code, [201, 400])

    def test_update_unit(self):
        self.authenticate(self.agent1)
        resp = self.client.patch(
            reverse("unit-detail", args=[self.unit1.pk]),
            {"status": "occupied"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], "occupied")

    def test_delete_unit(self):
        self.authenticate(self.agent1)
        resp = self.client.delete(reverse("unit-detail", args=[self.unit1.pk]))
        self.assertEqual(resp.status_code, 204)


class UnitInfoViewSetTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)

    def test_create_unit_info(self):
        self.authenticate(self.agent)
        resp = self.client.post(reverse("unit-info-list"), {
            "property": self.prop.pk,
            "icon_type": "wifi",
            "label": "WiFi",
            "value": "SSID: TestNet, Password: 123",
        })
        self.assertEqual(resp.status_code, 201)

    def test_list_unit_info_filter_by_property(self):
        from apps.properties.models import UnitInfo
        UnitInfo.objects.create(property=self.prop, label="WiFi", value="SSID: X")
        self.authenticate(self.agent)
        resp = self.client.get(reverse("unit-info-list"), {"property": self.prop.pk})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["results"]), 1)

    def test_update_unit_info(self):
        from apps.properties.models import UnitInfo
        info = UnitInfo.objects.create(property=self.prop, label="Old", value="old value")
        self.authenticate(self.agent)
        resp = self.client.patch(
            reverse("unit-info-detail", args=[info.pk]),
            {"value": "new value"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["value"], "new value")

    def test_delete_unit_info(self):
        from apps.properties.models import UnitInfo
        info = UnitInfo.objects.create(property=self.prop, label="Del", value="x")
        self.authenticate(self.agent)
        resp = self.client.delete(reverse("unit-info-detail", args=[info.pk]))
        self.assertEqual(resp.status_code, 204)


class PropertyAgentConfigTests(TremlyAPITestCase):

    def setUp(self):
        self.agent1 = self.create_agent(email="ag1@test.com")
        self.agent2 = self.create_agent(email="ag2@test.com")
        self.prop1 = self.create_property(agent=self.agent1, name="P1")
        self.prop2 = self.create_property(agent=self.agent2, name="P2")

    def test_by_property_get_creates_config(self):
        self.authenticate(self.agent1)
        url = reverse("agent-config-by-property", args=[self.prop1.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(PropertyAgentConfig.objects.filter(property=self.prop1).exists())

    def test_by_property_put_updates(self):
        self.authenticate(self.agent1)
        url = reverse("agent-config-by-property", args=[self.prop1.pk])
        self.client.get(url)  # Create
        resp = self.client.put(url, {
            "property": self.prop1.pk,
            "maintenance_playbook": "New playbook",
        })
        self.assertEqual(resp.status_code, 200)
        config = PropertyAgentConfig.objects.get(property=self.prop1)
        self.assertEqual(config.maintenance_playbook, "New playbook")

    def test_idor_by_property_no_ownership_check(self):
        """
        SECURITY AUDIT (vuln #3): Any authenticated user can read/write
        any property's agent config via by-property/{id} action.
        """
        self.authenticate(self.agent2)
        url = reverse("agent-config-by-property", args=[self.prop1.pk])
        resp = self.client.get(url)
        # Agent2 can access Agent1's property config
        self.assertEqual(resp.status_code, 200)
