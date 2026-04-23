"""
SMS delivery channel stub for OTP codes.

WinSMS / Panacea integration is pending commercial onboarding.
This stub is interface-compatible with Channel so callers need no
changes once the real provider is wired in.
"""
from typing import Any

from apps.accounts.otp.channels.base import Channel


class SMSChannel(Channel):
    """SMS OTP channel — stub pending WinSMS/Panacea integration."""

    def send(self, recipient: str, code: str, context: dict[str, Any]) -> None:
        raise NotImplementedError("SMS channel pending WinSMS/Panacea integration")
