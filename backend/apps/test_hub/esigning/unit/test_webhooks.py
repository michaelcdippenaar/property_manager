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
    """HMAC signature verification for DocuSeal webhooks."""

    @pytest.mark.red
    def test_valid_hmac_signature_accepted(self):
        """A request with a correct HMAC signature should be accepted."""
        from apps.esigning.webhooks import _verify_signature

        secret = "my-webhook-secret"
        body = _make_body({"event_type": "form.viewed", "data": {"id": "123"}})
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        with patch("apps.esigning.webhooks.settings") as mock_settings:
            mock_settings.DOCUSEAL_WEBHOOK_SECRET = secret
            mock_settings.DOCUSEAL_WEBHOOK_HEADER_NAME = ""
            result = _verify_signature(body, sig)

        assert result is True

    @pytest.mark.red
    def test_invalid_hmac_signature_rejected(self):
        """A request with a wrong HMAC signature should be rejected."""
        from apps.esigning.webhooks import _verify_signature

        secret = "my-webhook-secret"
        body = _make_body({"event_type": "form.viewed", "data": {"id": "123"}})

        with patch("apps.esigning.webhooks.settings") as mock_settings:
            mock_settings.DOCUSEAL_WEBHOOK_SECRET = secret
            mock_settings.DOCUSEAL_WEBHOOK_HEADER_NAME = ""
            result = _verify_signature(body, "bad-signature-value")

        assert result is False

    @pytest.mark.red
    def test_missing_signature_with_secret_rejected(self):
        """A request with no signature header, when secret is configured, should be rejected."""
        from apps.esigning.webhooks import _verify_signature

        body = _make_body({"event_type": "form.viewed", "data": {}})

        with patch("apps.esigning.webhooks.settings") as mock_settings:
            mock_settings.DOCUSEAL_WEBHOOK_SECRET = "configured-secret"
            mock_settings.DOCUSEAL_WEBHOOK_HEADER_NAME = ""
            result = _verify_signature(body, "")

        assert result is False

    @pytest.mark.red
    def test_no_secret_configured_allows_all(self):
        """When DOCUSEAL_WEBHOOK_SECRET is empty, signature check is skipped."""
        from apps.esigning.webhooks import _verify_signature

        body = _make_body({"event_type": "form.viewed", "data": {}})

        with patch("apps.esigning.webhooks.settings") as mock_settings:
            mock_settings.DOCUSEAL_WEBHOOK_SECRET = ""
            mock_settings.DOCUSEAL_WEBHOOK_HEADER_NAME = ""
            result = _verify_signature(body, "any-value-or-empty")

        assert result is True


class TestWebhookStaticHeaderValidation:
    """Static header token validation (alternative to HMAC)."""

    @pytest.mark.red
    def test_correct_static_token_accepted(self):
        """When DOCUSEAL_WEBHOOK_HEADER_NAME is set, matching token is accepted."""
        from apps.esigning.webhooks import _verify_signature

        body = _make_body({"event_type": "form.viewed", "data": {}})

        with patch("apps.esigning.webhooks.settings") as mock_settings:
            mock_settings.DOCUSEAL_WEBHOOK_SECRET = "my-static-token"
            mock_settings.DOCUSEAL_WEBHOOK_HEADER_NAME = "X-Tremly-Token"
            result = _verify_signature(body, "my-static-token")

        assert result is True

    @pytest.mark.red
    def test_wrong_static_token_rejected(self):
        """When DOCUSEAL_WEBHOOK_HEADER_NAME is set, wrong token is rejected."""
        from apps.esigning.webhooks import _verify_signature

        body = _make_body({"event_type": "form.viewed", "data": {}})

        with patch("apps.esigning.webhooks.settings") as mock_settings:
            mock_settings.DOCUSEAL_WEBHOOK_SECRET = "correct-token"
            mock_settings.DOCUSEAL_WEBHOOK_HEADER_NAME = "X-Tremly-Token"
            result = _verify_signature(body, "wrong-token")

        assert result is False

    @pytest.mark.red
    def test_verify_signature_function_exists(self):
        """RED: Verify that _verify_signature() exists in webhooks module.

        This test is marked red because the private function name/signature
        should be confirmed against the actual webhooks.py implementation.
        The function may be named differently or inline in the view.
        """
        try:
            from apps.esigning.webhooks import _verify_signature
        except ImportError:
            raise NotImplementedError(
                "_verify_signature not found in apps.esigning.webhooks. "
                "Locate the actual signature verification function and update import."
            )


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
