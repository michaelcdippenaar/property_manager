"""
Integration tests for the atomic lease importer.

Source file under test: apps/leases/import_view.py
  - ImportLeaseView             — POST /api/v1/leases/import/
  - _get_or_create_person helper

The importer is the last step of the lease-onboarding flow: after the
frontend has reviewed the AI-parsed data, it POSTs the finalized payload
here and the view atomically creates Property → Unit → Persons → Lease →
Tenant/Occupant/Guarantor rows.

Covers:
  - Auth: unauthenticated → 401
  - Validation errors (400):
      * missing property.name when creating new property
      * nonexistent property_id
      * nonexistent unit_id
      * missing primary_tenant.full_name
      * missing start_date or end_date
  - Happy paths:
      * create-new-property (end-to-end)
      * reuse existing property_id
      * reuse existing unit (same unit_number on existing property)
      * auto-generated lease_number when none provided
      * preserve explicit lease_number
      * co-tenants / occupants / guarantors created
      * guarantor.covers_tenant wired by name match
      * Person deduplication by id_number
  - Atomicity:
      * failure mid-import rolls back the whole transaction
  - Role handling:
      * agent user → new Property.agent is themselves
      * admin user with managing_agent_id → Property.agent is the chosen agent
"""
import pytest
from django.urls import reverse

from apps.accounts.models import Person, User
from apps.leases.models import Lease, LeaseGuarantor, LeaseOccupant, LeaseTenant
from apps.properties.models import Property, Unit
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


BASE_PAYLOAD = {
    "primary_tenant": {
        "full_name": "Thabo Mokoena",
        "id_number": "9001015800087",
        "phone": "0812345678",
        "email": "thabo@tenant.test",
    },
    "start_date": "2026-05-01",
    "end_date": "2027-04-30",
    "monthly_rent": 12500,
    "deposit": 25000,
}


class ImportLeaseViewAuthTests(TremlyAPITestCase):
    url = reverse("lease-import")

    def test_unauthenticated_returns_401(self):
        resp = self.client.post(self.url, BASE_PAYLOAD, format="json")
        self.assertEqual(resp.status_code, 401)


class ImportLeaseViewValidationTests(TremlyAPITestCase):
    url = reverse("lease-import")

    def setUp(self):
        self.agent = self.create_agent(email="importer-agent@lease.test")
        self.authenticate(self.agent)

    def test_missing_property_name_returns_400(self):
        payload = {**BASE_PAYLOAD, "property": {}}
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("property.name is required", resp.data["error"])

    def test_nonexistent_property_id_returns_400(self):
        payload = {**BASE_PAYLOAD, "property_id": 999_999}
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Property not found", resp.data["error"])

    def test_nonexistent_unit_id_returns_400(self):
        prop = self.create_property(agent=self.agent, name="Prop A")
        payload = {
            **BASE_PAYLOAD,
            "property_id": prop.id,
            "unit_id": 999_999,
        }
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Unit not found", resp.data["error"])

    def test_missing_primary_tenant_name_returns_400(self):
        payload = {**BASE_PAYLOAD, "primary_tenant": {}, "property": {"name": "Prop B"}}
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("primary_tenant.full_name is required", resp.data["error"])

    def test_missing_start_date_returns_400(self):
        payload = {**BASE_PAYLOAD, "property": {"name": "Prop C"}}
        payload.pop("start_date")
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("start_date is required", resp.data["error"])

    def test_missing_end_date_returns_400(self):
        payload = {**BASE_PAYLOAD, "property": {"name": "Prop D"}}
        payload.pop("end_date")
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("end_date is required", resp.data["error"])


class ImportLeaseCreateNewPropertyTests(TremlyAPITestCase):
    """Happy path — create property + unit + persons + lease from scratch."""
    url = reverse("lease-import")

    def setUp(self):
        self.agent = self.create_agent(email="new-prop-agent@lease.test")
        self.authenticate(self.agent)

    def test_end_to_end_creates_all_rows(self):
        payload = {
            **BASE_PAYLOAD,
            "property": {
                "name": "La Colline 18",
                "property_type": "house",
                "address": "18 Irene Park",
                "city": "Stellenbosch",
                "province": "Western Cape",
                "postal_code": "7600",
            },
            "unit": {"unit_number": "1", "bedrooms": 3, "bathrooms": 2},
            "co_tenants": [
                {
                    "full_name": "Lerato Mokoena",
                    "id_number": "9205056000088",
                    "phone": "0823456789",
                },
            ],
            "occupants": [
                {
                    "full_name": "Amogelang Mokoena",
                    "relationship_to_tenant": "child",
                },
            ],
            "guarantors": [
                {
                    "full_name": "Sipho Mokoena",
                    "id_number": "6003035100080",
                    "for_tenant": "Thabo Mokoena",
                }
            ],
        }
        resp = self.client.post(self.url, payload, format="json")

        self.assertEqual(resp.status_code, 201, resp.data)
        lease = Lease.objects.get(pk=resp.data["id"])

        # Property
        self.assertTrue(Property.objects.filter(name="La Colline 18").exists())
        self.assertEqual(lease.unit.property.agent, self.agent)
        self.assertEqual(lease.unit.property.city, "Stellenbosch")

        # Unit
        self.assertEqual(lease.unit.unit_number, "1")
        self.assertEqual(lease.unit.bedrooms, 3)

        # Persons
        self.assertEqual(lease.primary_tenant.full_name, "Thabo Mokoena")
        self.assertEqual(lease.primary_tenant.id_number, "9001015800087")
        self.assertEqual(lease.co_tenants.count(), 1)
        self.assertEqual(lease.co_tenants.first().person.full_name, "Lerato Mokoena")
        self.assertEqual(lease.occupants.count(), 1)
        self.assertEqual(lease.occupants.first().relationship_to_tenant, "child")

        # Guarantor wired to covers_tenant by name match
        self.assertEqual(lease.guarantors.count(), 1)
        g = lease.guarantors.first()
        self.assertEqual(g.person.full_name, "Sipho Mokoena")
        self.assertEqual(g.covers_tenant.full_name, "Thabo Mokoena")

        # Lease finance (stored as Decimal — compare numerically)
        from decimal import Decimal
        self.assertEqual(lease.monthly_rent, Decimal("12500"))
        self.assertEqual(lease.deposit, Decimal("25000"))

        # Auto-generated lease number format: L-YYYYMM-XXXX
        self.assertRegex(lease.lease_number, r"^L-\d{6}-\d{4}$")

    def test_explicit_lease_number_is_preserved(self):
        payload = {
            **BASE_PAYLOAD,
            "property": {"name": "Preserved Ref"},
            "lease_number": "CUSTOM-REF-2026",
        }
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 201)
        lease = Lease.objects.get(pk=resp.data["id"])
        self.assertEqual(lease.lease_number, "CUSTOM-REF-2026")


class ImportLeaseReuseExistingTests(TremlyAPITestCase):
    url = reverse("lease-import")

    def setUp(self):
        self.agent = self.create_agent(email="reuse-agent@lease.test")
        self.authenticate(self.agent)
        self.existing_prop = self.create_property(agent=self.agent, name="Existing Tower")
        self.existing_unit = self.create_unit(
            property_obj=self.existing_prop, unit_number="A5"
        )

    def test_reuses_existing_property_via_property_id(self):
        payload = {**BASE_PAYLOAD, "property_id": self.existing_prop.id}
        # No unit_id — importer should create/find a "1" unit by default
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 201)

        lease = Lease.objects.get(pk=resp.data["id"])
        self.assertEqual(lease.unit.property, self.existing_prop)
        # Did not duplicate the property row
        self.assertEqual(Property.objects.filter(name="Existing Tower").count(), 1)

    def test_reuses_existing_unit_via_unit_id(self):
        payload = {
            **BASE_PAYLOAD,
            "property_id": self.existing_prop.id,
            "unit_id": self.existing_unit.id,
        }
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 201)

        lease = Lease.objects.get(pk=resp.data["id"])
        self.assertEqual(lease.unit, self.existing_unit)

    def test_reuses_existing_unit_by_unit_number_match(self):
        """If property_id is passed without unit_id, but unit.unit_number
        matches an existing one, reuse rather than duplicate."""
        payload = {
            **BASE_PAYLOAD,
            "property_id": self.existing_prop.id,
            "unit": {"unit_number": "A5"},
        }
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 201)

        lease = Lease.objects.get(pk=resp.data["id"])
        self.assertEqual(lease.unit, self.existing_unit)
        # And not duplicated
        self.assertEqual(
            Unit.objects.filter(property=self.existing_prop, unit_number="A5").count(),
            1,
        )


class ImportLeasePersonDeduplicationTests(TremlyAPITestCase):
    url = reverse("lease-import")

    def setUp(self):
        self.agent = self.create_agent(email="dedupe-agent@lease.test")
        self.authenticate(self.agent)

    def test_existing_person_reused_by_id_number(self):
        existing = Person.objects.create(
            full_name="Thabo Mokoena",
            id_number="9001015800087",
            person_type="individual",
        )
        before = Person.objects.count()

        payload = {
            **BASE_PAYLOAD,
            "property": {"name": "Dedup Prop"},
        }
        resp = self.client.post(self.url, payload, format="json")

        self.assertEqual(resp.status_code, 201)
        # No new Person created for the primary tenant
        self.assertEqual(Person.objects.count(), before)

        lease = Lease.objects.get(pk=resp.data["id"])
        self.assertEqual(lease.primary_tenant, existing)

    def test_different_name_same_id_still_dedupes(self):
        """ID number is the unique identifier — even if Claude OCR misread
        the name, the existing Person must be reused."""
        existing = Person.objects.create(
            full_name="Thabo Mokoena",
            id_number="9001015800087",
            person_type="individual",
        )

        payload = {
            **BASE_PAYLOAD,
            "property": {"name": "Same ID Prop"},
            "primary_tenant": {
                "full_name": "Thabo Mokena",  # misspelling
                "id_number": "9001015800087",
            },
        }
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 201)
        lease = Lease.objects.get(pk=resp.data["id"])
        self.assertEqual(lease.primary_tenant, existing)


class ImportLeaseAtomicityTests(TremlyAPITestCase):
    """Regression pins for the ``@transaction.atomic`` contract on ImportLeaseView.

    KNOWN BUG documented by ``test_property_leaks_when_unit_lookup_fails``:
        The view is decorated with ``@transaction.atomic`` but all its
        validation branches ``return Response(status=400)`` instead of
        raising a ``ValidationError``. ``@transaction.atomic`` only rolls
        back on *raised* exceptions, so mid-flow 400s leak any rows that
        were already created (Property, Unit, etc.).

        The correct fix is to raise ``rest_framework.exceptions.ValidationError``
        from each validation branch, or manually ``transaction.set_rollback(True)``
        before returning the error response.

        Until that fix lands, this test asserts the **current leaky
        behaviour** so we notice the day someone tightens it up (the
        assertion will flip to failing and should be updated to
        ``assertFalse(...)``).

    Also covers:
        - An actual raised exception does roll back (positive atomicity).
    """
    url = reverse("lease-import")

    def setUp(self):
        self.agent = self.create_agent(email="atomic-agent@lease.test")
        self.authenticate(self.agent)

    def test_property_leaks_when_unit_lookup_fails(self):
        """BUG PIN — current behaviour. See class docstring.

        When unit_id points to a nonexistent unit, the view returns 400
        but the Property row created earlier in the method is committed.
        """
        before_props = Property.objects.count()
        payload = {
            **BASE_PAYLOAD,
            "property": {"name": "Leaky Property"},
            "unit_id": 999_999,
        }
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 400)
        # Current (buggy) behaviour: the property WAS committed.
        self.assertEqual(
            Property.objects.count(), before_props + 1,
            "Expected the leaky Property row to still be present. If this "
            "fails, the atomicity bug has been fixed — update this test to "
            "assert rollback instead.",
        )
        self.assertTrue(Property.objects.filter(name="Leaky Property").exists())

    def test_raised_exception_inside_importer_rolls_back(self):
        """Positive atomicity — a real raised exception in the middle of
        the importer DOES roll everything back.

        We force a failure by patching ``Lease.objects.create`` to raise
        AFTER Property + Unit are created. The @transaction.atomic
        decorator must catch the raise and roll the earlier inserts back.
        """
        from unittest import mock

        before_props = Property.objects.count()
        before_units = Unit.objects.count()
        payload = {
            **BASE_PAYLOAD,
            "property": {"name": "Will Rollback Prop"},
        }

        with mock.patch(
            "apps.leases.import_view.Lease.objects.create",
            side_effect=RuntimeError("simulated DB error"),
        ):
            with self.assertRaises(RuntimeError):
                self.client.post(self.url, payload, format="json")

        self.assertEqual(Property.objects.count(), before_props)
        self.assertEqual(Unit.objects.count(), before_units)
        self.assertFalse(Property.objects.filter(name="Will Rollback Prop").exists())


class ImportLeaseRoleHandlingTests(TremlyAPITestCase):
    """Property.agent assignment depends on the caller's role."""
    url = reverse("lease-import")

    def test_agent_becomes_property_agent(self):
        agent = self.create_agent(email="owner-agent@lease.test")
        self.authenticate(agent)

        resp = self.client.post(
            self.url,
            {**BASE_PAYLOAD, "property": {"name": "Agent Prop"}},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        lease = Lease.objects.get(pk=resp.data["id"])
        self.assertEqual(lease.unit.property.agent, agent)

    def test_admin_can_assign_managing_agent(self):
        admin = self.create_admin(email="admin@lease.test")
        target_agent = self.create_agent(email="target-agent@lease.test")
        self.authenticate(admin)

        resp = self.client.post(
            self.url,
            {
                **BASE_PAYLOAD,
                "property": {"name": "Admin Assigns Prop"},
                "managing_agent_id": target_agent.id,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        lease = Lease.objects.get(pk=resp.data["id"])
        self.assertEqual(lease.unit.property.agent, target_agent)

    def test_admin_without_managing_agent_id_leaves_agent_null(self):
        admin = self.create_admin(email="admin2@lease.test")
        self.authenticate(admin)

        resp = self.client.post(
            self.url,
            {**BASE_PAYLOAD, "property": {"name": "Admin No Agent Prop"}},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        lease = Lease.objects.get(pk=resp.data["id"])
        self.assertIsNone(lease.unit.property.agent)
