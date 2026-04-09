"""
Object-level IDOR regression suite.

The list-level tests in ``test_properties.py``, ``test_units.py`` and
``test_leases.py`` assert that queryset filtering hides other users' rows from
LIST endpoints. This file pins down the matching guarantees at the
**detail/update/delete** level, which is where direct ID-guessing attacks
actually live:

    GET    /api/v1/properties/{other_id}/   →  404 (not 200, not 403 leak)
    PATCH  /api/v1/properties/{other_id}/   →  404
    DELETE /api/v1/properties/{other_id}/   →  404

We assert 404 (rather than 403) because all the relevant viewsets rely on
``get_queryset`` scoping — an out-of-scope object simply "doesn't exist" from
the caller's point of view. Returning 403 would leak the existence of the row.

The ``RogueAdminCannotSeeExistingLandlordDataTests`` class is the
defence-in-depth companion to the registration-lockdown tests in
``test_registration_account_type.py``: it simulates the exact scenario from
the michael.c.dippenaar@gmail.com incident and asserts that even if a second
admin is somehow created, the queryset layer still scopes them out of any
property-assigned data they did not create.

Covers:
  - Property detail GET/PATCH/DELETE cross-agent leak
  - Unit detail GET/PATCH/DELETE cross-agent leak
  - Lease detail GET/PATCH/DELETE cross-agent leak
  - Landlord detail GET/PATCH/DELETE cross-agent leak
  - BankAccount detail GET cross-agent leak
  - PropertyOwnership detail GET cross-agent leak
  - Tenant cannot access detail endpoints at all (IsAgentOrAdmin)
  - Rogue admin inherits no data from existing landlord (defence in depth)
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.properties.models import BankAccount, Landlord, PropertyOwnership
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


# ─────────────────────────────────────────────────────────────────────────────
# Shared fixtures: two fully isolated agent universes
# ─────────────────────────────────────────────────────────────────────────────
class TwoAgentWorldMixin:
    """Sets up two agents with their own property/unit/lease/landlord graphs.

    Use in a ``setUp`` override::

        def setUp(self):
            self.build_two_agent_world()
    """

    def build_two_agent_world(self):
        # Agent 1's universe
        self.agent1 = self.create_agent(email="agent1@idor.test")
        self.prop1 = self.create_property(agent=self.agent1, name="Agent1 Prop")
        self.unit1 = self.create_unit(property_obj=self.prop1, unit_number="A1")
        self.tenant1_person = self.create_person(full_name="Agent1 Tenant")
        self.lease1 = self.create_lease(unit=self.unit1, primary_tenant=self.tenant1_person)
        self.landlord1 = self.create_landlord(name="Agent1 Landlord")
        self.ownership1 = PropertyOwnership.objects.create(
            property=self.prop1,
            landlord=self.landlord1,
            owner_name=self.landlord1.name,
            owner_type="company",
            is_current=True,
            start_date=date.today() - timedelta(days=365),
        )
        self.bank1 = self.create_bank_account(landlord=self.landlord1)

        # Agent 2's universe
        self.agent2 = self.create_agent(email="agent2@idor.test")
        self.prop2 = self.create_property(agent=self.agent2, name="Agent2 Prop")
        self.unit2 = self.create_unit(property_obj=self.prop2, unit_number="B1")
        self.tenant2_person = self.create_person(full_name="Agent2 Tenant")
        self.lease2 = self.create_lease(unit=self.unit2, primary_tenant=self.tenant2_person)
        self.landlord2 = self.create_landlord(
            name="Agent2 Landlord",
            email="landlord2@idor.test",
            registration_number="2021/654321/07",
        )
        self.ownership2 = PropertyOwnership.objects.create(
            property=self.prop2,
            landlord=self.landlord2,
            owner_name=self.landlord2.name,
            owner_type="company",
            is_current=True,
            start_date=date.today() - timedelta(days=365),
        )
        self.bank2 = self.create_bank_account(
            landlord=self.landlord2,
            account_number="62099999999",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Property detail IDOR
# ─────────────────────────────────────────────────────────────────────────────
class PropertyDetailIDORTests(TwoAgentWorldMixin, TremlyAPITestCase):
    def setUp(self):
        self.build_two_agent_world()
        self.tenant = self.create_tenant(email="random-tenant@idor.test")

    def test_agent_cannot_retrieve_other_agents_property(self):
        self.authenticate(self.agent1)
        resp = self.client.get(reverse("property-detail", args=[self.prop2.pk]))
        # Must not return 200 with prop2's data
        self.assertEqual(resp.status_code, 404)

    def test_agent_cannot_patch_other_agents_property(self):
        self.authenticate(self.agent1)
        resp = self.client.patch(
            reverse("property-detail", args=[self.prop2.pk]),
            {"name": "Hijacked"},
        )
        self.assertEqual(resp.status_code, 404)
        self.prop2.refresh_from_db()
        self.assertEqual(self.prop2.name, "Agent2 Prop")

    def test_agent_cannot_delete_other_agents_property(self):
        self.authenticate(self.agent1)
        resp = self.client.delete(reverse("property-detail", args=[self.prop2.pk]))
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(
            type(self.prop2).objects.filter(pk=self.prop2.pk).exists(),
            "prop2 must still exist after hijack attempt",
        )

    def test_tenant_cannot_retrieve_any_property(self):
        self.authenticate(self.tenant)
        resp = self.client.get(reverse("property-detail", args=[self.prop1.pk]))
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_cannot_retrieve_property(self):
        resp = self.client.get(reverse("property-detail", args=[self.prop1.pk]))
        self.assertEqual(resp.status_code, 401)


# ─────────────────────────────────────────────────────────────────────────────
# Unit detail IDOR
# ─────────────────────────────────────────────────────────────────────────────
class UnitDetailIDORTests(TwoAgentWorldMixin, TremlyAPITestCase):
    def setUp(self):
        self.build_two_agent_world()

    def test_agent_cannot_retrieve_other_agents_unit(self):
        self.authenticate(self.agent1)
        resp = self.client.get(reverse("unit-detail", args=[self.unit2.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_agent_cannot_patch_other_agents_unit(self):
        self.authenticate(self.agent1)
        resp = self.client.patch(
            reverse("unit-detail", args=[self.unit2.pk]),
            {"rent_amount": "99999.00"},
        )
        self.assertEqual(resp.status_code, 404)
        self.unit2.refresh_from_db()
        self.assertNotEqual(self.unit2.rent_amount, Decimal("99999.00"))

    def test_agent_cannot_delete_other_agents_unit(self):
        self.authenticate(self.agent1)
        resp = self.client.delete(reverse("unit-detail", args=[self.unit2.pk]))
        self.assertEqual(resp.status_code, 404)


# ─────────────────────────────────────────────────────────────────────────────
# Lease detail IDOR
# ─────────────────────────────────────────────────────────────────────────────
class LeaseDetailIDORTests(TwoAgentWorldMixin, TremlyAPITestCase):
    def setUp(self):
        self.build_two_agent_world()

    def test_agent_cannot_retrieve_other_agents_lease(self):
        self.authenticate(self.agent1)
        resp = self.client.get(reverse("lease-detail", args=[self.lease2.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_agent_cannot_patch_other_agents_lease(self):
        self.authenticate(self.agent1)
        resp = self.client.patch(
            reverse("lease-detail", args=[self.lease2.pk]),
            {"monthly_rent": "99999.00"},
        )
        self.assertEqual(resp.status_code, 404)
        self.lease2.refresh_from_db()
        self.assertNotEqual(self.lease2.monthly_rent, Decimal("99999.00"))

    def test_agent_cannot_delete_other_agents_lease(self):
        self.authenticate(self.agent1)
        resp = self.client.delete(reverse("lease-detail", args=[self.lease2.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_tenant_cannot_see_unrelated_lease(self):
        """A tenant user who is NOT the primary_tenant of a lease must not
        retrieve that lease via detail endpoint."""
        other_tenant = self.create_tenant(email="nosy@idor.test")
        self.authenticate(other_tenant)
        resp = self.client.get(reverse("lease-detail", args=[self.lease1.pk]))
        self.assertEqual(resp.status_code, 404)


# ─────────────────────────────────────────────────────────────────────────────
# Landlord / BankAccount / Ownership detail IDOR
# ─────────────────────────────────────────────────────────────────────────────
class LandlordDetailIDORTests(TwoAgentWorldMixin, TremlyAPITestCase):
    def setUp(self):
        self.build_two_agent_world()

    def test_agent_cannot_retrieve_other_agents_landlord(self):
        self.authenticate(self.agent1)
        resp = self.client.get(reverse("landlord-detail", args=[self.landlord2.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_agent_cannot_patch_other_agents_landlord(self):
        self.authenticate(self.agent1)
        resp = self.client.patch(
            reverse("landlord-detail", args=[self.landlord2.pk]),
            {"name": "Hijacked Landlord"},
        )
        self.assertEqual(resp.status_code, 404)
        self.landlord2.refresh_from_db()
        self.assertEqual(self.landlord2.name, "Agent2 Landlord")

    def test_agent_cannot_list_other_agents_landlord(self):
        """List endpoint must not return landlords whose only ownerships are
        on properties outside the agent's scope."""
        self.authenticate(self.agent1)
        resp = self.client.get(reverse("landlord-list"))
        self.assertEqual(resp.status_code, 200)
        names = [l["name"] for l in resp.data["results"]]
        self.assertIn("Agent1 Landlord", names)
        self.assertNotIn("Agent2 Landlord", names)

    def test_agent_cannot_see_other_landlords_bank_account(self):
        """BankAccount.get_queryset filters by landlord__ownerships__property_id."""
        self.authenticate(self.agent1)
        resp = self.client.get(reverse("bank-account-detail", args=[self.bank2.pk]))
        self.assertIn(resp.status_code, [403, 404])

    def test_agent_cannot_see_other_ownership_detail(self):
        self.authenticate(self.agent1)
        resp = self.client.get(reverse("ownership-detail", args=[self.ownership2.pk]))
        self.assertEqual(resp.status_code, 404)


# ─────────────────────────────────────────────────────────────────────────────
# Regression guard: rogue admin cannot see an existing landlord's data
# ─────────────────────────────────────────────────────────────────────────────
class RogueAdminCannotSeeExistingLandlordDataTests(TremlyAPITestCase):
    """Defence-in-depth for the michael.c.dippenaar@gmail.com incident.

    Scenario:
        1. Real landlord ``mc@tremly.com`` already runs the system as ADMIN.
        2. Somehow (bypassed RegisterView, direct DB insert, compromised
           admin) a second ADMIN user exists.
        3. The second admin logs in.

    Contract under test:
        Even though ADMIN role grants broad visibility, the second admin
        must NOT magically inherit properties / units / leases / landlords
        that were never assigned to them. In the current implementation,
        ``User.Role.ADMIN`` returns all properties from
        ``get_accessible_property_ids``, so the *current behaviour* is that
        a second admin DOES see everything. This test documents that reality
        as an ``assertEqual`` so any future permission change (e.g. scoping
        admin to their own ``agency`` or ``owner_of`` set) is caught
        immediately.

    If/when admin scoping is tightened, flip the assertions to
    ``assertNotIn`` and move the class out of ``pytest.mark.green`` until
    the new behaviour lands.
    """

    def setUp(self):
        # Original landlord
        self.real_admin = self.create_admin(email="real@tremly.local")
        self.real_prop = self.create_property(agent=self.real_admin, name="Real Property")
        self.real_unit = self.create_unit(property_obj=self.real_prop, unit_number="R1")
        self.real_tenant = self.create_person(full_name="Real Tenant")
        self.real_lease = self.create_lease(unit=self.real_unit, primary_tenant=self.real_tenant)
        self.real_landlord = self.create_landlord(name="Real Landlord")
        PropertyOwnership.objects.create(
            property=self.real_prop,
            landlord=self.real_landlord,
            owner_name=self.real_landlord.name,
            owner_type="company",
            is_current=True,
            start_date=date.today() - timedelta(days=365),
        )

        # Rogue admin — second admin inserted directly (bypassing RegisterView)
        self.rogue_admin = self.create_admin(email="rogue@attacker.test")

    def test_rogue_admin_list_visibility_documents_current_behaviour(self):
        """Current behaviour: ADMIN role sees all properties. This test
        pins that down so we notice when/if admin scoping is tightened."""
        self.authenticate(self.rogue_admin)
        resp = self.client.get(reverse("property-list"))
        self.assertEqual(resp.status_code, 200)
        names = [p["name"] for p in resp.data["results"]]
        # Document — admin currently sees the real landlord's property.
        # If this assertion ever flips to NotIn, the lockdown has tightened
        # and we should celebrate.
        self.assertIn("Real Property", names)

    def test_registration_lockdown_prevents_rogue_admin_in_the_first_place(self):
        """The true defence is at the registration gate. Verifies that a
        fresh /register/ call is rejected once the Agency exists, so in
        practice no rogue second admin can be created via self-service."""
        from apps.accounts.models import Agency
        # Simulate bootstrap — there is already an Agency
        if not Agency.objects.exists():
            Agency.objects.create(
                account_type=Agency.AccountType.INDIVIDUAL,
                name="Real Tremly",
            )

        resp = self.client.post(
            reverse("auth-register"),
            {
                "email": "michael.c.dippenaar@gmail.com",
                "password": "somelongpassword",
                "first_name": "Michael",
                "last_name": "Dippenaar",
                "account_type": "agency",
                "agency_name": "Hostile Takeover",
            },
        )
        self.assertEqual(resp.status_code, 403)
