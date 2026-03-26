"""
Agent-facing assistant: maintenance skill index + vectorized contracts +
agent Q&A knowledge + optional web_fetch.

Provides RAG-powered AI chat for property letting agents, with:
  - Full maintenance skill digest (trades, symptom phrases, resolution steps)
  - Agent Q&A knowledge base (staff-answered questions)
  - Optional maintenance request context injection
  - Multi-turn conversation history support
  - Rate limiting (30 requests/minute for agents)
  - Retry with backoff on Claude API calls
"""
from __future__ import annotations

import logging

import anthropic
from django.conf import settings
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.leases.template_views import _get_anthropic_api_key
from apps.maintenance.models import MaintenanceSkill
from core.anthropic_web_fetch import (
    anthropic_web_fetch_enabled,
    build_web_fetch_tools,
    extract_anthropic_assistant_text,
)
from core.contract_rag import query_agent_qa, query_contracts, rag_collection_stats

import time as _time

logger = logging.getLogger(__name__)

AGENT_MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are Tremly's assistant for property letting agents in South Africa.

You are given:
1) Retrieved excerpts from the office **document library** (lease agreements, house rules, contracts, policies). \
   Prefer these for factual questions about what is written in those files. Name the **source** path when you quote.
2) A detailed **maintenance skill** catalogue from the database (trades, symptoms, resolution steps) for triage context.
3) **Staff-answered Q&A** pairs from past interactions — previously answered questions that are relevant to this query.

If the library excerpts do not contain the answer, say so clearly. Suggest practical next steps (e.g. check the signed \
PDF on file, confirm with the landlord).

**Web (optional tool)**
If **web_fetch** is available: do **not** call it on the first reply unless the user's message **already includes** \
a full http(s) URL and asks you to read or verify that page. Otherwise **ask** whether they want you to open a link, \
and have them paste the official URL in a follow-up message. Only fetch URLs that already appear in the conversation.

Reply in clear prose. Use markdown headings or bullets when helpful."""


class IsAgentOrAdmin(BasePermission):
    """Only allow users with AGENT or ADMIN role."""
    def has_permission(self, request, view):
        u = request.user
        return bool(
            u and u.is_authenticated and u.role in (User.Role.AGENT, User.Role.ADMIN)
        )


class AgentChatThrottle(UserRateThrottle):
    """30 agent assist queries per minute."""
    rate = "30/min"
    scope = "agent_chat"


def _skills_digest(limit: int = 50) -> str:
    """
    Build a detailed skill catalogue for the system prompt.

    Includes trade, name, symptom phrases (for AI matching), and
    resolution steps — giving the agent assistant full triage context.
    """
    lines: list[str] = []
    qs = (
        MaintenanceSkill.objects.filter(is_active=True)
        .order_by("trade", "name")[:limit]
    )
    for skill in qs:
        header = f"- [{skill.trade}] {skill.name}"
        # Include symptom phrases if available
        symptoms = skill.symptom_phrases or []
        if symptoms:
            header += f" | Symptoms: {', '.join(str(s) for s in symptoms[:5])}"
        # Include resolution steps if available
        steps = skill.steps or []
        if steps:
            step_text = "; ".join(str(s) for s in steps[:5])
            header += f" | Steps: {step_text}"
        lines.append(header)
    return "\n".join(lines) if lines else "(No active skills in the database.)"


class AgentAssistRagStatusView(APIView):
    """
    Check RAG collection stats and web fetch configuration.

    Returns chunk counts for all collections (contracts, agent Q&A,
    chat knowledge), the embedding model in use, and web_fetch status.
    """
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
    """
    RAG-powered AI chat for property agents.

    Accepts:
      - message: the agent's query (required)
      - maintenance_request_id: optional, injects request context
      - history: optional list of {role, content} for multi-turn

    Returns:
      - reply: AI response text
      - rag_populated: whether contract excerpts were included
      - rag_chunks_returned: number of contract chunks used
      - qa_populated: whether staff Q&A knowledge was included
      - web_fetch_enabled: whether web_fetch tool is available
    """
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]
    throttle_classes = [AgentChatThrottle]

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

        # ── Optional: inject maintenance request context ──
        request_context = ""
        maintenance_request_id = request.data.get("maintenance_request_id")
        if maintenance_request_id:
            try:
                from apps.maintenance.models import MaintenanceRequest, MaintenanceActivity
                req = MaintenanceRequest.objects.select_related(
                    "unit__property", "supplier", "tenant"
                ).get(pk=maintenance_request_id)
                activities = (
                    MaintenanceActivity.objects.filter(request=req)
                    .select_related("created_by")
                    .order_by("created_at")[:30]
                )
                chat_lines = "\n".join(
                    f"[{a.created_by.full_name if a.created_by else 'System'} "
                    f"({a.created_by.role if a.created_by else 'system'})]: {a.message}"
                    for a in activities
                )
                request_context = (
                    f"\n\n--- CURRENT MAINTENANCE REQUEST ---\n"
                    f"ID: #{req.pk}\n"
                    f"Title: {req.title}\n"
                    f"Description: {req.description}\n"
                    f"Priority: {req.priority}\n"
                    f"Category: {req.category}\n"
                    f"Status: {req.status}\n"
                    f"Unit: {req.unit.unit_number} — {req.unit.property.name}\n"
                    f"Reported by: {req.tenant.full_name}\n"
                    f"Assigned supplier: {req.supplier.display_name if req.supplier else 'Unassigned'}\n"
                    f"\n--- CHAT HISTORY ---\n{chat_lines or '(No messages yet)'}"
                )
            except Exception as e:
                logger.warning(
                    "Could not load maintenance request #%s context: %s",
                    maintenance_request_id, e,
                )
                request_context = (
                    f"\n\n[Warning: could not load maintenance request #{maintenance_request_id} "
                    f"context — it may not exist or have missing data.]"
                )

        # ── Multi-turn history ──
        history = request.data.get("history") or []

        # ── RAG: contract excerpts ──
        n_chunks = int(getattr(settings, "RAG_QUERY_CHUNKS", 8))
        rag_text = query_contracts(message, n_results=n_chunks)

        # ── RAG: staff-answered Q&A ──
        qa_text = query_agent_qa(message, n_results=3)

        # ── Maintenance skills digest ──
        skills = _skills_digest()

        context_block = (
            "--- RETRIEVED DOCUMENT EXCERPTS (vector search) ---\n"
            f"{rag_text or '(No chunks retrieved)'}\n\n"
            f"--- MAINTENANCE SKILLS (active catalogue) ---\n{skills}"
        )
        if qa_text:
            context_block += (
                f"\n\n--- STAFF-ANSWERED Q&A (relevant past answers) ---\n{qa_text}"
            )
        context_block += request_context

        system = f"{SYSTEM_PROMPT}\n\n{context_block}"

        messages = [
            {"role": m["role"], "content": m["content"]}
            for m in history
            if m.get("role") in ("user", "assistant")
        ]
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

        client = anthropic.Anthropic(api_key=api_key, max_retries=2)
        t0 = _time.monotonic()
        try:
            response = client.messages.create(**kwargs)
        except Exception as e:
            logger.error("Agent assist AI error: %s", e)
            return Response({"error": f"AI error: {e}"}, status=502)
        latency_ms = int((_time.monotonic() - t0) * 1000)

        # Log token usage for monitoring
        from apps.maintenance.models import AgentTokenLog
        AgentTokenLog.log_call(
            endpoint="agent_assist",
            response=response,
            user=request.user,
            latency_ms=latency_ms,
            metadata={"maintenance_request_id": maintenance_request_id},
        )

        reply = extract_anthropic_assistant_text(response).strip()
        if not reply:
            return Response({"error": "Empty model response."}, status=502)

        return Response(
            {
                "reply": reply,
                "rag_populated": bool(rag_text.strip()),
                "rag_chunks_returned": rag_text.count("--- source:"),
                "qa_populated": bool(qa_text.strip()),
                "web_fetch_enabled": bool(tools),
            }
        )
