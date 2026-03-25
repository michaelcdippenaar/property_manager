from __future__ import annotations

import base64
import json
import mimetypes

import anthropic
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.leases.models import Lease
from apps.leases.template_views import _get_anthropic_api_key
from apps.maintenance.models import MaintenanceRequest
from core.anthropic_web_fetch import (
    anthropic_web_fetch_enabled,
    build_web_fetch_tools,
    extract_anthropic_assistant_text,
)
from core.contract_rag import query_contracts
from django.conf import settings

from .ai_parsing import (
    MAINTENANCE_DRAFT_SYSTEM_PROMPT,
    parse_maintenance_draft_response,
    parse_tenant_ai_response,
)
from .models import TenantAiConversation, TenantAiMessage

AGENT_MODEL = "claude-sonnet-4-6"

TENANT_SYSTEM_PROMPT = """You are Tremly's AI assistant for residential tenants in South Africa.

You may receive **retrieved excerpts** from the landlord's document library (lease agreements, house rules, policies). \
When you use them, mention the **source** path briefly. If excerpts do not answer the question, say so and suggest \
practical next steps (e.g. log a repair in the app, email the agent, check the signed lease).

**In-app repair form:** After a maintenance issue is recognized in this chat, the app shows a **Report maintenance issue** \
button below the composer. Tapping it runs a second AI step that turns this conversation into a structured form \
(title, description, category, priority) for the tenant to review and submit. When that applies, mention they can use \
that button for a formal report — in addition to **maintenance_ticket** in JSON when they are reporting a real issue.

**Not legal advice:** give general, practical guidance only; for disputes or legal questions, suggest consulting \
a qualified attorney or the Rental Housing Tribunal.

**Web (optional tool)**  
If **web_fetch** is available: do **not** call it unless the user's message **already includes** a full http(s) URL \
and asks you to read it. Otherwise ask them to paste an official link if they want a page opened.

**Maintenance tickets (required JSON output)**  
You must answer in a way that the app can parse. Respond with **ONLY** valid JSON (no markdown fences), shape:
{
  "reply": "What you say to the tenant — clear, supportive prose; for emergencies tell them to call SAPS 10111 if a crime is in progress.",
  "conversation_title": null OR "Very short thread name for the chat list, e.g. Broken window",
  "maintenance_ticket": null OR {
    "title": "Short title for staff (max ~80 chars)",
    "description": "What happened, what is damaged, what the tenant needs — for maintenance staff",
    "priority": "low" | "medium" | "high" | "urgent"
  }
}

Set **maintenance_ticket** to a non-null object when the tenant reports a **real property issue** that should be tracked \
(repairs, damage, leaks, pests, broken fixtures, **break-in / burglary / theft / forced entry / vandalism**, fire damage, \
serious electrical/plumbing failures, etc.). Use **priority** **urgent** for break-ins, ongoing danger, major security failure, \
or serious flooding / fire. Use **high** for serious but not immediately life-threatening issues.

Set **maintenance_ticket** to **null** for general questions, rent/account queries, how-to questions, or chit-chat — \
even if they mention maintenance in passing without reporting a current problem.

**conversation_title** (optional string, max ~60 chars)  
If the chat thread still has a generic title, suggest a short label for the inbox (e.g. "Kitchen leak", "Deposit question", \
"Break-in report"). Omit or use null if not needed. Use null once the topic is already clear from an existing specific title."""


def get_tenant_leases(user):
    """Leases where this user is linked as primary, co-tenant, or occupant."""
    return Lease.objects.filter(
        Q(primary_tenant__linked_user=user)
        | Q(co_tenants__person__linked_user=user)
        | Q(occupants__person__linked_user=user)
    ).distinct()


_SEVERE_HINTS = (
    "break-in",
    "break in",
    "burglary",
    "burglar",
    "robbed",
    "broken into",
    "forced entry",
    "someone broke",
    "stolen from",
    "theft from",
    "vandalis",
    "assault",
    "attacked",
    "fire in my",
    "the flat flooded",
    "burst pipe",
    "gas smell",
    "ceiling collapsed",
)


def _valid_priority(val) -> str:
    v = (str(val) if val is not None else "medium").lower().strip()
    allowed = {c[0] for c in MaintenanceRequest.Priority.choices}
    return v if v in allowed else MaintenanceRequest.Priority.MEDIUM


def _heuristic_severe_ticket(user_content: str) -> dict | None:
    """If the model misses JSON, still log urgent tickets for obvious security/emergency phrases."""
    c = user_content.lower()
    if not any(h in c for h in _SEVERE_HINTS):
        return None
    return {
        "title": "Urgent — incident reported via AI chat",
        "description": user_content.strip()[:8000],
        "priority": MaintenanceRequest.Priority.URGENT,
    }


def _is_generic_conv_title(title: str) -> bool:
    return (title or "").strip().lower() in ("ai assistant", "new conversation", "")


def _maybe_update_conversation_title(
    conv: TenantAiConversation,
    ai_title: str | None,
    maintenance_ticket: dict | None,
) -> None:
    candidate = (ai_title or "").strip()[:200]
    if not candidate and maintenance_ticket:
        candidate = (maintenance_ticket.get("title") or "").strip()[:200]
    if not candidate or not _is_generic_conv_title(conv.title):
        return
    TenantAiConversation.objects.filter(pk=conv.pk).update(title=candidate)
    conv.title = candidate


def _guess_image_media_type(filename: str) -> str:
    mt, _ = mimetypes.guess_type(filename or "")
    if mt in ("image/jpeg", "image/png", "image/gif", "image/webp"):
        return mt
    return "image/jpeg"


def _classify_upload(f) -> str | None:
    """Return 'image' or 'video' or None if unsupported."""
    name = (getattr(f, "name", None) or "").lower()
    ctype = (getattr(f, "content_type", None) or "").lower()
    if ctype.startswith("image/") or any(
        name.endswith(x) for x in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif")
    ):
        return "image"
    if ctype.startswith("video/") or any(
        name.endswith(x) for x in (".mp4", ".mov", ".m4v", ".webm", ".3gp")
    ):
        return "video"
    return None


def _message_to_claude_user_content(msg: TenantAiMessage):
    """String or list of blocks for Anthropic messages API."""
    kind = (msg.attachment_kind or "").strip()
    text = (msg.content or "").strip()
    max_img = int(getattr(settings, "TENANT_AI_MAX_IMAGE_BYTES", 12 * 1024 * 1024))

    if kind == "image" and msg.attachment:
        try:
            with msg.attachment.open("rb") as fh:
                raw = fh.read()
        except OSError:
            return text or "[Tenant attached a photo but it could not be read.]"
        if len(raw) > max_img:
            return (
                text
                + "\n\n[Photo too large for AI preview — staff can view the file in the portal.]"
            ).strip()
        b64 = base64.standard_b64encode(raw).decode("ascii")
        mt = _guess_image_media_type(msg.attachment.name)
        caption = text or "(Tenant attached a photo.)"
        return [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": mt, "data": b64},
            },
            {"type": "text", "text": caption},
        ]

    if kind == "video" and msg.attachment:
        name = (msg.attachment.name or "video").split("/")[-1]
        note = (
            f"\n\n[The tenant attached a video file ({name}). You cannot watch video — "
            f"rely on their message and suggest staff review the recording in the portal if needed.]"
        )
        if text:
            return (text + note).strip()
        return (
            f"(Tenant attached a video: {name}.) Please ask them to briefly describe what it shows "
            f"so you can help." + note
        )

    return text if text else "."


def _serialize_message(m: TenantAiMessage, request) -> dict:
    out = {"id": m.id, "role": m.role, "content": m.content}
    if m.attachment:
        url = m.attachment.url
        if request:
            url = request.build_absolute_uri(url)
        out["attachment_url"] = url
        out["attachment_kind"] = m.attachment_kind or ""
    else:
        out["attachment_url"] = None
        out["attachment_kind"] = m.attachment_kind or ""
    return out


def _default_unit_for_user(user):
    lease = (
        get_tenant_leases(user)
        .filter(status=Lease.Status.ACTIVE)
        .select_related("unit")
        .order_by("-start_date")
        .first()
    )
    return lease.unit if lease else None


def _create_mr_from_chat(user, ticket: dict, fallback_description: str) -> MaintenanceRequest | None:
    title = (ticket.get("title") or "").strip()[:200]
    if not title:
        return None
    desc = (ticket.get("description") or fallback_description or "").strip()[:8000]
    pr = _valid_priority(ticket.get("priority"))
    unit = _default_unit_for_user(user)
    if not unit:
        return None
    return MaintenanceRequest.objects.create(
        tenant=user,
        unit=unit,
        title=title,
        description=desc,
        priority=pr,
        status=MaintenanceRequest.Status.OPEN,
    )


def _conversation_for_user(request, pk: int) -> TenantAiConversation:
    return get_object_or_404(TenantAiConversation, pk=pk, user=request.user)


def _touch_conversation(conv: TenantAiConversation) -> None:
    TenantAiConversation.objects.filter(pk=conv.pk).update(updated_at=timezone.now())


class TenantConversationsListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = TenantAiConversation.objects.filter(user=request.user).order_by("-updated_at")
        out = []
        for c in qs:
            last = c.messages.order_by("-created_at").first()
            out.append(
                {
                    "id": c.id,
                    "title": c.title,
                    "last_message": (last.content[:200] if last else ""),
                    "updated_at": c.updated_at.isoformat(),
                }
            )
        return Response(out)

    def post(self, request):
        title = (request.data.get("title") or "").strip() or "New conversation"
        c = TenantAiConversation.objects.create(user=request.user, title=title)
        return Response(
            {
                "id": c.id,
                "title": c.title,
                "last_message": "",
                "updated_at": c.updated_at.isoformat(),
            },
            status=201,
        )


class TenantConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        c = _conversation_for_user(request, pk)
        msgs = [
            _serialize_message(m, request)
            for m in c.messages.all()
        ]
        return Response(
            {
                "id": c.id,
                "title": c.title,
                "maintenance_report_suggested": c.maintenance_report_suggested,
                "messages": msgs,
            }
        )


def _conversation_transcript_for_draft(conv: TenantAiConversation) -> str:
    lines = []
    for m in conv.messages.order_by("created_at"):
        label = "Tenant" if m.role == "user" else "Assistant"
        suffix = ""
        k = (m.attachment_kind or "").strip()
        if k == "image":
            suffix = " [Photo attached]"
        elif k == "video":
            suffix = " [Video attached]"
        text = (m.content or "").strip()
        lines.append(f"{label}: {text}{suffix}")
    return "\n".join(lines)


class TenantConversationMaintenanceDraftView(APIView):
    """AI: chat transcript → structured fields for the tenant maintenance report form."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        c = _conversation_for_user(request, pk)
        if not c.maintenance_report_suggested:
            return Response(
                {
                    "error": "No maintenance context in this chat yet. Describe the issue to the assistant first.",
                },
                status=400,
            )
        transcript = _conversation_transcript_for_draft(c)
        if not transcript.strip():
            return Response({"error": "No messages to summarize."}, status=400)

        api_key = _get_anthropic_api_key()
        if not api_key:
            return Response(
                {"error": "AI drafting is unavailable right now."},
                status=503,
            )

        client = anthropic.Anthropic(api_key=api_key)
        try:
            response = client.messages.create(
                model=AGENT_MODEL,
                max_tokens=1024,
                system=MAINTENANCE_DRAFT_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"Conversation transcript:\n\n{transcript}",
                    }
                ],
            )
        except Exception as e:
            return Response({"error": f"AI error: {e}"}, status=502)

        raw = extract_anthropic_assistant_text(response).strip()
        draft = parse_maintenance_draft_response(raw)
        if not draft:
            return Response(
                {
                    "error": "Could not build a draft from the conversation. Try again or fill the form manually.",
                },
                status=502,
            )
        return Response(draft)


class TenantConversationMessageCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, pk: int):
        content = (request.data.get("content") or "").strip()
        upload = request.FILES.get("file") or request.FILES.get("attachment")

        max_vid = int(getattr(settings, "TENANT_AI_MAX_VIDEO_BYTES", 45 * 1024 * 1024))
        max_img = int(getattr(settings, "TENANT_AI_MAX_IMAGE_BYTES", 12 * 1024 * 1024))

        kind = ""
        if upload:
            kind = _classify_upload(upload) or ""
            if not kind:
                return Response(
                    {"error": "Unsupported file type. Use a photo (JPEG, PNG, …) or video (MP4, MOV, …)."},
                    status=400,
                )
            lim = max_vid if kind == "video" else max_img
            if upload.size > lim:
                return Response(
                    {"error": f"File too large (max {lim // (1024 * 1024)} MB for {kind}s)."},
                    status=400,
                )

        if not content and not upload:
            return Response(
                {"error": "Send a message and/or attach a photo or video."},
                status=400,
            )

        if upload and not content:
            content = "(Photo attached)" if kind == "image" else "(Video attached)"

        c = _conversation_for_user(request, pk)
        user_msg = TenantAiMessage(
            conversation=c,
            role="user",
            content=content,
            attachment_kind=kind,
        )
        if upload:
            user_msg.attachment = upload
        user_msg.save()
        _touch_conversation(c)

        api_key = _get_anthropic_api_key()
        if not api_key:
            sorry = (
                "The AI assistant is not available right now (server configuration). "
                "Please try again later or contact your property manager."
            )
            ai_msg = TenantAiMessage.objects.create(
                conversation=c, role="assistant", content=sorry
            )
            _touch_conversation(c)
            return Response(
                {
                    "user_message": _serialize_message(user_msg, request),
                    "ai_message": {
                        "id": ai_msg.id,
                        "role": "assistant",
                        "content": sorry,
                        "attachment_url": None,
                        "attachment_kind": "",
                    },
                    "conversation": {"id": c.id, "title": c.title},
                    "maintenance_request": None,
                    "maintenance_report_suggested": c.maintenance_report_suggested,
                }
            )

        n_chunks = int(getattr(settings, "RAG_QUERY_CHUNKS", 8))
        rag_text = query_contracts(user_msg.content, n_results=n_chunks)
        context_block = (
            "--- RETRIEVED DOCUMENT EXCERPTS (vector search) ---\n"
            f"{rag_text or '(No chunks retrieved.)'}\n"
        )
        system = f"{TENANT_SYSTEM_PROMPT}\n\n{context_block}"

        prior = list(
            c.messages.filter(created_at__lte=user_msg.created_at).order_by(
                "created_at"
            )
        )
        anthropic_messages = []
        for m in prior:
            api_role = "assistant" if m.role == "assistant" else "user"
            if api_role == "assistant":
                anthropic_messages.append({"role": "assistant", "content": m.content})
            else:
                block = _message_to_claude_user_content(m)
                anthropic_messages.append({"role": "user", "content": block})

        tools = build_web_fetch_tools()
        max_tokens = 4096 if tools else 3072
        kwargs: dict = {
            "model": AGENT_MODEL,
            "max_tokens": max_tokens,
            "system": system,
            "messages": anthropic_messages,
        }
        if tools:
            kwargs["tools"] = tools

        client = anthropic.Anthropic(api_key=api_key)
        try:
            response = client.messages.create(**kwargs)
        except Exception as e:
            return Response({"error": f"AI error: {e}"}, status=502)

        raw_ai = extract_anthropic_assistant_text(response).strip()
        if not raw_ai:
            return Response({"error": "Empty model response."}, status=502)

        reply_text, maintenance_ticket, json_ok, conv_title = parse_tenant_ai_response(
            raw_ai
        )

        _maybe_update_conversation_title(c, conv_title, maintenance_ticket)

        created_mr: MaintenanceRequest | None = None
        ticket_context = user_msg.content
        if json_ok and maintenance_ticket and (maintenance_ticket.get("title") or "").strip():
            created_mr = _create_mr_from_chat(
                request.user, maintenance_ticket, ticket_context
            )
        if created_mr is None:
            hint = _heuristic_severe_ticket(ticket_context)
            if hint:
                created_mr = _create_mr_from_chat(request.user, hint, ticket_context)

        if created_mr:
            note = (
                f"\n\nWe've logged this for the property team "
                f"(maintenance request #{created_mr.id})."
            )
            if note.strip() not in reply_text:
                reply_text = reply_text + note

        maintenance_issue_identified = bool(created_mr) or (
            json_ok
            and maintenance_ticket is not None
            and bool((maintenance_ticket.get("title") or "").strip())
        )
        if maintenance_issue_identified and not c.maintenance_report_suggested:
            TenantAiConversation.objects.filter(pk=c.pk).update(
                maintenance_report_suggested=True
            )
            c.maintenance_report_suggested = True
        maintenance_report_suggested = c.maintenance_report_suggested

        ai_msg = TenantAiMessage.objects.create(
            conversation=c, role="assistant", content=reply_text
        )
        _touch_conversation(c)

        payload = {
            "user_message": _serialize_message(user_msg, request),
            "ai_message": {
                "id": ai_msg.id,
                "role": "assistant",
                "content": reply_text,
                "attachment_url": None,
                "attachment_kind": "",
            },
            "conversation": {"id": c.id, "title": c.title},
            "maintenance_request": (
                {
                    "id": created_mr.id,
                    "title": created_mr.title,
                    "priority": created_mr.priority,
                    "status": created_mr.status,
                }
                if created_mr
                else None
            ),
            "maintenance_report_suggested": maintenance_report_suggested,
        }
        return Response(payload)
