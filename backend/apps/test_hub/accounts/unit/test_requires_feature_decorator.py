"""
Unit tests for the @requires_feature decorator (accounts/decorators.py).

Covers:
  - DEBUG=True: ImproperlyConfigured raised when request cannot be resolved
  - DEBUG=False: HTTP 500 returned when request cannot be resolved
  - Feature allowed: view is called through
  - Feature blocked: HTTP 402 returned
  - FBV call convention: first_arg IS the request
  - CBV call convention: first_arg is self, args[0] is request

Run with:
    cd backend && pytest apps/test_hub/accounts/ -k requires_feature
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_drf_request(authenticated=True, feature_allowed=True, feature_slug="some_feature"):
    """
    Build a mock that passes isinstance(obj, DRFRequest) checks by patching
    the decorator's DRFRequest import rather than inheriting from it.
    """
    from rest_framework.request import Request as DRFRequest

    request = MagicMock(spec=DRFRequest)
    user = MagicMock()
    user.is_authenticated = authenticated
    request.user = user
    return request


def _patched_decorator_env(debug: bool):
    """Context manager: patch settings.DEBUG inside the decorator."""
    return patch("django.conf.settings.DEBUG", debug)


def _decorated_view(feature_slug="some_feature"):
    """Return a wrapped sentinel function with the decorator applied."""
    from apps.accounts.decorators import requires_feature

    call_log = []

    @requires_feature(feature_slug)
    def _view(*args, **kwargs):
        call_log.append(("called", args, kwargs))
        return "view_result"

    return _view, call_log


# ---------------------------------------------------------------------------
# Unknown-signature branch (cannot resolve DRF Request)
# ---------------------------------------------------------------------------

class TestUnresolvableRequest:

    @pytest.mark.green
    def test_debug_true_raises_improperly_configured(self):
        """In DEBUG mode, a non-standard signature must raise ImproperlyConfigured."""
        from django.core.exceptions import ImproperlyConfigured
        from apps.accounts.decorators import requires_feature

        @requires_feature("some_feature")
        def weird_view(not_a_request, also_not_a_request):
            return "should never reach here"

        with _patched_decorator_env(True):
            with pytest.raises(ImproperlyConfigured, match="requires_feature"):
                weird_view("plain_string", "another_plain_string")

    @pytest.mark.green
    def test_debug_false_returns_http_500(self):
        """In production mode, a non-standard signature must return HTTP 500."""
        from apps.accounts.decorators import requires_feature

        @requires_feature("some_feature")
        def weird_view(not_a_request, also_not_a_request):
            return "should never reach here"

        with _patched_decorator_env(False):
            response = weird_view("plain_string", "another_plain_string")

        assert response.status_code == 500

    @pytest.mark.green
    def test_debug_false_does_not_silently_grant_access(self):
        """
        The critical gate: when request cannot be resolved, the underlying
        view function MUST NOT be executed (no silent pass-through).
        """
        from apps.accounts.decorators import requires_feature

        reached = []

        @requires_feature("some_feature")
        def should_not_run(not_a_request):
            reached.append(True)
            return "oops"

        with _patched_decorator_env(False):
            should_not_run("not_a_drf_request")

        assert reached == [], "View was executed despite unresolvable request — silent grant!"

    @pytest.mark.green
    def test_debug_true_does_not_silently_grant_access(self):
        """Same gate for DEBUG=True path — must raise, not call through."""
        from django.core.exceptions import ImproperlyConfigured
        from apps.accounts.decorators import requires_feature

        reached = []

        @requires_feature("some_feature")
        def should_not_run(not_a_request):
            reached.append(True)
            return "oops"

        with _patched_decorator_env(True):
            with pytest.raises(ImproperlyConfigured):
                should_not_run("not_a_drf_request")

        assert reached == [], "View was executed despite unresolvable request — silent grant!"


# ---------------------------------------------------------------------------
# FBV convention: first_arg IS the DRF Request
# ---------------------------------------------------------------------------

class TestFBVConvention:

    @pytest.mark.green
    def test_feature_allowed_calls_view(self):
        """FBV: when feature is allowed, the view function is called and returns its value."""
        from rest_framework.request import Request as DRFRequest
        from apps.accounts.decorators import requires_feature

        call_log = []

        @requires_feature("some_feature")
        def my_fbv(request):
            call_log.append("called")
            return "ok"

        mock_request = MagicMock(spec=DRFRequest)
        mock_request.user.is_authenticated = True

        with patch("apps.accounts.models.Agency.for_user") as mock_for_user, \
             patch("apps.accounts.tier_service.TierService") as MockTierService:
            mock_svc = MagicMock()
            mock_svc.has_feature.return_value = True
            MockTierService.return_value = mock_svc
            mock_for_user.return_value = MagicMock()

            result = my_fbv(mock_request)

        assert call_log == ["called"]
        assert result == "ok"

    @pytest.mark.green
    def test_feature_blocked_returns_402(self):
        """FBV: when feature is NOT on the tier, HTTP 402 is returned."""
        from rest_framework.request import Request as DRFRequest
        from apps.accounts.decorators import requires_feature

        @requires_feature("ai_lease_generation")
        def my_fbv(request):
            return "should not reach"

        mock_request = MagicMock(spec=DRFRequest)
        mock_request.user.is_authenticated = True

        with patch("apps.accounts.models.Agency.for_user") as mock_for_user, \
             patch("apps.accounts.tier_service.TierService") as MockTierService:
            mock_svc = MagicMock()
            mock_svc.has_feature.return_value = False
            MockTierService.return_value = mock_svc
            mock_for_user.return_value = MagicMock()

            response = my_fbv(mock_request)

        assert response.status_code == 402
        assert response.data["feature"] == "ai_lease_generation"
        assert response.data["upgrade_required"] is True


# ---------------------------------------------------------------------------
# CBV convention: first_arg is self, args[0] is the DRF Request
# ---------------------------------------------------------------------------

class TestCBVConvention:

    @pytest.mark.green
    def test_feature_allowed_calls_view(self):
        """CBV: when feature is allowed, the view method is called through."""
        from rest_framework.request import Request as DRFRequest
        from apps.accounts.decorators import requires_feature

        call_log = []

        class FakeView:
            @requires_feature("some_feature")
            def get(self, request):
                call_log.append("called")
                return "ok"

        view = FakeView()
        mock_request = MagicMock(spec=DRFRequest)
        mock_request.user.is_authenticated = True

        with patch("apps.accounts.models.Agency.for_user") as mock_for_user, \
             patch("apps.accounts.tier_service.TierService") as MockTierService:
            mock_svc = MagicMock()
            mock_svc.has_feature.return_value = True
            MockTierService.return_value = mock_svc
            mock_for_user.return_value = MagicMock()

            result = view.get(mock_request)

        assert call_log == ["called"]
        assert result == "ok"

    @pytest.mark.green
    def test_feature_blocked_returns_402(self):
        """CBV: when feature is NOT on the tier, HTTP 402 is returned."""
        from rest_framework.request import Request as DRFRequest
        from apps.accounts.decorators import requires_feature

        class FakeView:
            @requires_feature("premium_only")
            def post(self, request):
                return "should not reach"

        view = FakeView()
        mock_request = MagicMock(spec=DRFRequest)
        mock_request.user.is_authenticated = True

        with patch("apps.accounts.models.Agency.for_user") as mock_for_user, \
             patch("apps.accounts.tier_service.TierService") as MockTierService:
            mock_svc = MagicMock()
            mock_svc.has_feature.return_value = False
            MockTierService.return_value = mock_svc
            mock_for_user.return_value = MagicMock()

            response = view.post(mock_request)

        assert response.status_code == 402

    @pytest.mark.green
    def test_cbv_unexpected_args_without_request_raises_or_500(self):
        """
        CBV-style call where neither self nor args[0] is a DRF Request:
        must not silently pass through to the view body.
        """
        from django.core.exceptions import ImproperlyConfigured
        from apps.accounts.decorators import requires_feature

        reached = []

        class WeirdView:
            @requires_feature("some_feature")
            def action(self, not_a_request):
                reached.append(True)
                return "bad"

        view = WeirdView()

        with _patched_decorator_env(False):
            response = view.action("some_string")
        assert response.status_code == 500
        assert reached == []

        with _patched_decorator_env(True):
            with pytest.raises(ImproperlyConfigured):
                view.action("some_string")
        assert reached == []
