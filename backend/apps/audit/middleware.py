"""
apps/audit/middleware.py

AuditContextMiddleware — stores request attribution data in thread-local
storage for the duration of each HTTP request so that Django signal handlers
(which run synchronously inside the same thread) can attach actor / IP /
user-agent metadata to AuditEvents even when no explicit ``actor`` argument
is passed to ``_write_event``.

Usage
-----
1. Register in ``MIDDLEWARE`` (after ``AuthenticationMiddleware`` so that
   ``request.user`` is already resolved):

       "apps.audit.middleware.AuditContextMiddleware",

2. In any signal handler or utility that calls ``_write_event`` without an
   explicit actor, import and call the helpers:

       from apps.audit.middleware import get_audit_context
       ctx = get_audit_context()
       # ctx.actor   → authenticated User or None
       # ctx.ip      → str | None
       # ctx.user_agent → str

Thread-safety
-------------
``threading.local()`` is per-thread, so concurrent requests do not interfere.
The context is cleared at the end of every request (``process_response`` and
``process_exception``) to prevent stale data leaking if the thread is reused.
"""

from __future__ import annotations

import threading

from utils.http import get_client_ip

_local = threading.local()


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


class _AuditContext:
    """Lightweight container for the three attribution fields."""

    __slots__ = ("actor", "ip", "user_agent")

    def __init__(self, actor=None, ip: str | None = None, user_agent: str = ""):
        self.actor = actor
        self.ip = ip
        self.user_agent = user_agent


_EMPTY_CTX = _AuditContext()


def get_audit_context() -> _AuditContext:
    """Return the current request's audit context, or an empty one if called outside a request."""
    return getattr(_local, "audit_ctx", _EMPTY_CTX)


def _set_audit_context(ctx: _AuditContext) -> None:
    _local.audit_ctx = ctx


def _clear_audit_context() -> None:
    _local.audit_ctx = _EMPTY_CTX


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class AuditContextMiddleware:
    """
    WSGI/ASGI-compatible middleware that populates thread-local audit context
    for every incoming request.

    Must be placed **after** ``django.contrib.auth.middleware.AuthenticationMiddleware``
    in the MIDDLEWARE list so that ``request.user`` is already resolved.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Populate context before the view (and any signals it triggers) runs.
        actor = None
        if hasattr(request, "user") and request.user.is_authenticated:
            actor = request.user

        ip = get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        _set_audit_context(_AuditContext(actor=actor, ip=ip, user_agent=user_agent))

        try:
            response = self.get_response(request)
        finally:
            # Always clear — prevents stale context leaking to the next request
            # on the same thread (common in Django's threaded dev server and
            # gunicorn/uvicorn thread pools).
            _clear_audit_context()

        return response
