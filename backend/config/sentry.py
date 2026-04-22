"""
Sentry integration for Klikk backend.

Initialised once from base.py when SENTRY_DSN is set.
PII scrubbing: strips id_number, passport_number, bank_account_number and similar
fields from event payloads before they leave the process (POPIA compliance).
"""
from __future__ import annotations

import re

# Fields (keys) to redact from any dict in a Sentry event payload.
_PII_KEYS = re.compile(
    r"(id_number|id_no|passport|passport_number|bank_account|account_number"
    r"|bank_account_number|card_number|cvv|pin)",
    re.IGNORECASE,
)

_REDACTED = "[Filtered]"


def _scrub_dict(data: dict) -> dict:
    """Recursively redact PII keys from a dict."""
    cleaned: dict = {}
    for key, value in data.items():
        if _PII_KEYS.search(str(key)):
            cleaned[key] = _REDACTED
        elif isinstance(value, dict):
            cleaned[key] = _scrub_dict(value)
        elif isinstance(value, list):
            cleaned[key] = _scrub_list(value)
        else:
            cleaned[key] = value
    return cleaned


def _scrub_list(items: list) -> list:
    return [
        _scrub_dict(item) if isinstance(item, dict)
        else (_scrub_list(item) if isinstance(item, list) else item)
        for item in items
    ]


def _before_send(event: dict, hint: dict) -> dict:  # noqa: ARG001
    """Strip PII from request body, extra, contexts, and breadcrumb data."""
    # Request body
    request = event.get("request", {})
    if isinstance(request.get("data"), dict):
        request["data"] = _scrub_dict(request["data"])

    # Extra context
    if isinstance(event.get("extra"), dict):
        event["extra"] = _scrub_dict(event["extra"])

    # Breadcrumb data
    for breadcrumb in event.get("breadcrumbs", {}).get("values", []):
        if isinstance(breadcrumb.get("data"), dict):
            breadcrumb["data"] = _scrub_dict(breadcrumb["data"])

    return event


def init(dsn: str, *, environment: str, release: str | None = None, traces_sample_rate: float = 0.1) -> None:
    """Initialise the Sentry SDK.  Called from settings when SENTRY_DSN is non-empty."""
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    import logging

    sentry_sdk.init(
        dsn=dsn,
        integrations=[
            DjangoIntegration(
                transaction_style="url",
                middleware_spans=True,
                signals_spans=False,   # keep noise low
                cache_spans=False,
            ),
            LoggingIntegration(
                level=logging.WARNING,     # breadcrumbs from WARNING+
                event_level=logging.ERROR, # send to Sentry at ERROR+
            ),
        ],
        environment=environment,
        release=release,
        traces_sample_rate=traces_sample_rate,
        # Never send PII automatically (POPIA)
        send_default_pii=False,
        before_send=_before_send,
        # Don't report 4xx client errors as Sentry issues
        ignore_errors=[
            "django.http.Http404",
        ],
    )
