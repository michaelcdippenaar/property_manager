"""
Regression tests for ChangePasswordView -- throttle enforcement.

DRF's SimpleRateThrottle.THROTTLE_RATES is a class-level dict frozen at
module-import time.  override_settings(REST_FRAMEWORK=...) updates api_settings
but NOT the class variable.  We patch the class variable directly (same pattern
as test_hub/esigning/unit/test_rate_limits.py) so the tight rate applies
regardless of import order or cross-test interference.

Run:
    cd backend && pytest apps/accounts/tests/test_change_password.py -v
"""
import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/change-password/"

_TIGHT_RATES = {
    "anon_auth": "5/min",
    "otp_send": "3/min",
    "otp_verify": "5/min",
    "login_hourly_user": "20/hour",
    "invite_accept": "5/min",
    "password_change": "3/min",  # tight -- we need to exceed this in the test
    "public_sign_minute": "10/min",
    "public_sign_hourly": "60/hour",
}

_ISOLATED_CACHE = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "change-password-throttle-tests",
    }
}


@pytest.fixture(autouse=True)
def _isolate_throttle(settings):
    """Patch SimpleRateThrottle.THROTTLE_RATES and use an isolated cache."""
    from rest_framework.throttling import SimpleRateThrottle

    original_rates = SimpleRateThrottle.THROTTLE_RATES
    SimpleRateThrottle.THROTTLE_RATES = _TIGHT_RATES
    settings.CACHES = _ISOLATED_CACHE
    cache.clear()
    yield
    SimpleRateThrottle.THROTTLE_RATES = original_rates
    cache.clear()


def _make_user(email, password="TestPass1!", oauth=False):
    user = User.objects.create_user(
        email=email,
        password=password,
        role=User.Role.TENANT,
    )
    if oauth:
        user.set_unusable_password()
        user.save()
    return user


def test_429_after_threshold_exceeded():
    """
    After the rate limit (3/min) is reached, the (N+1)th call returns 429.
    Uses wrong current_password so the auth never succeeds -- we are only
    testing the throttle layer fires.
    """
    user = _make_user("throttle-test@example.com")
    client = APIClient()
    client.force_authenticate(user=user)
    payload = {"current_password": "wrong", "new_password": "Whatever1!"}

    statuses = [
        client.post(URL, payload, format="json").status_code
        for _ in range(3)
    ]

    # First 3 calls must NOT be 429 (throttle allows them through)
    assert all(s != 429 for s in statuses), (
        f"Throttle fired too early -- first 3 responses: {statuses}"
    )

    # 4th call must be throttled
    fourth = client.post(URL, payload, format="json")
    assert fourth.status_code == 429, (
        f"Expected 429 on the 4th call but got {fourth.status_code}: {fourth.data}"
    )


def test_google_oauth_user_not_blocked_within_limit():
    """
    Google-OAuth users (no usable password) can call change-password within
    the throttle window.  Ensures the throttle does not break the OAuth branch.
    """
    oauth_user = _make_user("oauth-throttle@example.com", oauth=True)
    client = APIClient()
    client.force_authenticate(user=oauth_user)

    # One valid call -- OAuth branch skips current_password check
    r = client.post(
        URL,
        {"current_password": "", "new_password": "NewPass1!"},
        format="json",
    )
    # 200 means password changed; must not be throttled or forbidden
    assert r.status_code == 200, (
        f"Expected 200 from OAuth branch but got {r.status_code}: {r.data}"
    )
