"""Fixtures specific to the accounts test module."""
import pytest


@pytest.fixture
def otp_user(tremly):
    """A tenant user with a pending OTP code."""
    user = tremly.create_tenant()
    from apps.accounts.models import OTPCode
    otp = OTPCode.objects.create(user=user, code="123456")
    return user, otp
