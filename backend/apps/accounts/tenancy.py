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
def tenant_context_for_task(agency_id_or_obj) -> Iterator[None]:
    """
    Tenant context wrapper for async / Celery / threading tasks.

    QA-round-5 bug 3: task entry points run *outside* the
    ``TenantContextMiddleware`` lifecycle, so ``current_agency_id()`` is
    ``None`` by default. Any tenant-scoped queryset (``Model.tenant_objects``)
    inside such a task would silently return ``.none()``. Tasks must either
    (a) derive the agency from the task's primary input (e.g.
    ``lease.agency_id``) and wrap the body in this context manager, or
    (b) explicitly use ``unscoped_objects`` / ``Model.objects``.

    Example::

        from apps.accounts.tenancy import tenant_context_for_task
        def my_task(lease_id: int):
            lease = Lease.objects.get(pk=lease_id)
            with tenant_context_for_task(lease.agency_id):
                # ... tenant_objects queries inside this block ...

    Accepts either a raw int agency_id or an object with a ``.pk`` attr
    (e.g. an Agency instance) for caller convenience. Restores the
    previous context on exit.
    """
    if agency_id_or_obj is None:
        agency_id: int | None = None
    elif hasattr(agency_id_or_obj, "pk"):
        agency_id = agency_id_or_obj.pk
    else:
        agency_id = int(agency_id_or_obj)

    with override(agency_id=agency_id):
        yield


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


# ---------------------------------------------------------------------------
# Defence-in-depth: agency_id backfill from parent FK on pre_save
# ---------------------------------------------------------------------------
#
# The CTO audit on 2026-05-12 surfaced multiple `agency_id=NULL` orphans
# created by code paths that bypassed ``AgencyStampedCreateMixin.perform_create``
# (custom @action handlers, serializer `objects.create(...)` calls, etc.).
# Each of those is its own fix, but the systemic risk persists: every future
# code path that writes a row without going through the viewset's perform_create
# can produce a silent orphan. Orphans are then invisible through ``tenant_objects``
# and may leak across tenants depending on how downstream queries are written.
#
# Mitigation: a single ``pre_save`` receiver that — for any model declaring
# ``AGENCY_PARENT_FIELD = '<fk_attr>'`` as a class attribute — copies the
# parent's ``agency_id`` onto the instance when the instance's own
# ``agency_id`` is None. This makes "save a child without explicit agency_id"
# automatically correct rather than silently broken.
#
# Cost: one ``getattr(sender, ...)`` per save on any model. If the attribute
# isn't declared, the receiver returns immediately. Negligible.
#
# Models opt in by declaring (example):
#
#     class PropertyAgentAssignment(models.Model):
#         AGENCY_PARENT_FIELD = 'property'      # ← attribute name of the parent FK
#         agency   = models.ForeignKey(Agency, ...)
#         property = models.ForeignKey(Property, ...)
#
# Top-level models (Property, Landlord, Agency itself) do NOT opt in; their
# ``agency_id`` must be set explicitly at create time via the mixin or the
# RegisterSerializer.

def _backfill_agency_id_from_parent(sender, instance, **kwargs):
    """Pre-save receiver — see module-level note above."""
    parent_attr = getattr(sender, "AGENCY_PARENT_FIELD", None)
    if not parent_attr:
        return
    # Only act when the row genuinely has no agency_id. Never overwrite an
    # explicitly set value (admins creating on behalf of another agency,
    # cross-agency moves, etc. — all preserved).
    if getattr(instance, "agency_id", None) is not None:
        return
    parent = getattr(instance, parent_attr, None)
    if parent is None:
        return
    parent_agency_id = getattr(parent, "agency_id", None)
    if parent_agency_id is not None:
        instance.agency_id = parent_agency_id


def connect_agency_backfill_signal() -> None:
    """Wire ``_backfill_agency_id_from_parent`` to ``pre_save``.

    Called once from ``AccountsConfig.ready()``. Idempotent — connecting the
    same receiver twice with the same dispatch_uid is a no-op in Django.
    """
    from django.db.models.signals import pre_save

    pre_save.connect(
        _backfill_agency_id_from_parent,
        dispatch_uid="accounts.tenancy.backfill_agency_id_from_parent",
    )
