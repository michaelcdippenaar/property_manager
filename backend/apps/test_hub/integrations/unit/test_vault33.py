"""
Unit tests for apps.integrations.vault33 bridge.

Tests the _client() configuration guard and fetch helpers without
actually hitting Vault33. We never make real external calls in unit tests.
"""
import pytest
from unittest.mock import MagicMock, patch

pytestmark = [pytest.mark.unit, pytest.mark.green]


class TestVault33ClientConfigGuard:
    def test_raises_when_base_url_not_configured(self):
        """_client() raises RuntimeError when VAULT33_BASE_URL is empty."""
        from apps.integrations.vault33 import _client
        with patch("apps.integrations.vault33.settings") as mock_settings:
            mock_settings.VAULT33_BASE_URL = ""
            mock_settings.VAULT33_INTERNAL_TOKEN = "token"
            with pytest.raises(RuntimeError, match="VAULT33_BASE_URL"):
                _client()

    def test_raises_when_token_not_configured(self):
        """_client() raises RuntimeError when VAULT33_INTERNAL_TOKEN is empty."""
        from apps.integrations.vault33 import _client
        with patch("apps.integrations.vault33.settings") as mock_settings:
            mock_settings.VAULT33_BASE_URL = "https://vault33.example.com"
            mock_settings.VAULT33_INTERNAL_TOKEN = ""
            with pytest.raises(RuntimeError, match="VAULT33_INTERNAL_TOKEN"):
                _client()

    def test_raises_when_both_missing(self):
        from apps.integrations.vault33 import _client
        with patch("apps.integrations.vault33.settings") as mock_settings:
            mock_settings.VAULT33_BASE_URL = ""
            mock_settings.VAULT33_INTERNAL_TOKEN = ""
            with pytest.raises(RuntimeError):
                _client()
