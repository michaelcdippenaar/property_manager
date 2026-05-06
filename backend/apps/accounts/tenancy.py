"""
apps/accounts/tenancy.py

Multi-tenant scaffolding for Klikk Rentals — the foundation for per-agency
data isolation. See ~/.claude/plans/fuzzy-giggling-squid.md for the full
multi-tenant rollout plan.

What lives here
---------------

1. **Thread-local tenant context** — populated by ``TenantContextMiddleware``
   from ``request.user.agency_id`` after auth. Mirrors the existing
   ``apps.audit.middleware.AuditContextMiddleware`` pattern.

2. **``current_agency_id()``** — read the active tenant from anywhere
   (views, serializers, signals) without threading a ``request`` object
   through the call stack.

3. **``override(agency_id=...)``** — context manager for code paths that
   *need* to operate on a specific tenant outside an HTTP request:

       from apps.accounts.tenancy import override
       with override(agency_id=42):
           # all TenantManager queries inside the block scope to agency 42
           Property.tenant_objects.all()

4. **``override(bypass=True)``** — superuser/system escape hatch. Disables
   scoping inside the block. Use only in trusted code paths (data
   migrations, system maintenance commands).

5. **``TenantManager``** — Django manager that auto-filters every queryset
   by the current ``agency_id``. Models opt in by adding
   ``tenant_objects = TenantManager()``. The default ``objects`` manager
   stays as the unscoped escape hatch for the Django admin and superuser
   tools (renamed to ``unscoped_objects`` per-model in Phase 2).

6. **``TenantContextMiddleware``** — sets / clears the thread-local on
   every HTTP request. Wired in ``config/settings/base.py`` MIDDLEWARE
   immediately after ``AuditContextMiddleware``.

Safety model
------------

If the tenant context is empty (``agency_id is None``) AND bypass is not
active, ``TenantManager.get_queryset()`` returns an empty queryset. This
is the *safe* default: code paths that legitimately operate without a
tenant (e.g. management commands) MUST opt in via ``override(...)`` or
explicitly use ``unscoped_objects``. Forgetting to set context yields
"no data" rather than "all data" — the reverse would be a silent leak.

This module has no model or DB dependencies and is safe to import from
anywhere, including ``apps.py``.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Iterator

from django.db import models

# ---------------------------------------------------------------------------
# Thread-local context
# ---------------------------------------------------------------------------

_local = threading.local()


class _TenantContext:
    """Lightweight container for the active tenant + bypass flag."""

    __slots__ = ("agency_id", "bypass")

    def __init__(self, agency_id: int | None = None, bypass: bool = False) -> None:
        self.agency_id = agency_id
        self.bypass = bypass


_EMPTY_CTX = _TenantContext()


def current_agency_id() -> int | None:
    """
    Return the active tenant's PK, or ``None`` if no tenant is set
    (anonymous request, management command, etc.).
    """
    return getattr(_local, "tenant_ctx", _EMPTY_CTX).agency_id


def is_bypass_active() -> bool:
    """True when the current code path has explicitly bypassed tenant scoping."""
    return getattr(_local, "tenant_ctx", _EMPTY_CTX).bypass


def _set_context(ctx: _TenantContext) -> None:
    _local.tenant_ctx = ctx


def _clear_context() -> None:
    _local.tenant_ctx = _EMPTY_CTX


@contextmanager
def override(agency_id: int | None = None, *, bypass: bool = False) -> Iterator[None]:
    """
    Temporarily override the current tenant context.

    Use cases:
      - **Cron / management commands**: ``with override(agency_id=42): ...``
      - **Backfill migrations**: iterate per agency, scope each pass
      - **Trusted system code** that legitimately spans tenants: ``with override(bypass=True): ...``

    The previous context is restored on exit, even if an exception is raised.
    Nesting is supported — innermost wins.
    """
    previous = getattr(_local, "tenant_ctx", _EMPTY_CTX)
    try:
        _set_context(_TenantContext(agency_id=agency_id, bypass=bypass))
        yield
    finally:
        _set_context(previous)


# ---------------------------------------------------------------------------
# Manager / QuerySet
# ---------------------------------------------------------------------------


class TenantQuerySet(models.QuerySet):
    """
    A queryset that doesn't add scoping itself — scoping is applied once at
    ``get_queryset()`` time by ``TenantManager``. Defined separately so
    individual models can extend it with their own custom queryset methods
    while still inheriting the auto-scoping behaviour.
    """


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):
    """
    Auto-filters queries by the current tenant.

    Per-tenant models opt in by adding::

        class MyModel(models.Model):
            agency = models.ForeignKey('accounts.Agency', on_delete=models.CASCADE)
            ...

            objects = models.Manager()           # unscoped escape hatch
            tenant_objects = TenantManager()     # scoped, default for views

    All ORM access from views / serializers / signals should use
    ``MyModel.tenant_objects``. ``MyModel.objects`` is reserved for Django
    admin, data migrations, and other trusted contexts.

    Behaviour:
      - Bypass active → no filter (full table)
      - Bypass not active, agency_id set → filter(agency_id=agency_id)
      - Bypass not active, no agency_id → ``none()`` (safe default)
    """

    def get_queryset(self) -> TenantQuerySet:
        qs = super().get_queryset()
        if is_bypass_active():
            return qs
        agency_id = current_agency_id()
        if agency_id is None:
            return qs.none()
        return qs.filter(agency_id=agency_id)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class TenantContextMiddleware:
    """
    Populate thread-local tenant context for every HTTP request.

    Must be placed **after** ``AuthenticationMiddleware`` (so ``request.user``
    is resolved) in the ``MIDDLEWARE`` setting. Conventionally placed right
    after ``AuditContextMiddleware`` since both share the same lifecycle.

    Anonymous requests, requests from users without an agency_id, and
    health-check probes leave the context empty. ``TenantManager`` then
    returns ``.none()`` for any per-tenant query — meaning a misconfigured
    public endpoint can't accidentally leak per-tenant data.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        agency_id: int | None = None
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            agency_id = getattr(user, "agency_id", None)

        _set_context(_TenantContext(agency_id=agency_id, bypass=False))

        try:
            response = self.get_response(request)
        finally:
            # Always clear — prevents stale context leaking onto the next
            # request on the same thread (gunicorn / uvicorn worker pools).
            _clear_context()

        return response
