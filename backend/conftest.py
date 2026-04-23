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


@pytest.fixture(autouse=True)
def _reset_drf_throttle_cache():
    """
    DRF throttles use Django's default cache backend (locmem in tests) and share
    state across test cases. Without resetting, earlier register/login/Google tests
    poison later tests with 429s. Clear the cache before each test runs.

    Additionally, DRF's SimpleRateThrottle.THROTTLE_RATES is a class-level
    variable that is set at module import time from api_settings. If the module
    is imported outside an @override_settings context, the variable is frozen
    at the base settings for the lifetime of the process. This fixture saves and
    restores the class variable around every test so that any test which patches
    THROTTLE_RATES (e.g. TestPublicSignMinuteThrottle._isolate_throttle_cache)
    cannot bleed its patched value into subsequent tests.

    Tests that intentionally exercise throttle behaviour (account lockout, rate
    limits) layer their own fixtures on top of this baseline reset.
    """
    from django.core.cache import cache
    from rest_framework.throttling import SimpleRateThrottle

    # Snapshot the class variable before the test runs.
    _original_rates = SimpleRateThrottle.THROTTLE_RATES

    cache.clear()
    yield
    cache.clear()

    # Restore so any monkeypatching done inside the test does not bleed out.
    SimpleRateThrottle.THROTTLE_RATES = _original_rates


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
