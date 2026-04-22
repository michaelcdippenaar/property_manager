"""
Unit tests for webhook signature validation in the esigning app.

Tests cover HMAC validation, static header validation, and missing signatures.
"""
import hashlib
import hmac
import json
import pytest
from unittest.mock import MagicMock, patch

pytestmark = pytest.mark.unit


def _make_body(payload: dict) -> bytes:
    return json.dumps(payload).encode()


class TestWebhookHmacValidation:
    """HMAC signature verification for esigning webhooks."""

    @pytest.mark.green
    def test_valid_hmac_signature_accepted(self):
        """A request with a correct HMAC signature should be accepted."""
        from apps.esigning.webhooks import _verify_signature

        secret = "my-webhook-secret"
        body = _make_body({"event_type": "form.viewed", "data": {"id": "123"}})
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        with patch("apps.esigning.webhooks.settings") as mock_settings:
            mock_settings.WEBHOOK_SECRET_ESIGNING = secret
            mock_settings.WEBHOOK_HEADER_ESIGNING = ""
            result = _verify_signature(body, sig)

        assert result is True

    @pytest.mark.green
    def test_invalid_hmac_signature_rejected(self):
        """A request with a wrong HMAC signature should be rejected."""
        from apps.esigning.webhooks import _verify_signature

        secret = "my-webhook-secret"
        body = _make_body({"event_type": "form.viewed", "data": {"id": "123"}})

        with patch("apps.esigning.webhooks.settings") as mock_settings:
            mock_settings.WEBHOOK_SECRET_ESIGNING = secret
            mock_settings.WEBHOOK_HEADER_ESIGNING = ""
            result = _verify_signature(body, "bad-signature-value")

        assert result is False

    @pytest.mark.green
    def test_missing_signature_with_secret_rejected(self):
        """A request with no signature header, when secret is configured, should be rejected."""
        from apps.esigning.webhooks import _verify_signature

        body = _make_body({"event_type": "form.viewed", "data": {}})

        with patch("apps.esigning.webhooks.settings") as mock_settings:
            mock_settings.WEBHOOK_SECRET_ESIGNING = "configured-secret"
            mock_settings.WEBHOOK_HEADER_ESIGNING = ""
            result = _verify_signature(body, "")

        assert result is False

    @pytest.mark.green
    def test_no_secret_configured_allows_all(self):
        """When WEBHOOK_SECRET_ESIGNING is empty, signature check is skipped."""
        from apps.esigning.webhooks import _verify_signature

        body = _make_body({"event_type": "form.viewed", "data": {}})

        with patch("apps.esigning.webhooks.settings") as mock_settings:
            mock_settings.WEBHOOK_SECRET_ESIGNING = ""
            mock_settings.WEBHOOK_HEADER_ESIGNING = ""
            result = _verify_signature(body, "any-value-or-empty")

        assert result is True


class TestWebhookStaticHeaderValidation:
    """Static header token validation (alternative to HMAC)."""

    @pytest.mark.green
    def test_correct_static_token_accepted(self):
        """When WEBHOOK_HEADER_ESIGNING is set, matching token is accepted."""
        from apps.esigning.webhooks import _verify_signature

        body = _make_body({"event_type": "form.viewed", "data": {}})

        with patch("apps.esigning.webhooks.settings") as mock_settings:
            mock_settings.WEBHOOK_SECRET_ESIGNING = "my-static-token"
            mock_settings.WEBHOOK_HEADER_ESIGNING = "X-Tremly-Token"
            result = _verify_signature(body, "my-static-token")

        assert result is True

    @pytest.mark.green
    def test_wrong_static_token_rejected(self):
        """When WEBHOOK_HEADER_ESIGNING is set, wrong token is rejected."""
        from apps.esigning.webhooks import _verify_signature

        body = _make_body({"event_type": "form.viewed", "data": {}})

        with patch("apps.esigning.webhooks.settings") as mock_settings:
            mock_settings.WEBHOOK_SECRET_ESIGNING = "correct-token"
            mock_settings.WEBHOOK_HEADER_ESIGNING = "X-Tremly-Token"
            result = _verify_signature(body, "wrong-token")

        assert result is False

    @pytest.mark.green
    def test_verify_signature_function_exists(self):
        """_verify_signature() exists in webhooks module and is importable."""
        from apps.esigning.webhooks import _verify_signature

        assert callable(_verify_signature)


class TestWebhookEndpointSignatureEnforcement:
    """Integration-style tests for the webhook endpoint signature enforcement.

    These use Django's test client via a mocked request and test the view directly.
    """

    @pytest.mark.red
    def test_webhook_view_rejects_bad_hmac(self):
        """RED: The webhook view should return 400 for an invalid HMAC signature.

        Marked red: requires Django test client setup (not available in pure unit tests).
        See apps/test_hub/esigning/integration/test_esigning.py for full coverage.
        """
        raise NotImplementedError(
            "See WebhookSecurityTests in integration/test_esigning.py "
            "and integration/test_esigning_full.py for full webhook security tests."
        )
