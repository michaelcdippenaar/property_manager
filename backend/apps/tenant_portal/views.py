from __future__ import annotations

import base64
import mimetypes
import uuid

import anthropic
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.intel import update_tenant_intel
from apps.ai.models import TenantChatSession
from apps.ai.parsing import (
    MAINTENANCE_DRAFT_SYSTEM_PROMPT,
    parse_maintenance_draft_response,
    parse_tenant_ai_response,
)
from apps.ai.tenant_context import build_tenant_context
from apps.leases.models import Lease
from apps.leases.template_views import _get_anthropic_api_key
from apps.maintenance.models import MaintenanceRequest
from core.anthropic_web_fetch import (
    build_web_fetch_tools,
    extract_anthropic_assistant_text,
)
from core.contract_rag import query_contracts
from django.conf import settings

AGENT_MODEL = "claude-sonnet-4-6"

TENANT_SYSTEM_PROMPT = """You are Tremly's AI assistant for residential tenants in South Africa.

You may receive **retrieved excerpts** from the landlord's document library (lease agreements, house rules, policies). \
When you use them, mention the **source** path briefly. If excerpts do not answer the question, say so and suggest \
practical next steps (e.g. log a repair in the app, email the agent, check the signed lease).

**Brevity (important):** For simple FAQs — WiFi password, refuse day, parking rules, pool hours, “where do I find X” — keep the \
**reply** in the JSON to **2–5 short sentences** (roughly **under ~120 words**). Be direct: say where to look first (welcome pack, \
house rules, lease annexure, sticker on the router) and who to contact if it’s not there. **Do not** write long essays, full \
router-admin tutorials, default-gateway explanations, or step-by-step networking guides unless the tenant explicitly asked for \
that level of technical detail.

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
  "reply": "What you say to the tenant — clear and supportive; stay brief for simple FAQs (see Brevity). For emergencies tell them to call SAPS 10111 if a crime is in progress.",
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


def _maybe_update_session_title(
    session: TenantChatSession,
    ai_title: str | None,
    maintenance_ticket: dict | None,
) -> None:
    candidate = (ai_title or "").strip()[:200]
    if not candidate and maintenance_ticket:
        candidate = (maintenance_ticket.get("title") or "").strip()[:200]
    if not candidate or not _is_generic_conv_title(session.title):
        return
    TenantChatSession.objects.filter(pk=session.pk).update(title=candidate)
    session.title = candidate


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


def _next_message_id(messages: list) -> int:
    if not messages:
        return 1
    return max((int(m.get("id") or 0) for m in messages), default=0) + 1


def _append_messages(session: TenantChatSession, *new: dict) -> None:
    msgs = list(session.messages or [])
    msgs.extend(new)
    session.messages = msgs
    session.save(update_fields=["messages", "updated_at"])


def _store_tenant_upload(upload) -> str:
    raw_name = (getattr(upload, "name", None) or "file").lower()
    ext = ""
    if "." in raw_name:
        ext = "." + raw_name.rsplit(".", 1)[-1][:16]
    key = f"tenant_ai/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{ext}"
    default_storage.save(key, ContentFile(upload.read()))
    return key


def _message_to_claude_user_content(msg: dict):
    """String or list of blocks for Anthropic messages API."""
    kind = (msg.get("attachment_kind") or "").strip()
    text = (msg.get("content") or "").strip()
    max_img = int(getattr(settings, "TENANT_AI_MAX_IMAGE_BYTES", 12 * 1024 * 1024))
    storage_path = (msg.get("attachment_storage") or "").strip()

    if kind == "image" and storage_path:
        if not default_storage.exists(storage_path):
            return text or "[Tenant attached a photo but it could not be read.]"
        try:
            with default_storage.open(storage_path, "rb") as fh:
                raw = fh.read()
        except OSError:
            return text or "[Tenant attached a photo but it could not be read.]"
        if len(raw) > max_img:
            return (
                text
                + "\n\n[Photo too large for AI preview — staff can view the file in the portal.]"
            ).strip()
        b64 = base64.standard_b64encode(raw).decode("ascii")
        mt = _guess_image_media_type(storage_path)
        caption = text or "(Tenant attached a photo.)"
        return [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": mt, "data": b64},
            },
            {"type": "text", "text": caption},
        ]

    if kind == "video" and storage_path:
        name = storage_path.split("/")[-1]
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


def _serialize_stored_message(msg: dict, request) -> dict:
    out = {
        "id": msg.get("id"),
        "role": msg.get("role"),
        "content": msg.get("content") or "",
    }
    path = (msg.get("attachment_storage") or "").strip()
    k = msg.get("attachment_kind") or ""
    if path:
        url = default_storage.url(path)
        if request:
            url = request.build_absolute_uri(url)
        out["attachment_url"] = url
        out["attachment_kind"] = k
    else:
        out["attachment_url"] = None
        out["attachment_kind"] = k
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


def _session_for_user(request, pk: int) -> TenantChatSession:
    return get_object_or_404(TenantChatSession, pk=pk, user=request.user)


def _touch_session(session: TenantChatSession) -> None:
    TenantChatSession.objects.filter(pk=session.pk).update(updated_at=timezone.now())


def _conversation_transcript_for_draft(session: TenantChatSession) -> str:
    lines = []
    for m in session.messages or []:
        label = "Tenant" if m.get("role") == "user" else "Assistant"
        suffix = ""
        k = (m.get("attachment_kind") or "").strip()
        if k == "image":
            suffix = " [Photo attached]"
        elif k == "video":
            suffix = " [Video attached]"
        text = (m.get("content") or "").strip()
        lines.append(f"{label}: {text}{suffix}")
    return "\n".join(lines)


class TenantConversationsListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = TenantChatSession.objects.filter(user=request.user).order_by("-updated_at")
        out = []
        for c in qs:
            mlist = c.messages or []
            last = mlist[-1] if mlist else None
            last_text = (last.get("content") or "")[:200] if last else ""
            out.append(
                {
                    "id": c.id,
                    "title": c.title,
                    "last_message": last_text,
                    "updated_at": c.updated_at.isoformat(),
                }
            )
        return Response(out)

    def post(self, request):
        title = (request.data.get("title") or "").strip() or "New conversation"
        c = TenantChatSession.objects.create(user=request.user, title=title, messages=[])
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
        c = _session_for_user(request, pk)
        msgs = [_serialize_stored_message(m, request) for m in (c.messages or [])]
        return Response(
            {
                "id": c.id,
                "title": c.title,
                "maintenance_report_suggested": c.maintenance_report_suggested,
                "maintenance_request_id": c.maintenance_request_id,
                "agent_question_id": c.agent_question_id,
                "messages": msgs,
            }
        )


class TenantConversationMaintenanceDraftView(APIView):
    """AI: chat transcript → structured fields for the tenant maintenance report form."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        c = _session_for_user(request, pk)
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

        session = _session_for_user(request, pk)
        storage_path = ""
        if upload:
            storage_path = _store_tenant_upload(upload)

        now = timezone.now()
        uid = _next_message_id(session.messages or [])
        user_msg = {
            "id": uid,
            "role": "user",
            "content": content,
            "created_at": now.isoformat(),
            "attachment_kind": kind,
        }
        if storage_path:
            user_msg["attachment_storage"] = storage_path
        _append_messages(session, user_msg)
        session.refresh_from_db(fields=["messages", "updated_at"])
        _touch_session(session)

        def _linked_payload():
            return {
                "maintenance_request_id": session.maintenance_request_id,
                "agent_question_id": session.agent_question_id,
            }

        api_key = _get_anthropic_api_key()
        if not api_key:
            sorry = (
                "The AI assistant is not available right now (server configuration). "
                "Please try again later or contact your property manager."
            )
            aid = _next_message_id(session.messages or [])
            ai_msg = {
                "id": aid,
                "role": "assistant",
                "content": sorry,
                "created_at": timezone.now().isoformat(),
                "attachment_kind": "",
            }
            _append_messages(session, ai_msg)
            session.refresh_from_db(fields=["messages", "updated_at"])
            _touch_session(session)
            update_tenant_intel(request.user, session)
            return Response(
                {
                    "user_message": _serialize_stored_message(user_msg, request),
                    "ai_message": {
                        "id": ai_msg["id"],
                        "role": "assistant",
                        "content": sorry,
                        "attachment_url": None,
                        "attachment_kind": "",
                    },
                    "conversation": {"id": session.id, "title": session.title},
                    "maintenance_request": None,
                    "maintenance_report_suggested": session.maintenance_report_suggested,
                    **_linked_payload(),
                }
            )

        n_chunks = int(getattr(settings, "RAG_QUERY_CHUNKS", 8))
        rag_text = query_contracts(content, n_results=n_chunks)
        context_block = (
            "--- RETRIEVED DOCUMENT EXCERPTS (vector search) ---\n"
            f"{rag_text or '(No chunks retrieved.)'}\n"
        )
        tenant_ctx = build_tenant_context(request.user)
        system = TENANT_SYSTEM_PROMPT
        if tenant_ctx:
            system = f"{system}\n\n{tenant_ctx}"
        system = f"{system}\n\n{context_block}"

        anthropic_messages = []
        for m in session.messages or []:
            api_role = "assistant" if m.get("role") == "assistant" else "user"
            if api_role == "assistant":
                anthropic_messages.append(
                    {"role": "assistant", "content": (m.get("content") or "").strip()}
                )
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

        _maybe_update_session_title(session, conv_title, maintenance_ticket)

        created_mr: MaintenanceRequest | None = None
        ticket_context = content
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
            TenantChatSession.objects.filter(pk=session.pk).update(
                maintenance_request_id=created_mr.id
            )
            session.maintenance_request_id = created_mr.id

        maintenance_issue_identified = bool(created_mr) or (
            json_ok
            and maintenance_ticket is not None
            and bool((maintenance_ticket.get("title") or "").strip())
        )
        if maintenance_issue_identified and not session.maintenance_report_suggested:
            TenantChatSession.objects.filter(pk=session.pk).update(
                maintenance_report_suggested=True
            )
            session.maintenance_report_suggested = True
        maintenance_report_suggested = session.maintenance_report_suggested

        aid = _next_message_id(session.messages or [])
        ai_msg = {
            "id": aid,
            "role": "assistant",
            "content": reply_text,
            "created_at": timezone.now().isoformat(),
            "attachment_kind": "",
        }
        _append_messages(session, ai_msg)
        session.refresh_from_db(fields=["messages", "updated_at"])
        _touch_session(session)

        update_tenant_intel(
            request.user,
            session,
            maintenance_ticket=maintenance_ticket,
            json_ok=json_ok,
        )

        payload = {
            "user_message": _serialize_stored_message(user_msg, request),
            "ai_message": {
                "id": ai_msg["id"],
                "role": "assistant",
                "content": reply_text,
                "attachment_url": None,
                "attachment_kind": "",
            },
            "conversation": {"id": session.id, "title": session.title},
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
            **_linked_payload(),
        }
        return Response(payload)
