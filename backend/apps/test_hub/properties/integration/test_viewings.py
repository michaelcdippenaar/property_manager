"""Integration tests for PropertyViewing endpoints."""
import pytest
from datetime import datetime, timedelta, timezone
from django.urls import reverse
from apps.test_hub.base.test_case import TremlyAPITestCase
from apps.properties.models import PropertyViewing

pytestmark = [pytest.mark.integration, pytest.mark.green]


def _dt(days_from_now=1):
    """Return an ISO datetime string N days from now."""
    dt = datetime.now(tz=timezone.utc) + timedelta(days=days_from_now)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class PropertyViewingCRUDTests(TremlyAPITestCase):

    def setUp(self):
        self.agent1 = self.create_agent(email="agent1@test.com")
        self.agent2 = self.create_agent(email="agent2@test.com")
        self.tenant = self.create_tenant()
        self.prop1  = self.create_property(agent=self.agent1, name="Prop1")
        self.prop2  = self.create_property(agent=self.agent2, name="Prop2")
        self.unit1  = self.create_unit(property_obj=self.prop1, unit_number="1A")
        self.prospect = self.create_person(full_name="Jane Prospect", email="jane@example.com")

    def _viewing_payload(self, **overrides):
        payload = {
            "property":    self.prop1.pk,
            "unit":        self.unit1.pk,
            "prospect":    self.prospect.pk,
            "scheduled_at": _dt(2),
            "notes":        "Interested in long-term lease",
        }
        payload.update(overrides)
        return payload

    def test_create_viewing_as_agent(self):
        self.authenticate(self.agent1)
        resp = self.client.post(reverse("property-viewing-list"), self._viewing_payload(), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["status"], "scheduled")
        self.assertEqual(resp.data["agent"], self.agent1.pk)

    def test_create_viewing_auto_assigns_agent(self):
        """If agent field is omitted, the requesting user is auto-assigned."""
        self.authenticate(self.agent1)
        payload = self._viewing_payload()
        del payload  # rebuild without agent
        payload = {
            "property":    self.prop1.pk,
            "unit":        self.unit1.pk,
            "prospect":    self.prospect.pk,
            "scheduled_at": _dt(3),
        }
        resp = self.client.post(reverse("property-viewing-list"), payload, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["agent"], self.agent1.pk)

    def test_agent_cannot_create_viewing_for_other_agents_property(self):
        """agent2 cannot create a viewing for prop1 (owned by agent1)."""
        self.authenticate(self.agent2)
        payload = self._viewing_payload()  # points to prop1
        resp = self.client.post(reverse("property-viewing-list"), payload, format="json")
        self.assertEqual(resp.status_code, 403, resp.data)

    def test_tenant_blocked(self):
        self.authenticate(self.tenant)
        resp = self.client.get(reverse("property-viewing-list"))
        self.assertEqual(resp.status_code, 403)

    def test_agent_sees_only_own_viewings(self):
        self.authenticate(self.agent1)
        self.client.post(reverse("property-viewing-list"), self._viewing_payload(), format="json")
        # agent2 creates a viewing on their own property
        self.authenticate(self.agent2)
        payload2 = {
            "property":    self.prop2.pk,
            "prospect":    self.prospect.pk,
            "scheduled_at": _dt(5),
        }
        self.client.post(reverse("property-viewing-list"), payload2, format="json")

        # agent1 should only see prop1's viewing
        self.authenticate(self.agent1)
        resp = self.client.get(reverse("property-viewing-list"))
        self.assertEqual(resp.status_code, 200)
        for v in resp.data["results"]:
            self.assertEqual(v["property"], self.prop1.pk)

    def test_update_status_to_completed(self):
        self.authenticate(self.agent1)
        create = self.client.post(reverse("property-viewing-list"), self._viewing_payload(), format="json")
        pk = create.data["id"]
        resp = self.client.patch(
            reverse("property-viewing-detail", args=[pk]),
            {"status": "completed"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], "completed")

    def test_delete_viewing(self):
        self.authenticate(self.agent1)
        create = self.client.post(reverse("property-viewing-list"), self._viewing_payload(), format="json")
        pk = create.data["id"]
        resp = self.client.delete(reverse("property-viewing-detail", args=[pk]))
        self.assertEqual(resp.status_code, 204)


class PropertyViewingCalendarTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.prop  = self.create_property(agent=self.agent)
        self.unit  = self.create_unit(property_obj=self.prop)
        self.prospect = self.create_person(full_name="Cal Prospect")
        self.authenticate(self.agent)

    def _create_viewing(self, days_offset):
        payload = {
            "property":    self.prop.pk,
            "unit":        self.unit.pk,
            "prospect":    self.prospect.pk,
            "scheduled_at": _dt(days_offset),
        }
        resp = self.client.post(reverse("property-viewing-list"), payload, format="json")
        self.assertEqual(resp.status_code, 201)

    def test_calendar_returns_viewings_in_range(self):
        self._create_viewing(2)
        self._create_viewing(5)
        self._create_viewing(15)  # outside 10-day window

        from datetime import date, timedelta
        from_date = (date.today() + timedelta(days=1)).isoformat()
        to_date   = (date.today() + timedelta(days=10)).isoformat()

        resp = self.client.get(
            reverse("property-viewing-calendar"),
            {"from": from_date, "to": to_date},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)

    def test_calendar_requires_from_and_to(self):
        resp = self.client.get(reverse("property-viewing-calendar"))
        self.assertEqual(resp.status_code, 400)

    def test_calendar_rejects_bad_date_format(self):
        resp = self.client.get(
            reverse("property-viewing-calendar"),
            {"from": "01/01/2026", "to": "31/01/2026"},
        )
        self.assertEqual(resp.status_code, 400)


class PropertyViewingConversionTests(TremlyAPITestCase):

    def setUp(self):
        self.agent    = self.create_agent()
        self.prop     = self.create_property(agent=self.agent)
        self.unit     = self.create_unit(property_obj=self.prop)
        self.prospect = self.create_person(full_name="Convert Me")
        self.authenticate(self.agent)

        payload = {
            "property":    self.prop.pk,
            "unit":        self.unit.pk,
            "prospect":    self.prospect.pk,
            "scheduled_at": _dt(1),
        }
        resp = self.client.post(reverse("property-viewing-list"), payload, format="json")
        self.viewing_pk = resp.data["id"]

    def _convert_payload(self, **overrides):
        data = {
            "start_date":    "2026-05-01",
            "end_date":      "2027-04-30",
            "monthly_rent":  "9500.00",
            "deposit":       "9500.00",
        }
        data.update(overrides)
        return data

    def test_convert_viewing_to_lease(self):
        resp = self.client.post(
            reverse("property-viewing-convert-to-lease", args=[self.viewing_pk]),
            self._convert_payload(),
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        # Viewing status updated
        viewing = PropertyViewing.objects.get(pk=self.viewing_pk)
        self.assertEqual(viewing.status, PropertyViewing.Status.CONVERTED)
        self.assertIsNotNone(viewing.converted_to_lease)
        # Lease has correct data
        self.assertEqual(str(viewing.converted_to_lease.monthly_rent), "9500.00")
        self.assertEqual(viewing.converted_to_lease.primary_tenant, self.prospect)

    def test_convert_cancelled_viewing_fails(self):
        self.client.patch(
            reverse("property-viewing-detail", args=[self.viewing_pk]),
            {"status": "cancelled"},
            format="json",
        )
        resp = self.client.post(
            reverse("property-viewing-convert-to-lease", args=[self.viewing_pk]),
            self._convert_payload(),
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_convert_already_converted_viewing_fails(self):
        # First conversion succeeds
        self.client.post(
            reverse("property-viewing-convert-to-lease", args=[self.viewing_pk]),
            self._convert_payload(),
            format="json",
        )
        # Second should fail
        resp = self.client.post(
            reverse("property-viewing-convert-to-lease", args=[self.viewing_pk]),
            self._convert_payload(),
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_convert_missing_fields_returns_400(self):
        resp = self.client.post(
            reverse("property-viewing-convert-to-lease", args=[self.viewing_pk]),
            {"start_date": "2026-05-01"},  # missing end_date, monthly_rent, deposit
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_convert_viewing_without_unit_fails(self):
        """A viewing with no unit cannot be converted."""
        payload = {
            "property":    self.prop.pk,
            "prospect":    self.prospect.pk,
            "scheduled_at": _dt(3),
        }
        resp = self.client.post(reverse("property-viewing-list"), payload, format="json")
        no_unit_pk = resp.data["id"]

        resp = self.client.post(
            reverse("property-viewing-convert-to-lease", args=[no_unit_pk]),
            self._convert_payload(),
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
