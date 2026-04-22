"""
DRF throttle classes for public e-signing endpoints.

Public signing surfaces (no auth, just a UUID token in the URL) need two
tiers of limiting to resist both rapid-fire brute-force probing of token
UUIDs and slow-drip DoS attacks:

  PublicSignMinuteThrottle  — 10 requests / minute  / IP
  PublicSignHourlyThrottle  — 60 requests / hour    / IP

Apply both to every AllowAny e-signing view so the request is charged
against each bucket independently.
"""
import logging

from rest_framework.throttling import AnonRateThrottle

logger = logging.getLogger(__name__)


class PublicSignMinuteThrottle(AnonRateThrottle):
    """10 requests per minute per IP for public signing endpoints."""
    scope = "public_sign_minute"


class PublicSignHourlyThrottle(AnonRateThrottle):
    """60 requests per hour per IP for public signing endpoints."""
    scope = "public_sign_hourly"
