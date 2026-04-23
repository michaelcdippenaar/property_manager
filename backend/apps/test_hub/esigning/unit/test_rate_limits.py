"""
Rate-limit tests for public e-signing endpoints.

Verifies that the DRF throttle classes applied to public (AllowAny) signing
views return HTTP 429 after the configured threshold is exceeded.

These tests manipulate the DRF throttle cache directly so they do NOT require
a live Redis or Memcached — the root conftest clears the cache before each
test, giving each test a clean slate.

--- Cache isolation note ---

DRF's SimpleRateThrottle stores request history in Django's default cache using
a key derived from the throttle scope + client IP.  When the full test suite is
run, other tests that call the same public endpoints can leave counters in the
cache; the _isolate_throttle_cache fixture prevents this by pointing the default
cache at a uniquely-named LocMemCache location ("throttle-tests") that nothing
else writes to.

--- THROTTLE_RATES class-variable note ---

DRF sets SimpleRateThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES
at **class definition time** (i.e., when rest_framework.throttling is first
imported).  Django's setting_changed signal only reloads api_settings — it does
NOT update the class variable.  If throttling.py is first imported by an earlier
test (outside any @override_settings context), THROTTLE_RATES will contain the
initial base settings (10/min for public_sign_minute) for the rest of the
process, causing these throttle tests to silently use 10/min instead of the
intended 3/min.

The _isolate_throttle_cache fixture also patches SimpleRateThrottle.THROTTLE_RATES
directly for the duration of each test in this class, ensuring the tight rates
apply regardless of import order or cross-test interference.
"""
import pytest
from unittest.mock import MagicMock, patch
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient


pytestmark = pytest.mark.unit


TIGHT_THROTTLE_SETTINGS = {
    "DEFAULT_THROTTLE_RATES": {
        "anon_auth": "5/min",
        "otp_send": "3/min",
        "otp_verify": "5/min",
        "login_hourly_user": "20/hour",
        "invite_accept": "5/min",
        # Drop to 3/min so we can hit the limit cheaply in tests
        "public_sign_minute": "3/min",
        "public_sign_hourly": "60/hour",
    }
}

# Isolated LocMemCache location used only by TestPublicSignMinuteThrottle.
# Django's LocMemCache uses the LOCATION string as the key into a module-level
# dict, so a unique name here means no other test class can pollute this bucket.
_THROTTLE_TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "throttle-tests",
    }
}


class TestPublicSignMinuteThrottle:
    """PublicSignMinuteThrottle — 10 req/min per IP (3 in tight test settings)."""

    @pytest.fixture(autouse=True)
    def _isolate_throttle_cache(self, settings):
        """
        Two-part isolation fixture for throttle tests:

        1. CACHE ISOLATION — Override CACHES to a uniquely-named LocMemCache so
           that no other test class can pollute the throttle counter bucket.
           pytest-django's `settings` fixture emits `setting_changed` on each
           assignment, which triggers Django's built-in handler that calls
           close_caches() and resets the CacheHandler thread-local — so
           `django.core.cache.cache` automatically points to "throttle-tests"
           for the duration of the test and is fully restored afterwards.

        2. THROTTLE_RATES PATCH — DRF's SimpleRateThrottle.THROTTLE_RATES is a
           class-level variable set at module import time. If the module is first
           imported by an earlier test (outside any @override_settings context),
           the class variable is frozen at the base settings (10/min for
           public_sign_minute). The @override_settings(REST_FRAMEWORK=...) on
           individual test methods correctly updates api_settings, but does NOT
           update the already-frozen class variable. This fixture patches the
           class variable directly so that the tight rates (3/min) are always
           used regardless of import order.
        """
        from rest_framework.throttling import SimpleRateThrottle

        # Part 1: isolated cache backend
        settings.CACHES = _THROTTLE_TEST_CACHES

        # Part 2: patch THROTTLE_RATES class variable with tight test rates
        original_rates = SimpleRateThrottle.THROTTLE_RATES
        SimpleRateThrottle.THROTTLE_RATES = TIGHT_THROTTLE_SETTINGS["DEFAULT_THROTTLE_RATES"]
        yield
        SimpleRateThrottle.THROTTLE_RATES = original_rates

    def test_throttle_class_scope(self):
        from apps.esigning.throttles import PublicSignMinuteThrottle
        assert PublicSignMinuteThrottle.scope == "public_sign_minute"

    def test_throttle_class_scope_hourly(self):
        from apps.esigning.throttles import PublicSignHourlyThrottle
        assert PublicSignHourlyThrottle.scope == "public_sign_hourly"

    @override_settings(
        REST_FRAMEWORK={
            **TIGHT_THROTTLE_SETTINGS,
            "DEFAULT_AUTHENTICATION_CLASSES": [],
        }
    )
    def test_429_after_threshold_exceeded(self, db):
        """
        POST to the public submit endpoint 4 times with the same IP; the 4th
        request should receive 429.

        We use a non-existent link UUID so every call gets 404 from the
        business logic — we are only testing the throttle layer fires.
        """
        import uuid
        from django.core.cache import cache

        cache.clear()  # ensure clean state even if conftest already cleared

        client = APIClient()
        # Force a deterministic REMOTE_ADDR so all requests share one bucket
        link_id = uuid.uuid4()
        url = f"/api/v1/esigning/public-sign/{link_id}/sign/"

        responses = []
        for _ in range(4):
            resp = client.post(url, data={}, format="json", REMOTE_ADDR="10.0.0.1")
            responses.append(resp.status_code)

        # First 3 should be blocked by the business layer (404/410/400), not throttle
        assert all(r != 429 for r in responses[:3]), (
            f"Expected non-429 for first 3 requests, got {responses[:3]}"
        )
        # 4th request (exceeds 3/min limit) should be 429
        assert responses[3] == 429, (
            f"Expected 429 on the 4th request, got {responses[3]}"
        )

    @override_settings(
        REST_FRAMEWORK={
            **TIGHT_THROTTLE_SETTINGS,
            "DEFAULT_AUTHENTICATION_CLASSES": [],
        }
    )
    def test_different_ips_not_throttled_together(self, db):
        """
        Each IP has its own throttle bucket — IP-B should not be throttled
        because IP-A exhausted its own bucket.
        """
        import uuid
        from django.core.cache import cache

        cache.clear()

        client = APIClient()
        link_id = uuid.uuid4()
        url = f"/api/v1/esigning/public-sign/{link_id}/sign/"

        # Exhaust IP-A's bucket
        for _ in range(3):
            client.post(url, data={}, format="json", REMOTE_ADDR="10.0.0.2")

        # IP-A should be throttled now
        resp_a = client.post(url, data={}, format="json", REMOTE_ADDR="10.0.0.2")
        assert resp_a.status_code == 429

        # IP-B should still be allowed through (gets 404/other, not 429)
        resp_b = client.post(url, data={}, format="json", REMOTE_ADDR="10.0.0.3")
        assert resp_b.status_code != 429


class TestInviteAcceptThrottle:
    """InviteAcceptThrottle — 5 req/min per IP."""

    def test_throttle_class_scope(self):
        from apps.accounts.throttles import InviteAcceptThrottle
        assert InviteAcceptThrottle.scope == "invite_accept"

    def test_accept_invite_view_uses_invite_throttle(self):
        """AcceptInviteView must declare InviteAcceptThrottle, not AuthAnonThrottle."""
        from apps.accounts.views import AcceptInviteView
        from apps.accounts.throttles import InviteAcceptThrottle, AuthAnonThrottle

        throttle_classes = AcceptInviteView.throttle_classes
        throttle_types = [type(t) if not isinstance(t, type) else t for t in throttle_classes]
        assert InviteAcceptThrottle in throttle_classes, (
            "AcceptInviteView must include InviteAcceptThrottle"
        )
        assert AuthAnonThrottle not in throttle_classes, (
            "AcceptInviteView should NOT use AuthAnonThrottle (uses InviteAcceptThrottle instead)"
        )


class TestLoginHourlyThrottle:
    """LoginHourlyThrottle — 20/hr per user (email)."""

    def test_throttle_class_scope(self):
        from apps.accounts.throttles import LoginHourlyThrottle
        assert LoginHourlyThrottle.scope == "login_hourly_user"

    def test_login_view_includes_hourly_throttle(self):
        from apps.accounts.views import LoginView
        from apps.accounts.throttles import LoginHourlyThrottle, AuthAnonThrottle

        throttle_classes = LoginView.throttle_classes
        assert AuthAnonThrottle in throttle_classes
        assert LoginHourlyThrottle in throttle_classes

    def test_get_cache_key_uses_email(self):
        """LoginHourlyThrottle.get_cache_key() returns a key containing the email."""
        from apps.accounts.throttles import LoginHourlyThrottle

        throttle = LoginHourlyThrottle()
        throttle.scope = "login_hourly_user"
        throttle.cache_format = "throttle_%(scope)s_%(ident)s"

        request = MagicMock()
        request.data = {"email": "agent@example.co.za"}
        key = throttle.get_cache_key(request, view=None)
        assert key is not None
        assert "agent@example.co.za" in key

    def test_get_cache_key_returns_none_without_email(self):
        """No cache key means no per-user limit when email is absent."""
        from apps.accounts.throttles import LoginHourlyThrottle

        throttle = LoginHourlyThrottle()
        throttle.scope = "login_hourly_user"
        throttle.cache_format = "throttle_%(scope)s_%(ident)s"

        request = MagicMock()
        request.data = {}
        key = throttle.get_cache_key(request, view=None)
        assert key is None


class TestPublicSignViewThrottleDeclarations:
    """All public signing views must declare both throttle classes."""

    def _assert_has_public_sign_throttles(self, view_class):
        from apps.esigning.throttles import PublicSignMinuteThrottle, PublicSignHourlyThrottle
        classes = view_class.throttle_classes
        assert PublicSignMinuteThrottle in classes, (
            f"{view_class.__name__} missing PublicSignMinuteThrottle"
        )
        assert PublicSignHourlyThrottle in classes, (
            f"{view_class.__name__} missing PublicSignHourlyThrottle"
        )

    def test_public_sign_detail_view(self):
        from apps.esigning.views import ESigningPublicSignDetailView
        self._assert_has_public_sign_throttles(ESigningPublicSignDetailView)

    def test_public_document_view(self):
        from apps.esigning.views import ESigningPublicDocumentView
        self._assert_has_public_sign_throttles(ESigningPublicDocumentView)

    def test_public_submit_signature_view(self):
        from apps.esigning.views import ESigningPublicSubmitSignatureView
        self._assert_has_public_sign_throttles(ESigningPublicSubmitSignatureView)

    def test_public_draft_view(self):
        from apps.esigning.views import ESigningPublicDraftView
        self._assert_has_public_sign_throttles(ESigningPublicDraftView)

    def test_public_documents_view(self):
        from apps.esigning.views import ESigningPublicDocumentsView
        self._assert_has_public_sign_throttles(ESigningPublicDocumentsView)

    def test_public_document_delete_view(self):
        from apps.esigning.views import ESigningPublicDocumentDeleteView
        self._assert_has_public_sign_throttles(ESigningPublicDocumentDeleteView)


class TestThrottleRateConfiguration:
    """Verify all required scopes exist in DEFAULT_THROTTLE_RATES."""

    def test_required_scopes_in_settings(self):
        from django.conf import settings
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        required = [
            "anon_auth",
            "otp_send",
            "otp_verify",
            "login_hourly_user",
            "invite_accept",
            "public_sign_minute",
            "public_sign_hourly",
        ]
        for scope in required:
            assert scope in rates, f"Missing throttle scope '{scope}' in DEFAULT_THROTTLE_RATES"
