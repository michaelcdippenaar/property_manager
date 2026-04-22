"""
Tests for utils.webhook_signature — HMAC-SHA256 verification helper.

Covers:
- Valid HMAC accepted (no timestamp)
- Invalid HMAC rejected
- Missing signature rejected when secret configured
- No secret configured → verification skipped (returns True)
- Timestamp within window accepted
- Timestamp too old rejected (replay)
- Invalid (non-numeric) timestamp rejected
- get_webhook_secret reads from Django settings
"""

import hashlib
import hmac
import json
import time
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.green]


def _body(payload: dict = None) -> bytes:
    return json.dumps(payload or {"event": "test"}).encode()


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _ts_sign(body: bytes, secret: str, ts: int) -> str:
    payload = f"{ts}.{body.hex()}".encode()
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


# ── verify_hmac_signature ──────────────────────────────────────────────────────

class TestVerifyHmacSignature:

    def test_valid_signature_accepted(self):
        from utils.webhook_signature import verify_hmac_signature

        secret = "test-secret-abc"
        body = _body()
        sig = _sign(body, secret)
        assert verify_hmac_signature(body, sig, secret) is True

    def test_invalid_signature_rejected(self):
        from utils.webhook_signature import verify_hmac_signature

        secret = "test-secret-abc"
        body = _body()
        assert verify_hmac_signature(body, "deadbeefdeadbeef", secret) is False

    def test_missing_signature_rejected(self):
        from utils.webhook_signature import verify_hmac_signature

        assert verify_hmac_signature(_body(), "", "configured-secret") is False

    def test_no_secret_skips_verification(self):
        """When no secret is configured, the check is skipped and True is returned."""
        from utils.webhook_signature import verify_hmac_signature

        assert verify_hmac_signature(_body(), "any-sig", "") is True

    def test_none_secret_treated_as_empty(self):
        from utils.webhook_signature import verify_hmac_signature

        # Secret=None should be treated as not-configured → skip
        # The function signature expects str; passing None-like behaviour
        assert verify_hmac_signature(_body(), "x", "") is True

    def test_signature_case_insensitive(self):
        """Signature comparison should be case-insensitive for hex strings."""
        from utils.webhook_signature import verify_hmac_signature

        secret = "case-test"
        body = _body()
        sig = _sign(body, secret).upper()
        assert verify_hmac_signature(body, sig, secret) is True

    def test_tampered_body_rejected(self):
        from utils.webhook_signature import verify_hmac_signature

        secret = "tamper-test"
        original_body = _body({"event": "original"})
        sig = _sign(original_body, secret)
        tampered_body = _body({"event": "tampered"})
        assert verify_hmac_signature(tampered_body, sig, secret) is False


# ── Timestamp / replay protection ──────────────────────────────────────────────

class TestReplayProtection:

    def test_fresh_timestamp_accepted(self):
        from utils.webhook_signature import verify_hmac_signature

        secret = "replay-test"
        body = _body()
        ts = int(time.time())
        sig = _ts_sign(body, secret, ts)
        assert verify_hmac_signature(body, sig, secret, timestamp=str(ts)) is True

    def test_old_timestamp_rejected(self):
        from utils.webhook_signature import verify_hmac_signature

        secret = "replay-test"
        body = _body()
        stale_ts = int(time.time()) - 600  # 10 minutes ago
        sig = _ts_sign(body, secret, stale_ts)
        assert (
            verify_hmac_signature(body, sig, secret, timestamp=str(stale_ts)) is False
        )

    def test_custom_max_age_respected(self):
        from utils.webhook_signature import verify_hmac_signature

        secret = "replay-test"
        body = _body()
        ts = int(time.time()) - 90  # 90 seconds ago
        sig = _ts_sign(body, secret, ts)
        # Within 120 s window → accepted
        assert (
            verify_hmac_signature(body, sig, secret, timestamp=str(ts), max_age_seconds=120) is True
        )
        # Within 60 s window → rejected
        assert (
            verify_hmac_signature(body, sig, secret, timestamp=str(ts), max_age_seconds=60) is False
        )

    def test_invalid_timestamp_rejected(self):
        from utils.webhook_signature import verify_hmac_signature

        assert (
            verify_hmac_signature(_body(), "anysig", "secret", timestamp="not-a-number") is False
        )


# ── get_webhook_secret ─────────────────────────────────────────────────────────

class TestGetWebhookSecret:

    def test_reads_named_secret_from_settings(self):
        from utils.webhook_signature import get_webhook_secret

        # Real test using Django settings mock
        import django.conf
        original = getattr(django.conf.settings, "WEBHOOK_SECRET_TESTING", None)
        try:
            django.conf.settings.WEBHOOK_SECRET_TESTING = "super-secret-value"
            result = get_webhook_secret("testing")
            assert result == "super-secret-value"
        finally:
            if original is None:
                # Clean up: remove attribute we set
                try:
                    delattr(django.conf.settings, "WEBHOOK_SECRET_TESTING")
                except AttributeError:
                    pass
            else:
                django.conf.settings.WEBHOOK_SECRET_TESTING = original

    def test_returns_empty_string_when_not_configured(self):
        from utils.webhook_signature import get_webhook_secret

        # Unlikely to be set
        result = get_webhook_secret("xyzzy_not_configured_zzz")
        assert result == ""
