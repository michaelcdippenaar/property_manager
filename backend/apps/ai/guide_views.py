"""
AI Guide endpoint — POST /api/v1/ai/guide/

Accepts { message } and calls Anthropic claude-3-5-haiku with a tool-use
loop.  The portal is derived strictly from request.user.role — the client
cannot supply or override it.  Returns { reply, action } where `action` is
a GuideAction-compatible dict (or null if no navigation was needed).

Persists each interaction to GuideInteraction for analytics.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

import anthropic
import sentry_sdk
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from rest_framework import status as drf_status

from apps.ai.guide_tools import TOOL_ACTION_MAP, get_tools_for_portal, is_tool_allowed
from apps.ai.models import GuideInteraction
from apps.ai.scrubber import scrub as scrub_pii

User = get_user_model()

logger = logging.getLogger(__name__)

GUIDE_MODEL = "claude-haiku-4-5"
MESSAGE_MAX_LENGTH = 2000

SYSTEM_PROMPT = """\
You are the Klikk navigation assistant embedded in the property management admin portal.
Your job is to understand what the user wants to do and call the appropriate navigation tool.

Rules:
1. Always call exactly one tool if the intent is clear.
2. If the intent is ambiguous or you cannot match a tool, reply in plain text to ask for clarification.
3. Keep replies concise — one sentence is usually enough.
4. You are operating in the "{portal}" portal — only tools available to that portal are listed.
5. Do not invent tool names. Only use the tools provided.
"""

# Maps User.Role values to the portal name used by the tool allowlist.
# Roles not listed here are not permitted to use the AI Guide (403).
_ROLE_TO_PORTAL: dict[str, str] = {
    User.Role.ESTATE_AGENT: "agent",
    User.Role.MANAGING_AGENT: "agent",
    User.Role.AGENT: "agent",           # deprecated role — keep mapping
    User.Role.AGENCY_ADMIN: "agent",
    User.Role.ADMIN: "agent",
    User.Role.OWNER: "owner",
    User.Role.SUPPLIER: "supplier",
}


def _portal_for_user(user) -> str | None:
    """Return the portal name for the given user, or None if not permitted."""
    return _ROLE_TO_PORTAL.get(user.role)


class AIGuideThrottle(UserRateThrottle):
    rate = "20/min"


def _call_guide(message: str, portal: str) -> dict[str, Any]:
    """
    Run the claude-3-5-haiku tool-use loop and return
    { reply: str, action: dict | None, intent: str | None }.
    """
    api_key = getattr(settings, "ANTHROPIC_API_KEY", "") or ""
    if not api_key:
        return {
            "reply": "AI Guide is not configured. Please contact your administrator.",
            "action": None,
            "intent": None,
        }

    tools = get_tools_for_portal(portal)
    client = anthropic.Anthropic(api_key=api_key, timeout=30.0)

    response = client.messages.create(
        model=GUIDE_MODEL,
        max_tokens=256,
        system=SYSTEM_PROMPT.format(portal=portal),
        tools=tools,
        messages=[{"role": "user", "content": message}],
    )

    # Extract tool call (if any)
    tool_use_block = None
    text_block = None

    for block in response.content:
        if block.type == "tool_use":
            tool_use_block = block
        elif block.type == "text":
            text_block = block

    if tool_use_block is not None:
        tool_name = tool_use_block.name

        # Safety: double-check the model didn't hallucinate an out-of-scope tool
        if not is_tool_allowed(tool_name, portal):
            logger.warning(
                "AI Guide returned disallowed tool %r for portal=%r — ignoring",
                tool_name,
                portal,
            )
            return {
                "reply": "I'm not able to do that in this portal.",
                "action": None,
                "intent": tool_name,
            }

        action = TOOL_ACTION_MAP.get(tool_name)
        # Build a friendly reply if the model didn't also emit a text block
        reply = (text_block.text.strip() if text_block else None) or _default_reply(
            tool_name
        )
        return {"reply": reply, "action": action, "intent": tool_name}

    # No tool call — model replied in prose
    reply = (text_block.text.strip() if text_block else "") or (
        "I'm not sure how to help with that. "
        "Try asking me to navigate somewhere, like \"show me leases\" or \"go to maintenance\"."
    )
    return {"reply": reply, "action": None, "intent": None}


def _default_reply(tool_name: str) -> str:
    """Produce a sensible fallback reply for a tool name."""
    _map = {
        "go_to_dashboard": "Taking you to the Dashboard.",
        "owner_go_to_dashboard": "Taking you to the Owner Dashboard.",
        "create_property": "Navigating to Add Property — I've highlighted the button for you.",
        "list_properties": "Opening the Properties list.",
        "owner_list_properties": "Opening your Properties.",
        "list_leases": "Navigating to Leases.",
        "owner_list_leases": "Opening your Leases.",
        "view_maintenance": "Taking you to Maintenance Issues.",
        "list_tenants": "Opening the Tenants list.",
        "list_payments": "Navigating to Payments.",
    }
    return _map.get(tool_name, "Done — navigating now.")


class AIGuideView(APIView):
    """POST /api/v1/ai/guide/ — AI-powered navigation intent mapper."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [AIGuideThrottle]
    # Force JSON-only responses — the SPA never wants the browsable API HTML
    # (also avoids content-negotiation flakiness if Accept header is missing).
    renderer_classes = [JSONRenderer]

    def post(self, request):
        # request_id lets the SPA / Sentry correlate a 500 with backend logs.
        request_id = uuid.uuid4().hex[:12]

        try:
            return self._handle(request, request_id=request_id)
        except Exception as exc:  # noqa: BLE001 — last-resort safety net
            # Anything that escapes _handle is a bug — log structured + 500 cleanly.
            logger.exception(
                "AI Guide unhandled exception (request_id=%s, user_id=%s): %s",
                request_id,
                getattr(request.user, "id", None),
                exc,
            )
            # Explicit capture ensures Sentry receives this even if the logging
            # integration is not configured for the apps.ai logger in some envs.
            sentry_sdk.capture_exception(exc)
            return Response(
                {
                    "error": True,
                    "message": "Something went wrong. Please try again.",
                    "reply": "Something went wrong. Please try again.",
                    "action": None,
                    "request_id": request_id,
                },
                status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _handle(self, request, *, request_id: str):
        if not getattr(settings, "ENABLE_AI_GUIDE", True):
            return Response(
                {"detail": "AI Guide is disabled.", "request_id": request_id},
                status=drf_status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        message = (request.data.get("message") or "").strip()

        if not message:
            return Response(
                {"detail": "message is required.", "request_id": request_id},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        if len(message) > MESSAGE_MAX_LENGTH:
            return Response(
                {
                    "detail": f"message must be {MESSAGE_MAX_LENGTH} characters or fewer.",
                    "request_id": request_id,
                },
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        # Derive portal strictly from the authenticated user's role — never
        # trust a client-supplied portal field (privilege escalation risk).
        portal = _portal_for_user(request.user)
        if portal is None:
            return Response(
                {
                    "detail": "Your account role is not permitted to use the AI Guide.",
                    "request_id": request_id,
                },
                status=drf_status.HTTP_403_FORBIDDEN,
            )

        # POPIA s72 — scrub PII before sending to Anthropic or persisting.
        clean_message = scrub_pii(message)

        try:
            result = _call_guide(clean_message, portal)
        except anthropic.APIError as exc:
            logger.exception(
                "AI Guide anthropic.APIError (request_id=%s, user_id=%s, portal=%s): %s",
                request_id,
                request.user.id,
                portal,
                exc,
            )
            return Response(
                {
                    "reply": "Sorry, I'm having trouble connecting to the AI service. Please try again.",
                    "action": None,
                    "request_id": request_id,
                },
                status=drf_status.HTTP_200_OK,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "AI Guide unexpected _call_guide failure (request_id=%s, user_id=%s, portal=%s): %s",
                request_id,
                request.user.id,
                portal,
                exc,
            )
            return Response(
                {
                    "reply": "Something went wrong. Please try again.",
                    "action": None,
                    "request_id": request_id,
                },
                status=drf_status.HTTP_200_OK,
            )

        # Persist interaction — store the scrubbed message, not the raw input.
        # Persistence failures must NEVER take down the user-visible reply.
        try:
            GuideInteraction.objects.create(
                user=request.user,
                portal=portal,
                message=clean_message,
                intent=result.get("intent") or "",
                action_taken=result.get("action") or {},
                completed=result.get("action") is not None,
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "AI Guide GuideInteraction persist failed (request_id=%s, user_id=%s)",
                request_id,
                request.user.id,
            )

        return Response(
            {
                "reply": result["reply"],
                "action": result["action"],
            },
            status=drf_status.HTTP_200_OK,
        )
