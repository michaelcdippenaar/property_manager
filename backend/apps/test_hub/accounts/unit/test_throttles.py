"""
Unit tests for the custom auth throttle classes.

Source file under test: apps/accounts/throttles.py

The throttle classes themselves are trivial wrappers around
``AnonRateThrottle`` — the value lies in pinning the ``scope`` names so that a
future rename of a DRF throttle rate (``DEFAULT_THROTTLE_RATES["anon_auth"]``
etc.) is caught immediately by a failing unit test rather than silently
disabling rate limiting in production.
"""
import pytest
from rest_framework.throttling import AnonRateThrottle

from apps.accounts.throttles import (
    AuthAnonThrottle,
    OTPSendThrottle,
    OTPVerifyThrottle,
)

pytestmark = [pytest.mark.unit, pytest.mark.green]


class TestThrottleScopes:
    """The three auth throttles must expose stable scope strings.

    These scopes are referenced by ``settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]``
    — renaming one without updating settings would silently turn the throttle
    into a no-op.
    """

    def test_auth_anon_throttle_scope(self):
        assert AuthAnonThrottle.scope == "anon_auth"

    def test_otp_send_throttle_scope(self):
        assert OTPSendThrottle.scope == "otp_send"

    def test_otp_verify_throttle_scope(self):
        assert OTPVerifyThrottle.scope == "otp_verify"

    def test_all_throttles_inherit_anon_rate_throttle(self):
        """They must stay anonymous-scoped — if one gets switched to
        UserRateThrottle by accident, unauthenticated brute-force traffic
        becomes unlimited."""
        assert issubclass(AuthAnonThrottle, AnonRateThrottle)
        assert issubclass(OTPSendThrottle, AnonRateThrottle)
        assert issubclass(OTPVerifyThrottle, AnonRateThrottle)

    def test_scopes_are_unique(self):
        """Each throttle must map to a distinct rate bucket."""
        scopes = {
            AuthAnonThrottle.scope,
            OTPSendThrottle.scope,
            OTPVerifyThrottle.scope,
        }
        assert len(scopes) == 3


class TestThrottleRateConfiguration:
    """The DRF settings must define a rate for every throttle scope we ship.

    If this test fails, it means a throttle is effectively a no-op because
    ``get_rate`` would return ``None`` and skip the throttle check.
    """

    def test_auth_anon_throttle_has_configured_rate(self):
        t = AuthAnonThrottle()
        assert t.get_rate() is not None, (
            "anon_auth rate not configured in DEFAULT_THROTTLE_RATES — "
            "register/login/OAuth endpoints are effectively unthrottled"
        )

    def test_otp_send_throttle_has_configured_rate(self):
        t = OTPSendThrottle()
        assert t.get_rate() is not None, (
            "otp_send rate not configured in DEFAULT_THROTTLE_RATES — "
            "OTP send endpoint is effectively unthrottled (SMS abuse risk)"
        )

    def test_otp_verify_throttle_has_configured_rate(self):
        t = OTPVerifyThrottle()
        assert t.get_rate() is not None, (
            "otp_verify rate not configured in DEFAULT_THROTTLE_RATES — "
            "OTP verify endpoint is effectively unthrottled (brute force risk)"
        )
