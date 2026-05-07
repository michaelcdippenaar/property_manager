"""
apps/audit/views.py

Read-only API for AuditEvent.

Endpoints
---------
GET /api/v1/audit/events/
    List all events — paginated, most recent first.
    Filterable by ?action=, ?content_type=, ?object_id=, ?actor=

GET /api/v1/audit/events/{id}/
    Single event detail.

GET /api/v1/audit/timeline/{app_label}/{model}/{pk}/
    Timeline of events for a specific object (e.g. /audit/timeline/leases/lease/42/).
"""

from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from apps.accounts.models import User
from apps.accounts.permissions import IsAdminOrAgencyAdmin
from apps.accounts.scoping import AgencyScopedQuerysetMixin

from .models import AuditEvent
from .serializers import AuditEventSerializer


class AuditEventViewSet(
    AgencyScopedQuerysetMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    """
    Read-only viewset for AuditEvent.

    Access is restricted to admin/agency-admin roles — audit events contain
    full field snapshots that may include PII.

    Phase 2.6: AgencyScopedQuerysetMixin enforces a HARD security boundary —
    agency A must never see agency B's audit trail. Defence in depth: an
    explicit ``filter(agency_id=...)`` is also applied below for non-admins.
    The hash chain (`prev_hash`, `self_hash`) is preserved at the model
    layer; this viewset only reads.
    """

    queryset = AuditEvent.objects.all()
    serializer_class = AuditEventSerializer
    permission_classes = [IsAuthenticated, IsAdminOrAgencyAdmin]
    ordering = ["-timestamp"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("actor", "content_type").order_by("-timestamp")
        # Defence in depth: even if the mixin is somehow bypassed, scope by
        # the caller's agency for non-admin users.
        user = getattr(self.request, "user", None)
        is_admin = bool(user and (getattr(user, "is_superuser", False) or getattr(user, "role", None) == User.Role.ADMIN))
        if not is_admin:
            agency_id = getattr(user, "agency_id", None) if user else None
            if agency_id is None:
                return qs.none()
            qs = qs.filter(agency_id=agency_id)

        action = self.request.query_params.get("action")
        if action:
            qs = qs.filter(action__icontains=action)

        content_type_label = self.request.query_params.get("content_type")
        if content_type_label:
            # Expect "app_label.model" format
            parts = content_type_label.split(".")
            if len(parts) == 2:
                qs = qs.filter(
                    content_type__app_label=parts[0],
                    content_type__model=parts[1],
                )

        object_id = self.request.query_params.get("object_id")
        if object_id:
            qs = qs.filter(object_id=object_id)

        actor_id = self.request.query_params.get("actor")
        if actor_id:
            qs = qs.filter(actor_id=actor_id)

        return qs


class AuditTimelineView(APIView):
    """
    Timeline of AuditEvents for a specific object.

    GET /api/v1/audit/timeline/{app_label}/{model}/{pk}/

    Returns events in chronological order (oldest first — natural for a timeline).
    """

    permission_classes = [IsAuthenticated, IsAdminOrAgencyAdmin]

    def get(self, request, app_label: str, model: str, pk: int):
        ct = get_object_or_404(ContentType, app_label=app_label, model=model)
        events_qs = AuditEvent.objects.filter(content_type=ct, object_id=pk)

        # Phase 2.6 — non-admin users can only see audit events for their
        # own agency. Hard boundary: an agency A reviewer must never see
        # agency B's audit trail for the same object id.
        user = getattr(request, "user", None)
        is_admin = bool(user and (getattr(user, "is_superuser", False) or getattr(user, "role", None) == User.Role.ADMIN))
        if not is_admin:
            agency_id = getattr(user, "agency_id", None) if user else None
            if agency_id is None:
                events_qs = events_qs.none()
            else:
                events_qs = events_qs.filter(agency_id=agency_id)

        events = (
            events_qs.select_related("actor", "content_type").order_by("timestamp")
        )
        serializer = AuditEventSerializer(events, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
