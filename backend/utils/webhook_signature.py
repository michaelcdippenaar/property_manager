"""
HMAC-SHA256 webhook signature verification helpers for Klikk.

Usage — in any webhook view:

    from utils.webhook_signature import verify_hmac_signature, reject_if_invalid

    def post(self, request):
        if not verify_hmac_signature(request.body, request.META.get("HTTP_X_KLIKK_SIGNATURE", ""), secret):
            return reject_if_invalid()
        ...

Environment variables
---------------------
WEBHOOK_SECRET_<NAME>   Shared HMAC secret for a named integration.
                        Rotate by updating the env var and restarting;
                        old requests (>5 min) are already rejected by the
                        optional timestamp check.

Replay protection
-----------------
Pass ``timestamp`` (epoch seconds, int or str) and ``max_age_seconds`` to
``verify_hmac_signature`` to reject replayed payloads whose timestamp is
older than ``max_age_seconds`` (default: 300 s / 5 min).

The canonical signed payload for timestamped verification is:
    "<timestamp>.<raw_body_hex>"

When no timestamp is provided, only the HMAC of the raw body is verified.
"""

import hashlib
import hmac
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


def verify_hmac_signature(
    body: bytes,
    signature: str,
    secret: str,
    *,
    timestamp: Optional[str] = None,
    max_age_seconds: int = 300,
) -> bool:
    """
    Verify an HMAC-SHA256 signature over *body*.

    Parameters
    ----------
    body:
        Raw request body bytes.
    signature:
        The hex HMAC digest provided by the sender (from the signature header).
    secret:
        Shared HMAC secret (plaintext, loaded from env).
    timestamp:
        Optional epoch-seconds string sent alongside the signature.  When
        provided, the signed payload is ``"<timestamp>.<body_hex>"`` and the
        timestamp is also checked to be within *max_age_seconds* of now.
    max_age_seconds:
        How old a timestamped payload may be before it is rejected as a replay.
        Defaults to 300 (5 minutes).  Ignored when *timestamp* is None.

    Returns
    -------
    bool
        True if the signature is valid (and the timestamp, if supplied, is
        within the acceptable window).  False otherwise.
    """
    if not secret:
        # No secret configured — verification is not enforced for this integration.
        # Log a warning so operators notice.
        logger.warning(
            "webhook_signature: secret is empty — signature verification skipped. "
            "Set WEBHOOK_SECRET_<NAME> in the environment to enforce verification."
        )
        return True

    if not signature:
        logger.warning("webhook_signature: missing signature header — rejected.")
        return False

    # Replay protection
    if timestamp is not None:
        try:
            ts = int(timestamp)
        except (TypeError, ValueError):
            logger.warning("webhook_signature: invalid timestamp %r — rejected.", timestamp)
            return False

        age = abs(time.time() - ts)
        if age > max_age_seconds:
            logger.warning(
                "webhook_signature: timestamp too old (age=%.1f s, max=%d s) — rejected.",
                age,
                max_age_seconds,
            )
            return False

        # Canonical payload: "<timestamp>.<body_as_hex>"
        signed_payload = f"{ts}.{body.hex()}".encode()
    else:
        signed_payload = body

    expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    valid = hmac.compare_digest(expected, signature.lower().strip())

    if not valid:
        logger.warning("webhook_signature: HMAC mismatch — rejected.")

    return valid


def get_webhook_secret(name: str) -> str:
    """
    Load the shared webhook secret for integration *name* from Django settings.

    The setting key is ``WEBHOOK_SECRET_<NAME_UPPER>``.
    Returns an empty string if not configured (caller decides whether to enforce).

    Example::

        secret = get_webhook_secret("gotenberg")
        # reads settings.WEBHOOK_SECRET_GOTENBERG
    """
    from django.conf import settings

    key = f"WEBHOOK_SECRET_{name.upper()}"
    return getattr(settings, key, "") or ""
