"""
UX-008 — Move-in prep checklist: serializer + permission tests.

Tests:
  1. GET returns default items seeded automatically
  2. Agent can tick (complete) and untick an item
  3. Owner receives 403 on PATCH
  4. Tenant receives 403 on PATCH
  5. Serializer exposes key_label and completed_by_name
  6. Migration round-trip: existing lease has no checklist rows initially (no data loss)

Run:
    cd backend && pytest apps/leases/tests/test_move_in_checklist.py -v
"""
from __future__ import annotations

import pytest
from django.urls import reverse

from apps.leases.models import MoveInChecklistItem, MOVE_IN_CHECKLIST_DEFAULTS
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


class MoveInChecklistTests(TremlyAPITestCase):

    def setUp(self):
        from apps.accounts.models import Agency
        self.agency = Agency.objects.create(name="Test Agency MoveIn")
        self.agent = self.create_agent(
            email="agent-ci@test.com", first_name="Agent", last_name="Smith",
            agency=self.agency,
        )
        self.owner = self.create_owner_user(email="owner-ci@test.com", agency=self.agency)
        self.tenant_user = self.create_tenant(email="tenant-ci@test.com", agency=self.agency)
        self.prop = self.create_property(agent=self.agent, agency=self.agency)
        self.unit = self.create_unit(property_obj=self.prop, agency=self.agency)
        self.lease = self.create_lease(unit=self.unit, status="active", agency=self.agency)

    # ── GET: seed + return all items ─────────────────────────────────────── #

    def test_get_seeds_default_items(self):
        """First GET should auto-seed all 4 default checklist items."""
        self.authenticate(self.agent)
        url = reverse("lease-move-in-checklist", kwargs={"pk": self.lease.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        keys = {item["key"] for item in resp.data}
        expected = {k for k in MOVE_IN_CHECKLIST_DEFAULTS}
        self.assertEqual(keys, expected)

    def test_get_is_idempotent_no_duplicate_seeding(self):
        """Calling GET twice should not create duplicate items."""
        self.authenticate(self.agent)
        url = reverse("lease-move-in-checklist", kwargs={"pk": self.lease.pk})
        self.client.get(url)
        self.client.get(url)
        count = MoveInChecklistItem.objects.filter(lease=self.lease).count()
        self.assertEqual(count, len(MOVE_IN_CHECKLIST_DEFAULTS))

    def test_get_returns_key_label(self):
        """key_label should be the human-readable display value."""
        self.authenticate(self.agent)
        url = reverse("lease-move-in-checklist", kwargs={"pk": self.lease.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        labels = {item["key_label"] for item in resp.data}
        self.assertIn("Keys handed over", labels)
        self.assertIn("Utilities notified", labels)
        self.assertIn("Tenant app invite sent", labels)
        self.assertIn("Welcome pack delivered", labels)

    # ── PATCH: agent can toggle items ────────────────────────────────────── #

    def test_agent_can_complete_item(self):
        """Agent PATCH with is_completed=true should mark item done and record who/when."""
        self.authenticate(self.agent)
        # Seed first
        self.client.get(reverse("lease-move-in-checklist", kwargs={"pk": self.lease.pk}))

        url = reverse(
            "lease-toggle-move-in-item",
            args=[self.lease.pk, "keys_handover"],
        )
        resp = self.client.patch(url, {"is_completed": True}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["is_completed"])
        self.assertIsNotNone(resp.data["completed_at"])
        self.assertEqual(resp.data["completed_by_name"], "Agent Smith")

    def test_agent_can_untick_item(self):
        """Agent PATCH with is_completed=false should clear completion state."""
        self.authenticate(self.agent)
        self.client.get(reverse("lease-move-in-checklist", kwargs={"pk": self.lease.pk}))
        patch_url = reverse(
            "lease-toggle-move-in-item",
            kwargs={"pk": self.lease.pk, "item_key": "keys_handover"},
        )
        # Tick first
        self.client.patch(patch_url, {"is_completed": True}, format="json")
        # Untick
        resp = self.client.patch(patch_url, {"is_completed": False}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["is_completed"])
        self.assertIsNone(resp.data["completed_at"])
        self.assertIsNone(resp.data["completed_by_name"])

    # ── PATCH: permission enforcement ────────────────────────────────────── #

    def test_owner_cannot_patch_checklist(self):
        """Owner role should receive 403 on PATCH."""
        self.authenticate(self.agent)
        self.client.get(reverse("lease-move-in-checklist", kwargs={"pk": self.lease.pk}))

        self.authenticate(self.owner)
        url = reverse(
            "lease-toggle-move-in-item",
            args=[self.lease.pk, "keys_handover"],
        )
        resp = self.client.patch(url, {"is_completed": True}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_tenant_cannot_patch_checklist(self):
        """Tenant role should receive 403 on PATCH."""
        # Tenant needs to access the lease — create a lease owned by them
        tenant_person = self.create_person(full_name="Tenant CI", linked_user=self.tenant_user)
        lease2 = self.create_lease(unit=self.unit, primary_tenant=tenant_person, status="active")

        self.authenticate(self.agent)
        self.client.get(reverse("lease-move-in-checklist", kwargs={"pk": lease2.pk}))

        self.authenticate(self.tenant_user)
        url = reverse(
            "lease-toggle-move-in-item",
            kwargs={"pk": lease2.pk, "item_key": "keys_handover"},
        )
        resp = self.client.patch(url, {"is_completed": True}, format="json")
        self.assertEqual(resp.status_code, 403)

    # ── Data integrity ───────────────────────────────────────────────────── #

    def test_existing_lease_has_no_checklist_rows(self):
        """A pre-existing lease should start with zero checklist rows (no migration data loss)."""
        fresh_lease = self.create_lease(unit=self.unit, status="active")
        count = MoveInChecklistItem.objects.filter(lease=fresh_lease).count()
        self.assertEqual(count, 0)

    def test_lease_serializer_includes_move_in_checklist(self):
        """LeaseSerializer should expose move_in_checklist as a list."""
        from apps.leases.serializers import LeaseSerializer
        # Seed items
        for key in MOVE_IN_CHECKLIST_DEFAULTS:
            MoveInChecklistItem.objects.get_or_create(lease=self.lease, key=key)
        from apps.leases.models import Lease
        lease = Lease.objects.prefetch_related("move_in_checklist__completed_by").get(pk=self.lease.pk)
        data = LeaseSerializer(lease).data
        self.assertIn("move_in_checklist", data)
        self.assertEqual(len(data["move_in_checklist"]), len(MOVE_IN_CHECKLIST_DEFAULTS))
