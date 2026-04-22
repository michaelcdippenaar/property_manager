"""
Integration tests for Tenant API views.

Covers:
- GET /api/v1/tenants/ (agent required)
- POST /api/v1/tenants/assign-unit/
"""
import pytest
from datetime import date

pytestmark = [pytest.mark.integration, pytest.mark.green]


@pytest.fixture
def tenant_api_setup(db, tremly):
    """Create agent, person, and property + unit for tenant tests."""
    agent = tremly.create_agent(email="agent@tenanttest.com")
    person = tremly.create_person(full_name="Carlo Tenant", email="carlo@tenants.com")
    prop = tremly.create_property(agent=agent)
    unit = tremly.create_unit(property_obj=prop)
    return {"agent": agent, "person": person, "property": prop, "unit": unit}


TENANT_LIST_URL = "/api/v1/tenant/tenants/"
ASSIGN_UNIT_URL = "/api/v1/tenant/tenants/assign-unit/"


class TestTenantListView:
    def test_unauthenticated_returns_401(self, db, api_client):
        response = api_client.get(TENANT_LIST_URL)
        assert response.status_code == 401

    def test_tenant_user_cannot_list(self, db, tremly, api_client):
        """Tenants cannot access the tenant management list."""
        tenant_user = tremly.create_tenant(email="portal@tenant.com")
        api_client.force_authenticate(user=tenant_user)
        response = api_client.get(TENANT_LIST_URL)
        assert response.status_code == 403

    def test_agent_can_list_tenants(self, api_client, tenant_api_setup):
        from apps.tenant.models import Tenant
        agent = tenant_api_setup["agent"]
        person = tenant_api_setup["person"]
        Tenant.objects.create(person=person)
        api_client.force_authenticate(user=agent)
        response = api_client.get(TENANT_LIST_URL)
        assert response.status_code == 200
        data = response.json()
        # Accept both plain list and paginated response
        assert isinstance(data, list) or "results" in data


class TestAssignUnitAction:
    def test_valid_assignment_returns_201(self, api_client, tenant_api_setup):
        from apps.tenant.models import Tenant
        agent = tenant_api_setup["agent"]
        person = tenant_api_setup["person"]
        unit = tenant_api_setup["unit"]
        tenant = Tenant.objects.create(person=person)
        api_client.force_authenticate(user=agent)
        payload = {
            "tenant_id": tenant.pk,
            "unit_id": unit.pk,
            "start_date": "2026-05-01",
            "end_date": None,
            "notes": "",
        }
        response = api_client.post(ASSIGN_UNIT_URL, payload, format="json")
        assert response.status_code == 201

    def test_overlapping_assignment_returns_400(self, api_client, tenant_api_setup):
        from apps.tenant.models import Tenant, TenantUnitAssignment
        agent = tenant_api_setup["agent"]
        person = tenant_api_setup["person"]
        unit = tenant_api_setup["unit"]
        prop = tenant_api_setup["property"]
        tenant = Tenant.objects.create(person=person)
        # Create an existing open assignment
        TenantUnitAssignment.objects.create(
            tenant=tenant,
            unit=unit,
            property=prop,
            start_date=date(2026, 1, 1),
            end_date=None,
            source="manual",
        )
        api_client.force_authenticate(user=agent)
        payload = {
            "tenant_id": tenant.pk,
            "unit_id": unit.pk,
            "start_date": "2026-05-01",
            "end_date": None,
            "notes": "",
        }
        response = api_client.post(ASSIGN_UNIT_URL, payload, format="json")
        assert response.status_code == 400
