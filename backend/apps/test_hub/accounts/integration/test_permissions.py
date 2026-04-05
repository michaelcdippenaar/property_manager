"""
Tests for RBAC endpoint access, user management, and invite flows.

Covers:
  P2 - Role-based access control on core endpoints
  P3 - Admin-only user management (list, filter, search, update, deactivate)
  P3 - Admin-only invite workflow
"""
import pytest
from django.urls import reverse

from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


# ---------------------------------------------------------------------------
# P2: RBAC Endpoint Access
# ---------------------------------------------------------------------------

class PropertyEndpointPermissionTests(TremlyAPITestCase):
    """Tenant cannot access property list; agent can."""

    def setUp(self):
        self.agent = self.create_agent()
        self.tenant = self.create_tenant()
        self.create_property(agent=self.agent)
        self.url = reverse("property-list")

    def test_tenant_cannot_list_properties(self):
        self.authenticate(self.tenant)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_agent_can_list_properties(self):
        self.authenticate(self.agent)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_admin_can_list_properties(self):
        admin = self.create_admin()
        self.authenticate(admin)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_owner_cannot_list_properties(self):
        owner = self.create_owner_user()
        self.authenticate(owner)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_cannot_list_properties(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 401)


class PersonEndpointPermissionTests(TremlyAPITestCase):
    """Tenant cannot access the persons list."""

    def setUp(self):
        self.url = reverse("persons-list")

    def test_tenant_cannot_list_persons(self):
        tenant = self.create_tenant()
        self.authenticate(tenant)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_agent_can_list_persons(self):
        agent = self.create_agent()
        self.authenticate(agent)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)


class LeaseTemplateEndpointPermissionTests(TremlyAPITestCase):
    """Tenant cannot access lease templates; admin/agent can."""

    def setUp(self):
        self.url = reverse("lease-templates")

    def test_tenant_cannot_list_lease_templates(self):
        tenant = self.create_tenant()
        self.authenticate(tenant)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_list_lease_templates(self):
        admin = self.create_admin()
        self.authenticate(admin)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_agent_can_list_lease_templates(self):
        agent = self.create_agent()
        self.authenticate(agent)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)


class OwnerDashboardPermissionTests(TremlyAPITestCase):
    """Owner can access dashboard; tenant cannot."""

    def setUp(self):
        self.url = reverse("owner-dashboard")

    def test_owner_can_access_dashboard(self):
        owner = self.create_owner_user()
        self.authenticate(owner)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_tenant_cannot_access_dashboard(self):
        tenant = self.create_tenant()
        self.authenticate(tenant)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_agent_can_access_dashboard(self):
        """Agents are staff and can access the owner dashboard."""
        agent = self.create_agent()
        self.authenticate(agent)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_supplier_cannot_access_dashboard(self):
        supplier = self.create_supplier_user()
        self.authenticate(supplier)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# P3: User Management (Admin-only)
# ---------------------------------------------------------------------------

class UserListViewTests(TremlyAPITestCase):
    """Admin can list, filter, and search users; others cannot."""

    def setUp(self):
        self.admin = self.create_admin()
        self.agent = self.create_agent()
        self.tenant = self.create_tenant(
            email="tenant@test.com", first_name="John", last_name="Doe",
        )
        self.url = reverse("user-list")

    def test_admin_can_list_users(self):
        self.authenticate(self.admin)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_agent_cannot_list_users(self):
        self.authenticate(self.agent)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_tenant_cannot_list_users(self):
        self.authenticate(self.tenant)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_cannot_list_users(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 401)

    def test_admin_can_filter_users_by_role(self):
        self.authenticate(self.admin)
        resp = self.client.get(self.url, {"role": "tenant"})
        self.assertEqual(resp.status_code, 200)
        emails = [u["email"] for u in resp.data["results"]] if "results" in resp.data else [u["email"] for u in resp.data]
        self.assertIn("tenant@test.com", emails)
        self.assertNotIn("agent@test.com", emails)

    def test_admin_can_search_users(self):
        self.authenticate(self.admin)
        resp = self.client.get(self.url, {"search": "john"})
        self.assertEqual(resp.status_code, 200)
        emails = [u["email"] for u in resp.data["results"]] if "results" in resp.data else [u["email"] for u in resp.data]
        self.assertIn("tenant@test.com", emails)


class UserDetailViewTests(TremlyAPITestCase):
    """Admin can update/deactivate users; others cannot."""

    def setUp(self):
        self.admin = self.create_admin()
        self.agent = self.create_agent()
        self.tenant = self.create_tenant()

    def test_admin_can_update_user_role(self):
        self.authenticate(self.admin)
        url = reverse("user-detail", args=[self.tenant.pk])
        resp = self.client.patch(url, {"role": "agent"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.role, "agent")

    def test_admin_cannot_change_own_role(self):
        self.authenticate(self.admin)
        url = reverse("user-detail", args=[self.admin.pk])
        resp = self.client.patch(url, {"role": "tenant"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, "admin")

    def test_admin_can_deactivate_user(self):
        self.authenticate(self.admin)
        url = reverse("user-detail", args=[self.tenant.pk])
        resp = self.client.delete(url)
        self.assertIn(resp.status_code, [200, 204])
        self.tenant.refresh_from_db()
        self.assertFalse(self.tenant.is_active)

    def test_non_admin_cannot_update_user(self):
        self.authenticate(self.agent)
        url = reverse("user-detail", args=[self.tenant.pk])
        resp = self.client.patch(url, {"role": "admin"}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_tenant_cannot_update_user(self):
        self.authenticate(self.tenant)
        url = reverse("user-detail", args=[self.agent.pk])
        resp = self.client.patch(url, {"role": "tenant"}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_non_admin_cannot_deactivate_user(self):
        self.authenticate(self.agent)
        url = reverse("user-detail", args=[self.tenant.pk])
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# P3: Invite
# ---------------------------------------------------------------------------

class InviteUserViewTests(TremlyAPITestCase):
    """Admin can invite users; others cannot."""

    def setUp(self):
        self.admin = self.create_admin()
        self.agent = self.create_agent()
        self.tenant = self.create_tenant()
        self.url = reverse("user-invite")

    def test_admin_can_invite_user(self):
        self.authenticate(self.admin)
        resp = self.client.post(self.url, {
            "email": "newuser@example.com",
            "role": "tenant",
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertIn("token", resp.data)

    def test_invite_with_existing_email_returns_400(self):
        self.authenticate(self.admin)
        resp = self.client.post(self.url, {
            "email": "tenant@test.com",
            "role": "tenant",
        }, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_agent_cannot_invite(self):
        self.authenticate(self.agent)
        resp = self.client.post(self.url, {
            "email": "someone@example.com",
            "role": "tenant",
        }, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_tenant_cannot_invite(self):
        self.authenticate(self.tenant)
        resp = self.client.post(self.url, {
            "email": "someone@example.com",
            "role": "agent",
        }, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_cannot_invite(self):
        resp = self.client.post(self.url, {
            "email": "someone@example.com",
            "role": "tenant",
        }, format="json")
        self.assertEqual(resp.status_code, 401)
