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
from apps.leases.models import Lease, LeaseTemplate  # noqa: E402

from fastmcp import FastMCP  # noqa: E402

mcp = FastMCP(
    name="tremly-property-manager",
    instructions=(
        "Tremly Property Manager MCP server. Provides access to tenant "
        "AI chat history, intelligence profiles, and lease template management "
        "for South African rental property management."
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
#  Lease Template Tools
# ──────────────────────────────────────────────

def _serialize_template_summary(t: LeaseTemplate) -> dict:
    fields_count = 0
    if t.content_html:
        try:
            content = json.loads(t.content_html)
            fields_count = len(content.get("fields", []))
        except (json.JSONDecodeError, TypeError):
            fields_count = len(t.fields_schema or [])
    else:
        fields_count = len(t.fields_schema or [])
    return {
        "id": t.id,
        "name": t.name,
        "version": t.version,
        "province": t.province,
        "is_active": t.is_active,
        "fields_count": fields_count,
        "has_html": bool(t.content_html),
        "has_docx": bool(t.docx_file),
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _serialize_template_full(t: LeaseTemplate) -> dict:
    data = _serialize_template_summary(t)
    # Parse content_html JSON envelope
    if t.content_html:
        try:
            content = json.loads(t.content_html)
            data["html"] = content.get("html", "")
            data["fields"] = content.get("fields", [])
        except (json.JSONDecodeError, TypeError):
            data["html"] = t.content_html
            data["fields"] = t.fields_schema or []
    else:
        data["html"] = ""
        data["fields"] = t.fields_schema or []
    data["header_html"] = t.header_html
    data["footer_html"] = t.footer_html
    return data


@mcp.tool
def list_lease_templates(include_inactive: bool = False) -> str:
    """List all lease templates with summary info (id, name, version, field count)."""
    qs = LeaseTemplate.objects.all()
    if not include_inactive:
        qs = qs.filter(is_active=True)
    return json.dumps([_serialize_template_summary(t) for t in qs], ensure_ascii=False)


@mcp.tool
def get_lease_template(template_id: int) -> str:
    """
    Get full lease template details including HTML content and fields schema.

    Returns the template's HTML body, merge fields list, header/footer HTML,
    and metadata.
    """
    try:
        t = LeaseTemplate.objects.get(pk=template_id)
    except LeaseTemplate.DoesNotExist:
        return json.dumps({"error": f"Template {template_id} not found."})
    return json.dumps(_serialize_template_full(t), ensure_ascii=False)


@mcp.tool
def update_lease_template(
    template_id: int,
    html: str | None = None,
    fields: list[dict] | None = None,
    name: str | None = None,
    version: str | None = None,
    province: str | None = None,
    header_html: str | None = None,
    footer_html: str | None = None,
) -> str:
    """
    Update a lease template's content, fields, or metadata.

    Parameters
    ----------
    template_id : ID of the template to update
    html : New HTML body content (the document text with merge field spans)
    fields : New fields schema list, e.g. [{"ref": "tenant_name", "label": "Tenant Name", "type": "text"}, ...]
    name : New template name
    version : New version string
    province : New province
    header_html : Header HTML shown at top of every page
    footer_html : Footer HTML shown at bottom of every page
    """
    try:
        t = LeaseTemplate.objects.get(pk=template_id)
    except LeaseTemplate.DoesNotExist:
        return json.dumps({"error": f"Template {template_id} not found."})

    # Update content_html JSON envelope
    if html is not None or fields is not None:
        current = {"v": 1, "html": "", "fields": []}
        if t.content_html:
            try:
                current = json.loads(t.content_html)
            except (json.JSONDecodeError, TypeError):
                current["html"] = t.content_html
        if html is not None:
            current["html"] = html
        if fields is not None:
            current["fields"] = fields
        t.content_html = json.dumps(current)

    if name is not None:
        t.name = name
    if version is not None:
        t.version = version
    if province is not None:
        t.province = province
    if header_html is not None:
        t.header_html = header_html
    if footer_html is not None:
        t.footer_html = footer_html

    t.save()
    return json.dumps({"ok": True, **_serialize_template_full(t)}, ensure_ascii=False)


@mcp.tool
def create_lease_template(
    name: str,
    html: str = "",
    fields: list[dict] | None = None,
    version: str = "1.0",
    province: str = "",
) -> str:
    """
    Create a new lease template.

    Parameters
    ----------
    name : Template name, e.g. "Standard Residential Lease"
    html : Initial HTML body content
    fields : Fields schema list
    version : Version string (default "1.0")
    province : Province (optional, leave blank for national)
    """
    content = json.dumps({"v": 1, "html": html, "fields": fields or []})
    t = LeaseTemplate.objects.create(
        name=name,
        version=version,
        province=province,
        content_html=content,
    )
    return json.dumps({"ok": True, **_serialize_template_full(t)}, ensure_ascii=False)


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


@mcp.resource("template://lease/{template_id}")
def lease_template_resource(template_id: int) -> str:
    """Full lease template content and fields."""
    try:
        t = LeaseTemplate.objects.get(pk=int(template_id))
    except LeaseTemplate.DoesNotExist:
        return json.dumps({"error": f"Template {template_id} not found."})
    return json.dumps(_serialize_template_full(t), ensure_ascii=False)


@mcp.resource("template://lease/list")
def lease_templates_list_resource() -> str:
    """All active lease templates (summary)."""
    templates = LeaseTemplate.objects.filter(is_active=True)
    return json.dumps([_serialize_template_summary(t) for t in templates], ensure_ascii=False)


# ──────────────────────────────────────────────
#  Maintenance Chat Tools
# ──────────────────────────────────────────────

def _serialize_activity(activity) -> dict:
    return {
        "id": activity.id,
        "activity_type": activity.activity_type,
        "message": activity.message,
        "metadata": activity.metadata,
        "created_by": {
            "id": activity.created_by_id,
            "name": activity.created_by.full_name if activity.created_by else None,
            "role": activity.created_by.role if activity.created_by else "system",
        } if activity.created_by_id else {"id": None, "name": "AI Agent", "role": "ai"},
        "created_at": activity.created_at.isoformat() if activity.created_at else None,
    }


@mcp.tool
def get_maintenance_chat(request_id: int, limit: int = 50) -> str:
    """
    Get the chat/activity history for a maintenance request.

    This is the per-issue conversation thread shared between tenants,
    agents/admins, and AI. Use this to monitor issue progress and
    understand context before responding.

    Parameters
    ----------
    request_id : MaintenanceRequest ID
    limit : max messages to return (default 50)
    """
    from apps.maintenance.models import MaintenanceActivity, MaintenanceRequest

    try:
        req = MaintenanceRequest.objects.select_related(
            "unit__property", "tenant", "supplier"
        ).get(pk=request_id)
    except MaintenanceRequest.DoesNotExist:
        return json.dumps({"error": f"Maintenance request {request_id} not found."})

    activities = (
        MaintenanceActivity.objects.filter(request=req)
        .select_related("created_by")
        .order_by("-created_at")[:limit]
    )

    return json.dumps({
        "request": {
            "id": req.pk,
            "title": req.title,
            "description": req.description,
            "priority": req.priority,
            "category": req.category,
            "status": req.status,
            "unit": f"{req.unit.unit_number} — {req.unit.property.name}" if req.unit else None,
            "tenant": req.tenant.full_name if req.tenant else None,
            "supplier": req.supplier.display_name if req.supplier else None,
        },
        "messages": [_serialize_activity(a) for a in reversed(list(activities))],
    }, ensure_ascii=False)


@mcp.tool
def post_maintenance_chat(
    request_id: int,
    message: str,
    activity_type: str = "note",
) -> str:
    """
    Post a message to a maintenance request chat thread.

    Use this to contribute to the per-issue conversation as an external
    agent. Messages posted here are visible to tenants (mobile app),
    agents/admins (admin dashboard), and other connected agents.

    Parameters
    ----------
    request_id : MaintenanceRequest ID
    message : message text to post
    activity_type : one of "note", "system" (default "note")
    """
    from apps.maintenance.models import MaintenanceActivity, MaintenanceRequest

    try:
        req = MaintenanceRequest.objects.get(pk=request_id)
    except MaintenanceRequest.DoesNotExist:
        return json.dumps({"error": f"Maintenance request {request_id} not found."})

    activity = MaintenanceActivity.objects.create(
        request=req,
        activity_type=activity_type,
        message=message.strip(),
        created_by=None,
        metadata={"source": "mcp_agent"},
    )
    return json.dumps({
        "ok": True,
        **_serialize_activity(activity),
    }, ensure_ascii=False)


@mcp.tool
def list_maintenance_requests(
    status: str | None = None,
    limit: int = 20,
) -> str:
    """
    List maintenance requests with summary info.

    Parameters
    ----------
    status : filter by status (open, in_progress, resolved, closed)
    limit : max results (default 20)
    """
    from apps.maintenance.models import MaintenanceRequest

    qs = MaintenanceRequest.objects.select_related(
        "unit__property", "tenant", "supplier"
    ).order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    qs = qs[:limit]

    results = []
    for req in qs:
        results.append({
            "id": req.pk,
            "title": req.title,
            "priority": req.priority,
            "category": req.category,
            "status": req.status,
            "unit": f"{req.unit.unit_number} — {req.unit.property.name}" if req.unit else None,
            "tenant": req.tenant.full_name if req.tenant else None,
            "supplier": req.supplier.display_name if req.supplier else None,
            "created_at": req.created_at.isoformat() if req.created_at else None,
        })
    return json.dumps(results, ensure_ascii=False)


# ──────────────────────────────────────────────
#  Maintenance Chat Resources
# ──────────────────────────────────────────────

@mcp.resource("maintenance://request/{request_id}/chat")
def maintenance_chat_resource(request_id: int) -> str:
    """Full chat history for a maintenance request."""
    from apps.maintenance.models import MaintenanceActivity
    activities = (
        MaintenanceActivity.objects.filter(request_id=int(request_id))
        .select_related("created_by")
        .order_by("created_at")[:100]
    )
    return json.dumps(
        [_serialize_activity(a) for a in activities],
        ensure_ascii=False,
    )


# ──────────────────────────────────────────────
#  Entry point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
