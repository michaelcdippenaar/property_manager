"""
apps/ai/knowledge_views.py

Endpoints for reading and updating the admin-editable AI knowledge file.

GET  /api/v1/ai/knowledge/  — returns current knowledge content (admin only)
POST /api/v1/ai/knowledge/  — saves new content, busts cache, logs AuditEvent
"""
from __future__ import annotations

import logging

from django.utils import timezone
from rest_framework import status as drf_status
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.audit.models import AuditEvent
from utils.http import get_client_ip

from .knowledge import bust_cache, get_knowledge, save_knowledge

logger = logging.getLogger(__name__)

# Maximum bytes we will accept in a single save to prevent runaway payloads.
_MAX_CONTENT_BYTES = 512 * 1024  # 512 KB


def _log_audit(request, old_content: str, new_content: str) -> None:
    """Append an AuditEvent for a knowledge file save.  Never raises."""
    try:
        ip = get_client_ip(request) or None
        ua = request.META.get("HTTP_USER_AGENT", "")

        AuditEvent.objects.create(
            actor=request.user,
            actor_email=request.user.email,
            action="ai.knowledge.updated",
            target_repr="content/ai/knowledge.md",
            before_snapshot={"content": old_content},
            after_snapshot={"content": new_content},
            ip_address=ip,
            user_agent=ua,
            retention_years=5,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to log AuditEvent for ai.knowledge.updated")


class AIKnowledgeView(APIView):
    """
    GET  /api/v1/ai/knowledge/ — read current content
    POST /api/v1/ai/knowledge/ — save new content (busts cache, logs audit)

    Both methods require IsAdmin.
    """

    permission_classes = [IsAuthenticated, IsAdmin]
    renderer_classes = [JSONRenderer]

    def get(self, request):
        return Response({"content": get_knowledge()}, status=drf_status.HTTP_200_OK)

    def post(self, request):
        content = request.data.get("content")

        if content is None:
            return Response(
                {"detail": "'content' field is required."},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(content, str):
            return Response(
                {"detail": "'content' must be a string."},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        if len(content.encode("utf-8")) > _MAX_CONTENT_BYTES:
            return Response(
                {"detail": f"Content exceeds maximum allowed size ({_MAX_CONTENT_BYTES // 1024} KB)."},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        # Capture previous content for audit diff before overwriting.
        old_content = get_knowledge()

        try:
            save_knowledge(content)
        except OSError as exc:
            logger.error("Failed to write AI knowledge file: %s", exc)
            return Response(
                {"detail": "Failed to save knowledge file. See server logs."},
                status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        _log_audit(request, old_content, content)

        return Response(
            {"detail": "Knowledge file updated.", "saved_at": timezone.now().isoformat()},
            status=drf_status.HTTP_200_OK,
        )
