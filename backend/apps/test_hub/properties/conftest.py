"""Fixtures specific to the properties test module."""
import pytest


@pytest.fixture
def prop_with_units(tremly):
    """A property with 3 units (2 available, 1 occupied)."""
    agent = tremly.create_agent()
    prop = tremly.create_property(agent=agent)
    u1 = tremly.create_unit(property_obj=prop, status="available")
    u2 = tremly.create_unit(property_obj=prop, status="available")
    u3 = tremly.create_unit(property_obj=prop, status="occupied")
    return prop, [u1, u2, u3]
