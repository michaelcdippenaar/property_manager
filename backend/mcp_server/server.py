#!/usr/bin/env python
"""
Tremly Tenant Context — MCP Server (stdio transport).

Exposes tenant chat sessions and intelligence profiles so any AI agent
(Cursor, external pipelines, training harnesses) can query cross-chat
context for a tenant.

Usage (Cursor / Claude Desktop):
    python backend/mcp_server/server.py

Requires the same .env / DJANGO_SETTINGS_MODULE as the main backend.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# ── Bootstrap Django before importing models ──
_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django  # noqa: E402

django.setup()

from django.db.models import Q  # noqa: E402

from apps.accounts.models import User  # noqa: E402
from apps.ai.models import TenantChatSession, TenantIntelligence  # noqa: E402
from apps.leases.models import Lease  # noqa: E402

from fastmcp import FastMCP  # noqa: E402

mcp = FastMCP(
    name="tremly-tenant-context",
    instructions=(
        "Tremly Tenant Context server. Provides read-only access to tenant "
        "AI chat history and intelligence profiles for South African rental "
        "property management. Use these tools to understand tenant behaviour, "
        "review past conversations, and get cross-chat context."
    ),
)


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────

def _user_by_id(user_id: int) -> User | None:
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return None


def _serialize_session(session: TenantChatSession) -> dict:
    msgs = session.messages or []
    return {
        "id": session.id,
        "user_id": session.user_id,
        "title": session.title,
        "message_count": len(msgs),
        "maintenance_request_id": session.maintenance_request_id,
        "agent_question_id": session.agent_question_id,
        "maintenance_report_suggested": session.maintenance_report_suggested,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        "messages": msgs,
    }


def _serialize_session_summary(session: TenantChatSession) -> dict:
    """Lighter version without full message bodies."""
    msgs = session.messages or []
    last_text = ""
    if msgs:
        last_text = (msgs[-1].get("content") or "")[:200]
    return {
        "id": session.id,
        "user_id": session.user_id,
        "title": session.title,
        "message_count": len(msgs),
        "last_message_preview": last_text,
        "maintenance_request_id": session.maintenance_request_id,
        "agent_question_id": session.agent_question_id,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }


def _serialize_intel(intel: TenantIntelligence) -> dict:
    return {
        "user_id": intel.user_id,
        "property_id": intel.property_ref_id,
        "unit_id": intel.unit_ref_id,
        "facts": intel.facts or {},
        "question_categories": intel.question_categories or {},
        "total_chats": intel.total_chats,
        "total_messages": intel.total_messages,
        "complaint_score": intel.complaint_score,
        "last_chat_at": intel.last_chat_at.isoformat() if intel.last_chat_at else None,
        "updated_at": intel.updated_at.isoformat() if intel.updated_at else None,
    }


def _tenant_users_for_property(property_id: int) -> list[int]:
    """User IDs of tenants linked to a property via active leases."""
    leases = Lease.objects.filter(
        unit__property_id=property_id,
        status=Lease.Status.ACTIVE,
    ).select_related("primary_tenant")
    user_ids = set()
    for lease in leases:
        if lease.primary_tenant and lease.primary_tenant.linked_user_id:
            user_ids.add(lease.primary_tenant.linked_user_id)
    return list(user_ids)


# ──────────────────────────────────────────────
#  Tools
# ──────────────────────────────────────────────

@mcp.tool
def get_chat_session(session_id: int) -> str:
    """Fetch a single chat session by ID with the full message thread."""
    try:
        session = TenantChatSession.objects.get(pk=session_id)
    except TenantChatSession.DoesNotExist:
        return json.dumps({"error": f"Chat session {session_id} not found."})
    return json.dumps(_serialize_session(session), ensure_ascii=False)


@mcp.tool
def list_tenant_chats(
    user_id: int,
    limit: int = 20,
    include_messages: bool = False,
    has_maintenance_request: bool | None = None,
) -> str:
    """
    List chat sessions for a tenant.

    Parameters
    ----------
    user_id : tenant's User.id
    limit : max sessions to return (default 20)
    include_messages : if True, include full message arrays; otherwise summaries only
    has_maintenance_request : if True/False, filter by presence of a linked maintenance request
    """
    qs = TenantChatSession.objects.filter(user_id=user_id).order_by("-updated_at")
    if has_maintenance_request is True:
        qs = qs.filter(maintenance_request__isnull=False)
    elif has_maintenance_request is False:
        qs = qs.filter(maintenance_request__isnull=True)
    sessions = qs[:limit]
    serializer = _serialize_session if include_messages else _serialize_session_summary
    return json.dumps([serializer(s) for s in sessions], ensure_ascii=False)


@mcp.tool
def get_tenant_context(user_id: int) -> str:
    """
    Full intelligence profile for a tenant: unit, property, complaint score,
    question categories, key facts extracted from chats, and recent chat summaries.
    """
    user = _user_by_id(user_id)
    if not user:
        return json.dumps({"error": f"User {user_id} not found."})

    intel = TenantIntelligence.objects.filter(user=user).first()
    intel_data = _serialize_intel(intel) if intel else {"note": "No intelligence profile yet."}

    recent = TenantChatSession.objects.filter(user=user).order_by("-updated_at")[:5]
    recent_summaries = [_serialize_session_summary(s) for s in recent]

    return json.dumps(
        {
            "user": {
                "id": user.id,
                "email": user.email,
                "name": f"{user.first_name} {user.last_name}".strip(),
                "phone": getattr(user, "phone", ""),
                "role": user.role,
            },
            "intelligence": intel_data,
            "recent_chats": recent_summaries,
        },
        ensure_ascii=False,
    )


@mcp.tool
def search_tenant_chats(
    user_id: int,
    query: str,
    limit: int = 10,
) -> str:
    """
    Keyword search across a tenant's chat history.
    Searches message content in the JSON messages array using PostgreSQL containment.
    Falls back to Python-level filtering for broader compatibility.
    """
    sessions = TenantChatSession.objects.filter(user_id=user_id).order_by("-updated_at")
    q_lower = query.lower()
    matches = []
    for session in sessions:
        matching_msgs = []
        for msg in session.messages or []:
            content = (msg.get("content") or "").lower()
            if q_lower in content:
                matching_msgs.append({
                    "message_id": msg.get("id"),
                    "role": msg.get("role"),
                    "content": msg.get("content", "")[:500],
                    "created_at": msg.get("created_at"),
                })
        if matching_msgs:
            matches.append({
                "session_id": session.id,
                "session_title": session.title,
                "updated_at": session.updated_at.isoformat() if session.updated_at else None,
                "matching_messages": matching_msgs[:5],
            })
        if len(matches) >= limit:
            break
    return json.dumps(
        {"query": query, "user_id": user_id, "results": matches},
        ensure_ascii=False,
    )


@mcp.tool
def list_property_chats(property_id: int, limit: int = 30) -> str:
    """
    All recent chat sessions from tenants at a given property.
    Resolves tenants via active leases.
    """
    user_ids = _tenant_users_for_property(property_id)
    if not user_ids:
        return json.dumps({"error": f"No active tenants found for property {property_id}."})
    sessions = (
        TenantChatSession.objects.filter(user_id__in=user_ids)
        .order_by("-updated_at")[:limit]
    )
    return json.dumps(
        [_serialize_session_summary(s) for s in sessions],
        ensure_ascii=False,
    )


# ──────────────────────────────────────────────
#  Resources
# ──────────────────────────────────────────────

@mcp.resource("tenant://chats/{user_id}")
def tenant_chats_resource(user_id: int) -> str:
    """All chat sessions for a tenant (full messages)."""
    sessions = TenantChatSession.objects.filter(user_id=user_id).order_by("-updated_at")
    return json.dumps([_serialize_session(s) for s in sessions], ensure_ascii=False)


@mcp.resource("tenant://chats/{user_id}/latest")
def tenant_latest_chats_resource(user_id: int) -> str:
    """Most recent 5 chat sessions for a tenant."""
    sessions = TenantChatSession.objects.filter(user_id=user_id).order_by("-updated_at")[:5]
    return json.dumps([_serialize_session(s) for s in sessions], ensure_ascii=False)


@mcp.resource("tenant://intel/{user_id}")
def tenant_intel_resource(user_id: int) -> str:
    """Intelligence profile for a tenant."""
    intel = TenantIntelligence.objects.filter(user_id=user_id).first()
    if not intel:
        return json.dumps({"note": f"No intelligence profile for user {user_id}."})
    return json.dumps(_serialize_intel(intel), ensure_ascii=False)


@mcp.resource("tenant://property/{property_id}/chats")
def property_chats_resource(property_id: int) -> str:
    """All recent chats for tenants at a property."""
    user_ids = _tenant_users_for_property(int(property_id))
    if not user_ids:
        return json.dumps([])
    sessions = (
        TenantChatSession.objects.filter(user_id__in=user_ids)
        .order_by("-updated_at")[:50]
    )
    return json.dumps(
        [_serialize_session_summary(s) for s in sessions],
        ensure_ascii=False,
    )


# ──────────────────────────────────────────────
#  Entry point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
