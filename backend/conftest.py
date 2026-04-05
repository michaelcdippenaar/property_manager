"""
Root pytest configuration for the Tremly test suite.

TDD enforcement:
- @pytest.mark.red  → xfail(strict=True): test MUST fail (implementation not written yet)
- @pytest.mark.green → must pass
- @pytest.mark.unit → no DB, fast
- @pytest.mark.integration → uses DB + API client
"""
import pytest
from unittest.mock import Mock
from rest_framework.test import APIClient


def pytest_collection_modifyitems(items):
    """Enforce TDD Red phase: red-marked tests must xfail strictly."""
    for item in items:
        if item.get_closest_marker("red"):
            item.add_marker(
                pytest.mark.xfail(
                    strict=True,
                    reason="RED: implementation not written yet — this test must fail",
                )
            )


@pytest.fixture
def api_client():
    """DRF API test client."""
    return APIClient()


@pytest.fixture
def tremly(db):
    """
    Lazy factory accessor. Usage:
        def test_foo(tremly):
            agent = tremly.agent()
            tenant = tremly.tenant()
    """
    from apps.test_hub.base.test_case import TremlyAPITestCase
    tc = TremlyAPITestCase()
    tc._pre_setup()  # initialise DB state
    return tc


@pytest.fixture
def admin_user(tremly):
    return tremly.create_admin()


@pytest.fixture
def agent_user(tremly):
    return tremly.create_agent()


@pytest.fixture
def tenant_user(tremly):
    return tremly.create_tenant()


@pytest.fixture
def supplier_user(tremly):
    return tremly.create_supplier_user()


@pytest.fixture
def owner_user(tremly):
    return tremly.create_owner_user()
