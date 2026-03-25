"""
Agent-facing assistant: maintenance skill index + vectorized contracts + optional web_fetch.
"""
from __future__ import annotations

import anthropic
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.leases.template_views import _get_anthropic_api_key
from apps.maintenance.models import MaintenanceSkill
from core.anthropic_web_fetch import (
    anthropic_web_fetch_enabled,
    build_web_fetch_tools,
    extract_anthropic_assistant_text,
)
from core.contract_rag import query_contracts, rag_collection_stats
from django.conf import settings

AGENT_MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are Tremly's assistant for property letting agents in South Africa.

You are given:
1) Retrieved excerpts from the office **document library** (lease agreements, house rules, contracts, policies). \
   Prefer these for factual questions about what is written in those files. Name the **source** path when you quote.
2) A list of **maintenance skill** titles from the database (for triage context).

If the library excerpts do not contain the answer, say so clearly. Suggest practical next steps (e.g. check the signed \
PDF on file, confirm with the landlord).

**Web (optional tool)**  
If **web_fetch** is available: do **not** call it on the first reply unless the user's message **already includes** \
a full http(s) URL and asks you to read or verify that page. Otherwise **ask** whether they want you to open a link, \
and have them paste the official URL in a follow-up message. Only fetch URLs that already appear in the conversation.

Reply in clear prose. Use markdown headings or bullets when helpful."""


class IsAgentOrAdmin(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(
            u and u.is_authenticated and u.role in (User.Role.AGENT, User.Role.ADMIN)
        )


def _skills_digest(limit: int = 50) -> str:
    lines: list[str] = []
    qs = (
        MaintenanceSkill.objects.filter(is_active=True)
        .order_by("trade", "name")
        .values_list("trade", "name")[:limit]
    )
    for trade, name in qs:
        lines.append(f"- [{trade}] {name}")
    return "\n".join(lines) if lines else "(No active skills in the database.)"


class AgentAssistRagStatusView(APIView):
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]

    def get(self, request):
        stats = rag_collection_stats()
        return Response(
            {
                **stats,
                "documents_root": str(getattr(settings, "CONTRACT_DOCUMENTS_ROOT", "")),
                "web_fetch_enabled": anthropic_web_fetch_enabled(),
            }
        )


class AgentAssistChatView(APIView):
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]

    def post(self, request):
        message = (request.data.get("message") or "").strip()
        if not message:
            return Response({"error": "message is required"}, status=400)

        api_key = _get_anthropic_api_key()
        if not api_key:
            return Response(
                {"error": "ANTHROPIC_API_KEY is not configured."},
                status=503,
            )

        # Optional: inject maintenance request context
        request_context = ""
        maintenance_request_id = request.data.get("maintenance_request_id")
        if maintenance_request_id:
            try:
                from apps.maintenance.models import MaintenanceRequest, MaintenanceActivity
                req = MaintenanceRequest.objects.select_related("unit__property", "supplier", "tenant").get(
                    pk=maintenance_request_id
                )
                activities = MaintenanceActivity.objects.filter(request=req).select_related("created_by").order_by("created_at")[:30]
                chat_lines = "\n".join(
                    f"[{a.created_by.full_name if a.created_by else 'System'} ({a.created_by.role if a.created_by else 'system'})]: {a.message}"
                    for a in activities
                )
                request_context = (
                    f"\n\n--- CURRENT MAINTENANCE REQUEST ---\n"
                    f"ID: #{req.pk}\n"
                    f"Title: {req.title}\n"
                    f"Description: {req.description}\n"
                    f"Priority: {req.priority}\n"
                    f"Status: {req.status}\n"
                    f"Unit: {req.unit.unit_number} — {req.unit.property.name}\n"
                    f"Reported by: {req.tenant.full_name}\n"
                    f"Assigned supplier: {req.supplier.display_name if req.supplier else 'Unassigned'}\n"
                    f"\n--- CHAT HISTORY ---\n{chat_lines or '(No messages yet)'}"
                )
            except Exception:
                pass

        # Optional multi-turn history
        history = request.data.get("history") or []

        n_chunks = int(getattr(settings, "RAG_QUERY_CHUNKS", 8))
        rag_text = query_contracts(message, n_results=n_chunks)
        skills = _skills_digest()

        context_block = (
            "--- RETRIEVED DOCUMENT EXCERPTS (vector search) ---\n"
            f"{rag_text or '(No chunks retrieved)'}\n\n"
            f"--- MAINTENANCE SKILLS (active, sample) ---\n{skills}"
            f"{request_context}"
        )

        system = f"{SYSTEM_PROMPT}\n\n{context_block}"

        messages = [{"role": m["role"], "content": m["content"]} for m in history if m.get("role") in ("user", "assistant")]
        messages.append({"role": "user", "content": message})

        tools = build_web_fetch_tools()
        max_tokens = 3072 if tools else 2048
        kwargs: dict = {
            "model": AGENT_MODEL,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        client = anthropic.Anthropic(api_key=api_key)
        try:
            response = client.messages.create(**kwargs)
        except Exception as e:
            return Response({"error": f"AI error: {e}"}, status=502)

        reply = extract_anthropic_assistant_text(response).strip()
        if not reply:
            return Response({"error": "Empty model response."}, status=502)

        return Response(
            {
                "reply": reply,
                "rag_populated": bool(rag_text.strip()),
                "rag_chunks_returned": rag_text.count("--- source:"),
                "web_fetch_enabled": bool(tools),
            }
        )
