"""Fixtures specific to the esigning test module."""
import pytest


@pytest.fixture
def lease_for_signing(tremly):
    """A lease ready for e-signing."""
    agent = tremly.create_agent()
    tenant = tremly.create_tenant()
    prop = tremly.create_property(agent=agent)
    unit = tremly.create_unit(property_obj=prop)
    lease = tremly.create_lease(unit=unit, tenant=tenant)
    return {"agent": agent, "tenant": tenant, "lease": lease, "unit": unit}
