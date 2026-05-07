"""
apps/accounts/scoping.py

Phase 2.2 — DRF viewset mixins for tenant-scoped queries + perform_create
agency-stamping. Built on top of ``apps.accounts.tenancy.TenantManager``.

Why a mixin (not a base ViewSet)
-------------------------------

Klikk's existing viewsets already inherit from various DRF base classes
(`ModelViewSet`, `GenericViewSet`, `APIView`, custom mixins for property
access, role gating, etc.). Forcing a single base class would mean
rewriting every viewset's MRO. Instead, this module provides:

  * ``AgencyScopedQuerysetMixin`` — overrides ``get_queryset()`` to use
    ``<Model>.tenant_objects`` so the active agency_id auto-filters every
    list/retrieve/update/delete.

  * ``AgencyStampedCreateMixin`` — overrides ``perform_create(serializer)``
    to set ``agency_id=request.user.agency_id`` on the new instance. Stops
    a malicious / buggy serializer from creating data for a different
    agency.

  * ``AgencyScopedViewSet`` — convenience class that combines both mixins
    on top of `ModelViewSet`. Use for new viewsets; existing ones can
    selectively adopt the individual mixins.

Admin escape hatch
------------------

Users with ``role == ADMIN`` or ``is_superuser`` see ALL agencies' data —
they bypass the scoping mixin and fall back to `<Model>.objects` (the
unscoped default manager). System support, debugging, and DSAR
fulfilment depend on this. Agency-admins (the SaaS customer's principal)
do NOT bypass — they only see their own agency.

Failure mode
------------

If a request hits a scoped viewset but the user has no agency_id (and
isn't ADMIN), ``get_queryset()`` returns ``.none()``. The viewset
gracefully returns an empty list instead of leaking everything. A user
with no agency cannot create either — ``perform_create`` raises
``ValidationError``. This is the safe-by-default behaviour.

See ~/.claude/plans/fuzzy-giggling-squid.md (Phase 2) and
docs/compliance/popia-klikk-rentals-brief.md.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.exceptions import ValidationError

from apps.accounts.models import User

if TYPE_CHECKING:
    from django.db.models import QuerySet


def _is_admin(user) -> bool:
    """ADMIN role or Django superuser → bypass tenant scoping."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return getattr(user, "role", None) == User.Role.ADMIN


class AgencyScopedQuerysetMixin:
    """
    Mixin: ``get_queryset()`` returns the model's ``tenant_objects`` queryset
    (auto-filtered by ``current_agency_id()`` from the middleware).

    For ADMIN / superuser, falls through to ``objects`` (full table) so
    operator support staff can see everything.

    The viewset must declare a ``queryset`` class attribute as usual —
    we read its model from there, then swap in the tenant_objects manager.

    Example::

        class PropertyViewSet(AgencyScopedQuerysetMixin, viewsets.ModelViewSet):
            queryset = Property.objects.all()       # used only for the model resolution
            serializer_class = PropertySerializer
            permission_classes = [IsAgentOrAdmin]
    """

    def get_queryset(self) -> "QuerySet":  # type: ignore[override]
        """
        Filter the parent queryset by ``request.user.agency_id``. We don't
        rely on the thread-local TenantManager here — DRF's
        ``force_authenticate`` (and any non-session auth) populates
        ``request.user`` AFTER Django's middleware chain has run, so the
        middleware can't see it. The viewset has the request directly,
        so we filter explicitly. The TenantManager + middleware combo
        remains the right tool for signals / services / async code that
        doesn't have a request.
        """
        base = super().get_queryset()  # uses self.queryset by default
        user = getattr(self.request, "user", None)

        if _is_admin(user):
            # Admin bypass — full table (whatever the parent returned).
            return base

        agency_id = getattr(user, "agency_id", None) if user else None
        if agency_id is None:
            # Authenticated but no agency, OR anonymous on a public
            # endpoint that somehow inherited this mixin. Return empty
            # rather than the full table — fail closed.
            return base.none()

        return base.filter(agency_id=agency_id)


class AgencyStampedCreateMixin:
    """
    Mixin: ``perform_create()`` stamps ``agency_id = request.user.agency_id``
    on the new instance. Prevents create paths from leaking objects into
    another agency (deliberately or accidentally via mass assignment).

    For ADMIN / superuser, the user's `agency_id` may be None or arbitrary
    — admin users can create on behalf of any agency by passing `agency`
    explicitly in the request body. Non-admin users have it forced.
    """

    def perform_create(self, serializer):  # type: ignore[override]
        user = getattr(self.request, "user", None)

        if _is_admin(user):
            # Admin can pass `agency` explicitly; if absent, stamp their own.
            # QA-round-5 bug 2: DRF ModelSerializer exposes the FK as the
            # model field name ("agency"), not "agency_id". Check both keys
            # so admin "create on behalf of agency X" via {"agency": <pk>}
            # actually lands in agency X instead of falling through to the
            # admin's own agency. The "agency" value may be either an
            # Agency instance (when the serializer resolves the FK pk) or
            # a raw int (rare); handle both.
            agency_obj = serializer.validated_data.get("agency")
            explicit_agency_id = (
                serializer.validated_data.get("agency_id")
                or (agency_obj.pk if hasattr(agency_obj, "pk") else agency_obj)
            )
            agency_id = explicit_agency_id or getattr(user, "agency_id", None)
            if agency_id is None:
                # Admin without agency creating without specifying — block.
                raise ValidationError(
                    {"agency": "Admin user must specify `agency` when creating without an agency_id of their own."}
                )
            serializer.save(agency_id=agency_id)
            return

        # Non-admin: must have an agency.
        agency_id = getattr(user, "agency_id", None)
        if agency_id is None:
            raise ValidationError(
                {"detail": "Your user account is not linked to an agency. Contact your administrator."}
            )
        # Force the value — ignore any agency_id the client may have sent.
        serializer.save(agency_id=agency_id)


class AgencyScopedViewSet(AgencyScopedQuerysetMixin, AgencyStampedCreateMixin):
    """
    Convenience mixin combining both behaviours. Pair with a DRF base
    class (``viewsets.ModelViewSet``, etc.) when defining new viewsets:

        class MyViewSet(AgencyScopedViewSet, viewsets.ModelViewSet):
            queryset = MyModel.objects.all()
            serializer_class = MySerializer
            permission_classes = [IsAgentOrAdmin]

    Existing viewsets adopt one mixin at a time — easier rollout.
    """
    pass
