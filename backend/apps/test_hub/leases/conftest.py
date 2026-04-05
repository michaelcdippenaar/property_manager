"""Fixtures specific to the leases test module."""
import pytest


@pytest.fixture
def lease_setup(tremly):
    """An active lease with all related objects."""
    agent = tremly.create_agent()
    tenant = tremly.create_tenant()
    prop = tremly.create_property(agent=agent)
    unit = tremly.create_unit(property_obj=prop)
    lease = tremly.create_lease(unit=unit, tenant=tenant)
    return {"agent": agent, "tenant": tenant, "property": prop, "unit": unit, "lease": lease}
