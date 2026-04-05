"""Fixtures specific to the maintenance test module."""
import pytest


@pytest.fixture
def maintenance_setup(tremly):
    """A maintenance request with tenant, unit, and supplier."""
    agent = tremly.create_agent()
    tenant = tremly.create_tenant()
    supplier = tremly.create_supplier_user()
    prop = tremly.create_property(agent=agent)
    unit = tremly.create_unit(property_obj=prop)
    lease = tremly.create_lease(unit=unit, tenant=tenant)
    mr = tremly.create_maintenance_request(unit=unit, tenant=tenant)
    return {
        "agent": agent, "tenant": tenant, "supplier": supplier,
        "property": prop, "unit": unit, "lease": lease, "request": mr
    }
