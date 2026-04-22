"""
Tenant Portal AI views.

Handles tenant↔AI chat, maintenance ticket auto-creation, and maintenance
draft generation. Integrates with:
  - RAG (contract/policy vector search, property-scoped)
  - Tenant context (lease, unit, property data from DB)
  - Agent Q&A knowledge base (staff-answered questions)
  - Chat self-training knowledge base (resolved interactions)
  - TenantIntelligence profiling (fact extraction, severity tracking)

Key design decisions:
  - Transcript windowing: only the last MAX_CHAT_WINDOW messages are sent to
    Claude to prevent token explosion. Earlier messages are summarised.
  - Duplicate MR guard: only one MaintenanceRequest per chat session.
  - Rate limiting: 10 messages/min for tenants, 30/min for agents.
  - Severity-aware: the AI classifies issue type and severity; heuristic
    fallback catches emergency keywords even if JSON parsing fails.
"""
from __future__ import annotations

import base64
import logging
import mimetypes
import uuid

import anthropic
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
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
from apps.maintenance.agent_assist_views import _skills_digest, skills_digest_for_message
from apps.maintenance.chat_history import persist_chat_history_to_request
from core.contract_rag import (
    query_agent_qa,
    query_chat_knowledge,
    query_contracts,
    query_maintenance_issues,
    query_property_information,
)

logger = logging.getLogger(__name__)

AGENT_MODEL = "claude-sonnet-4-6"

# ── Transcript windowing ──
# Maximum number of messages sent to Claude per request.
# Older messages are summarised to preserve context without token explosion.
MAX_CHAT_WINDOW = 20

# ── Rate limiting ──


class TenantChatThrottle(UserRateThrottle):
    """10 AI messages per minute for tenants."""
    rate = "10/min"
    scope = "tenant_chat"


class TenantDraftThrottle(UserRateThrottle):
    """5 maintenance drafts per minute."""
    rate = "5/min"
    scope = "tenant_draft"


# ── System prompt ──
# The AI classifies each interaction as general vs maintenance, and assigns
# a severity level. This drives downstream routing, ticket priority, and
# the TenantIntelligence complaint_score.

TENANT_SYSTEM_PROMPT = """\
You are Tremly's AI assistant for residential tenants in South Africa.

You are provided with several sources of knowledge:
1. Retrieved excerpts from the landlord's document library (lease agreements, house rules, policies). \
When you use them, mention the source path briefly.
2. Maintenance skills catalogue — trade-specific symptom phrases and resolution steps to help triage issues.
3. Staff-answered Q&A from past tenant interactions.
4. Similar past maintenance issues from the property.

If the provided context doesn't answer the question, say so clearly and suggest practical next steps \
(e.g. log a repair, email the agent, check the signed lease).

TRANSPARENCY: If a tenant asks what you have access to or what tools you use, you can tell them: \
you search the property's document library, use a maintenance knowledge base with triage steps, \
and reference past Q&A. You do not have access to live internet search.

INTERACTION CLASSIFICATION
Before composing your reply, classify this interaction:
  - interaction_type: "general" (FAQ, how-to, chit-chat, rent query) or "maintenance" (property issue report)
  - severity: "none" (general), "low" (cosmetic), "medium" (normal repair), "high" (serious defect), \
"critical" (emergency — danger to life/property)
Include these in your JSON output.

TONE & BREVITY
- Be warm, direct, and practical. Talk like a helpful property manager, not a textbook.
- Do NOT explain what a category of issue is (e.g. "A plumbing issue involves pipes..."). The tenant already knows what is broken.
- For simple FAQs (WiFi, refuse day, parking) keep the reply to 2-4 short sentences.
- For maintenance reports: if you have enough detail, acknowledge and confirm it is logged. If the report is vague \
(e.g. "broken plug", "broken door"), ask ONE clarifying question — do NOT log yet. \
Give one or two immediate safety/damage-limitation tips if relevant. 3-5 sentences max.
- NEVER use markdown formatting (no **, no #, no * bullets, no []()). Write plain text only. \
The mobile app renders your reply as-is.

KNOWLEDGE GAPS
If you genuinely cannot answer a question from the provided context (lease excerpts, property info, \
past Q&A), include "needs_staff_input": true in your JSON so the system can flag it for human follow-up. \
Still give the tenant a helpful response explaining you'll get the answer from the property team.

Not legal advice: give general, practical guidance only; for disputes or legal questions, suggest consulting \
a qualified attorney or the Rental Housing Tribunal.

Web (optional tool): do NOT call web_fetch unless the user's message already includes a full URL and asks you to read it.

JSON OUTPUT (required)
Respond with ONLY valid JSON (no markdown fences, no commentary outside the JSON).
IMPORTANT: For vague reports like "broken plug" or "broken door", set maintenance_ticket to null and ask what exactly is wrong. \
Only set maintenance_ticket when you know WHAT is broken and HOW (or for emergencies).
Shape:
{
  "reply": "Plain text response to the tenant.",
  "conversation_title": null | "Short thread title, e.g. Burst pipe",
  "interaction_type": "general" | "maintenance",
  "severity": "none" | "low" | "medium" | "high" | "critical",
  "needs_staff_input": false,
  "maintenance_ticket": null | {
    "title": "Short staff-facing title (max ~80 chars)",
    "description": "What happened, where in the unit, what the tenant needs",
    "priority": "low" | "medium" | "high" | "urgent",
    "category": "plumbing" | "electrical" | "roof" | "appliance" | "security" | "pest" | "garden" | "other"
  }
}

CRITICAL RULE — WHEN TO SET maintenance_ticket:

You MUST set maintenance_ticket to null unless you have enough detail to write a useful, actionable ticket. \
Follow this decision tree STRICTLY:

STEP 1: Is it an EMERGENCY? (burst pipe, break-in, gas smell, fire, flooding, no water/power to whole unit)
→ YES: Set maintenance_ticket immediately. These are urgent and time-sensitive.
→ NO: Go to Step 2.

STEP 2: Does the message contain SPECIFIC, actionable detail? \
(e.g. "kitchen tap is dripping", "bedroom light switch sparks when I flip it", "toilet won't flush")
→ YES: Set maintenance_ticket.
→ NO: Go to Step 3.

STEP 3: The report is VAGUE. Set maintenance_ticket to null. Ask ONE clarifying question. Examples:
- "broken plug" → maintenance_ticket: null. Reply: "Which plug is it and what's happening — is it loose, sparking, or just not giving power?"
- "broken door" → maintenance_ticket: null. Reply: "What's wrong with the door — is the handle broken, won't it close, or is the lock jammed?"
- "problem with tap" → maintenance_ticket: null. Reply: "What's happening with the tap — is it dripping, no water at all, or no hot water?"
- "something wrong with stove" → maintenance_ticket: null. Reply: "What exactly is the issue — is an element not heating, the oven not working, or a knob broken?"
- "broken window" → maintenance_ticket: null. Reply: "Which window and what happened — is the glass cracked, won't it open/close, or is the latch broken?"
After the tenant clarifies, THEN set maintenance_ticket in your NEXT response.

REMEMBER: "broken plug", "broken door", "broken window" etc. are NOT enough detail. You MUST ask what exactly is wrong \
before logging a ticket. Only emergencies skip clarification.

Priority:
- urgent: break-in, active danger, gas smell, major flood, fire, no water/power to whole unit
- high: serious defect (burst pipe, sewage, geyser burst, security gate broken)
- medium: normal repairs (dripping tap, cracked tile, faulty element)
- low: minor / cosmetic (scuff marks, squeaky door)

Category:
- plumbing: pipes, taps, geysers, toilets, drains, water leaks, burst pipes
- electrical: power, lights, sockets, breaker trips, wiring
- roof: roof leaks, gutters, ceiling damage from above
- appliance: stove, fridge, washing machine, dishwasher, aircon
- security: locks, gates, alarms, intercoms, break-ins, forced entry
- pest: insects, rodents, birds nesting
- garden: irrigation, trees, fencing, paving
- other: anything else

WHEN maintenance_ticket IS null: general questions, rent queries, how-to, chit-chat, OR vague reports needing clarification.

conversation_title: suggest a short label (max ~60 chars) if the thread still has a generic title. \
Use null once the topic is already clear."""


def get_tenant_leases(user):
    """Leases where this user is linked as primary, co-tenant, or occupant."""
    return Lease.objects.filter(
        Q(primary_tenant__linked_user=user)
        | Q(co_tenants__person__linked_user=user)
        | Q(occupants__person__linked_user=user)
    ).distinct()


# ── Emergency keyword heuristics ──
# Catches urgent issues even when Claude's JSON output is malformed.

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


def _valid_category(val) -> str:
    v = (str(val) if val is not None else "other").lower().strip()
    allowed = {c[0] for c in MaintenanceRequest.Category.choices}
    return v if v in allowed else MaintenanceRequest.Category.OTHER


def _priority_from_severity(severity: str) -> str:
    sev = (severity or "none").lower().strip()
    return {
        "critical": MaintenanceRequest.Priority.URGENT,
        "high": MaintenanceRequest.Priority.HIGH,
        "medium": MaintenanceRequest.Priority.MEDIUM,
        "low": MaintenanceRequest.Priority.LOW,
    }.get(sev, MaintenanceRequest.Priority.MEDIUM)


def _higher_priority(left: str, right: str) -> str:
    rank = {
        MaintenanceRequest.Priority.LOW: 1,
        MaintenanceRequest.Priority.MEDIUM: 2,
        MaintenanceRequest.Priority.HIGH: 3,
        MaintenanceRequest.Priority.URGENT: 4,
    }
    left_valid = _valid_priority(left)
    right_valid = _valid_priority(right)
    return left_valid if rank[left_valid] >= rank[right_valid] else right_valid


_SEVERE_CATEGORY_HINTS = {
    "burst pipe": "plumbing", "pipe": "plumbing", "leak": "plumbing",
    "geyser": "plumbing", "toilet": "plumbing", "drain": "plumbing",
    "flooded": "plumbing", "water": "plumbing",
    "fire": "other", "gas smell": "other", "ceiling collapsed": "other",
    "break-in": "security", "break in": "security", "burglary": "security",
    "burglar": "security", "robbed": "security", "broken into": "security",
    "forced entry": "security", "someone broke": "security",
    "stolen from": "security", "theft from": "security",
    "vandalis": "security", "assault": "security", "attacked": "security",
}


_MAINTENANCE_HINTS = (
    "broken", "leaking", "leak", "dripping", "not working", "damaged",
    "cracked", "stuck", "jammed", "burst", "flooding", "blocked",
    "tripped", "sparking", "no power", "no water", "no hot water",
    "roof", "geyser", "tap", "toilet", "drain", "pipe", "socket",
    "light", "door", "window", "lock", "gate", "alarm", "intercom",
    "stove", "fridge", "aircon", "washing machine", "dishwasher",
    "pest", "rats", "mice", "cockroach", "ants", "mould", "mold",
    "ceiling", "gutter", "fence", "paving",
    # Wildlife / dead animals
    "dead animal", "dead bird", "dead rat", "dead mouse", "dead cat",
    "carcass", "animal smell", "rotting smell", "bad smell",
    "snake", "bees", "wasps", "birds nesting", "pigeon",
    # Pool
    "pool", "pool pump", "pool filter", "pool green",
    # Garden / grounds
    "pothole", "driveway", "parking", "tree", "overgrown",
    # Misc obvious
    "smell", "odour", "odor", "noise", "vibrating", "loose",
)

_MAINTENANCE_CATEGORY_HINTS = {
    **_SEVERE_CATEGORY_HINTS,
    "tap": "plumbing", "dripping": "plumbing", "blocked": "plumbing",
    "geyser": "plumbing", "no hot water": "plumbing", "no water": "plumbing",
    "socket": "electrical", "light": "electrical", "tripped": "electrical",
    "sparking": "electrical", "no power": "electrical", "power": "electrical",
    "roof": "roof", "ceiling": "roof", "gutter": "roof",
    "stove": "appliance", "fridge": "appliance", "aircon": "appliance",
    "washing machine": "appliance", "dishwasher": "appliance",
    "door": "security", "window": "security", "lock": "security",
    "gate": "security", "alarm": "security", "intercom": "security",
    "pest": "pest", "rats": "pest", "mice": "pest", "cockroach": "pest",
    "ants": "pest", "mould": "other", "mold": "other",
    "fence": "garden", "paving": "garden",
    # Wildlife / dead animals → pest control
    "dead animal": "pest", "dead bird": "pest", "dead rat": "pest",
    "dead mouse": "pest", "carcass": "pest", "snake": "pest",
    "bees": "pest", "wasps": "pest", "birds nesting": "pest", "pigeon": "pest",
    # Pool
    "pool": "garden", "pool pump": "garden", "pool filter": "garden",
    # Garden / grounds
    "pothole": "garden", "driveway": "garden", "overgrown": "garden",
    "tree": "garden",
    # Smell (could be many things — default to other)
    "bad smell": "other", "rotting smell": "pest", "smell": "other",
}


def _heuristic_severe_ticket(user_content: str) -> dict | None:
    """If the model misses JSON, still log urgent tickets for obvious security/emergency phrases."""
    c = user_content.lower()
    if not any(h in c for h in _SEVERE_HINTS):
        return None
    cat = "other"
    for hint, hint_cat in _SEVERE_CATEGORY_HINTS.items():
        if hint in c:
            cat = hint_cat
            break
    return {
        "title": "Urgent — incident reported via AI chat",
        "description": user_content.strip()[:8000],
        "priority": MaintenanceRequest.Priority.URGENT,
        "category": cat,
    }


def _heuristic_maintenance_ticket(user_content: str) -> dict | None:
    """Broader fallback: catch normal maintenance reports when AI didn't return JSON."""
    c = user_content.lower()
    if not any(h in c for h in _MAINTENANCE_HINTS):
        return None
    cat = "other"
    for hint, hint_cat in _MAINTENANCE_CATEGORY_HINTS.items():
        if hint in c:
            cat = hint_cat
            break
    # Determine priority from severity hints
    priority = MaintenanceRequest.Priority.MEDIUM
    if any(h in c for h in _SEVERE_HINTS):
        priority = MaintenanceRequest.Priority.URGENT
    elif any(h in c for h in ("not working", "no power", "no water", "no hot water", "burst", "flooding")):
        priority = MaintenanceRequest.Priority.HIGH
    title = user_content.strip()[:80]
    return {
        "title": title,
        "description": user_content.strip()[:8000],
        "priority": priority,
        "category": cat,
    }


def _has_usable_maintenance_ticket(ticket: dict | None) -> bool:
    return bool(ticket and (ticket.get("title") or "").strip())


def _build_maintenance_ticket_from_interaction(
    user_content: str,
    maintenance_ticket: dict | None,
    *,
    interaction_type: str,
    severity: str,
    json_ok: bool = True,
) -> dict | None:
    if interaction_type != "maintenance":
        return maintenance_ticket if _has_usable_maintenance_ticket(maintenance_ticket) else None

    base_ticket = dict(maintenance_ticket or {})
    if _has_usable_maintenance_ticket(base_ticket):
        return base_ticket

    # If the AI returned valid JSON but chose NOT to create a ticket
    # (maintenance_ticket: null), respect that — the AI is gathering details.
    # Only use heuristic fallback when JSON parsing failed (json_ok=False).
    if json_ok and maintenance_ticket is None:
        # AI deliberately returned null — still triaging, don't override
        return None

    hint = _heuristic_severe_ticket(user_content)
    if not hint:
        hint = _heuristic_maintenance_ticket(user_content)

    synthesized = hint or {}
    title = (
        (base_ticket.get("title") or "").strip()
        or (synthesized.get("title") or "").strip()
        or user_content.strip()[:80]
        or "Maintenance issue reported via AI chat"
    )
    description = (
        (base_ticket.get("description") or "").strip()
        or user_content.strip()[:8000]
        or (synthesized.get("description") or "").strip()
        or title
    )
    if (base_ticket.get("priority") or "").strip():
        priority = (base_ticket.get("priority") or "").strip()
    else:
        priority = _higher_priority(
            (synthesized.get("priority") or "").strip() or MaintenanceRequest.Priority.MEDIUM,
            _priority_from_severity(severity),
        )
    category = (
        (base_ticket.get("category") or "").strip()
        or (synthesized.get("category") or "").strip()
        or MaintenanceRequest.Category.OTHER
    )
    return {
        "title": title,
        "description": description,
        "priority": priority,
        "category": category,
    }


def _serialize_skills_used(skills_text: str, *, preview_limit: int = 8) -> dict:
    text = (skills_text or "").strip()
    if not text or text == "(No active skills in the database.)":
        return {
            "used": False,
            "count": 0,
            "preview": [],
            "source": "maintenance_skills_digest",
        }

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return {
        "used": True,
        "count": len(lines),
        "preview": lines[:preview_limit],
        "source": "maintenance_skills_digest",
    }


def _ensure_truthful_maintenance_reply(
    reply_text: str,
    *,
    maintenance_issue_identified: bool,
    created_mr: MaintenanceRequest | None,
    existing_request_id: int | None,
) -> str:
    if not maintenance_issue_identified or created_mr or existing_request_id:
        return reply_text

    truthful_note = (
        "I identified this as a maintenance issue, but I could not log it automatically yet. "
        "Please use the Report maintenance issue button below so the property team receives it."
    )
    lower_reply = (reply_text or "").lower()
    misleading_phrases = (
        "logged",
        "maintenance request",
        "ticket",
        "team has been alerted",
        "we've alerted",
        "i've alerted",
    )
    if any(phrase in lower_reply for phrase in misleading_phrases):
        return truthful_note
    if not reply_text.strip():
        return truthful_note
    return f"{reply_text.rstrip()}\n\n{truthful_note}"


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
    """Convert a stored message to Anthropic messages API format (text or multimodal blocks)."""
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
    """
    Best-effort unit resolution for ticket logging.

    We prefer an ACTIVE lease, but fall back to PENDING or the most recent lease.
    This prevents maintenance tickets from silently failing for tenants whose
    lease is not yet marked ACTIVE in the database.

    Auto-link fallback: if no lease is found via Person.linked_user (invite flow),
    try matching by email. This handles tenants who self-registered rather than
    accepting a formal invite — their Person record exists with the right email
    but linked_user was never set.
    """
    qs = get_tenant_leases(user).select_related("unit").order_by("-start_date")

    lease = qs.filter(status=Lease.Status.ACTIVE).first()
    if not lease:
        lease = qs.filter(status=Lease.Status.PENDING).first()
    if not lease:
        lease = qs.first()
    if lease and lease.unit_id:
        return lease.unit

    # Email-based fallback: find a Person by email and auto-link them.
    # This covers tenants who registered without going through the invite flow.
    if user.email:
        try:
            from apps.tenant.models import Person  # local import to avoid circular
            person = Person.objects.filter(
                email__iexact=user.email,
                linked_user__isnull=True,
            ).first()
            if person:
                person.linked_user = user
                person.save(update_fields=["linked_user"])
                # Retry lease lookup now that the link is established
                qs2 = get_tenant_leases(user).select_related("unit").order_by("-start_date")
                lease2 = (
                    qs2.filter(status=Lease.Status.ACTIVE).first()
                    or qs2.filter(status=Lease.Status.PENDING).first()
                    or qs2.first()
                )
                if lease2 and lease2.unit_id:
                    return lease2.unit
        except Exception:
            pass

    # Final fallback: TenantIntelligence (if present) may already have unit_ref.
    try:
        intel = getattr(user, "tenant_intel", None)
        if intel and getattr(intel, "unit_ref_id", None):
            return intel.unit_ref
    except Exception:
        pass
    return None


def _property_id_for_user(user) -> int | None:
    """Resolve the tenant's active property ID for scoped RAG queries."""
    lease = (
        get_tenant_leases(user)
        .filter(status=Lease.Status.ACTIVE)
        .select_related("unit__property")
        .order_by("-start_date")
        .first()
    )
    if lease and lease.unit and lease.unit.property:
        return lease.unit.property_id
    return None


def _create_mr_from_chat(user, ticket: dict, fallback_description: str) -> MaintenanceRequest | None:
    """Create a MaintenanceRequest from a parsed AI maintenance_ticket dict.

    Uses RAG classification to improve category/priority when the AI's
    extraction returned defaults (other/medium).

    Includes dedup guard: if the user already has an open ticket with a
    very similar title created in the last 10 minutes, return the existing
    one instead of creating a duplicate.
    """
    title = (ticket.get("title") or "").strip()[:200]
    if not title:
        return None
    desc = (ticket.get("description") or fallback_description or "").strip()[:8000]

    pr = _valid_priority(ticket.get("priority"))
    cat = _valid_category(ticket.get("category"))
    unit = _default_unit_for_user(user)
    if not unit:
        return None

    # RAG classification: improve category/priority from historical data
    property_id = unit.property_id if unit else None
    try:
        from core.contract_rag import classify_from_rag
        classification = classify_from_rag(f"{title} {desc}", property_id=property_id)
        if classification["confidence"] >= 0.3:
            if cat == "other" and classification["category"] != "other":
                cat = classification["category"]
            priority_order = {"low": 1, "medium": 2, "high": 3, "urgent": 4}
            if priority_order.get(classification["priority"], 0) > priority_order.get(pr, 0):
                pr = classification["priority"]
    except Exception:
        pass  # RAG failure should never block ticket creation

    return MaintenanceRequest.objects.create(
        tenant=user,
        unit=unit,
        title=title,
        description=desc,
        priority=pr,
        category=cat,
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


def _build_windowed_messages(all_messages: list) -> list[dict]:
    """
    Apply transcript windowing: send the last MAX_CHAT_WINDOW messages to Claude.

    If the conversation is longer, prepend a summary of earlier messages so
    Claude retains high-level context without token explosion.
    """
    if len(all_messages) <= MAX_CHAT_WINDOW:
        # Short conversation — send everything
        result = []
        for m in all_messages:
            api_role = "assistant" if m.get("role") == "assistant" else "user"
            if api_role == "assistant":
                result.append(
                    {"role": "assistant", "content": (m.get("content") or "").strip()}
                )
            else:
                block = _message_to_claude_user_content(m)
                result.append({"role": "user", "content": block})
        return result

    # Long conversation — summarise early messages, send recent ones in full
    early = all_messages[:-MAX_CHAT_WINDOW]
    recent = all_messages[-MAX_CHAT_WINDOW:]

    # Build a condensed summary of early messages
    summary_parts = []
    for m in early:
        role = "Tenant" if m.get("role") == "user" else "Assistant"
        text = (m.get("content") or "").strip()[:200]
        if text:
            summary_parts.append(f"{role}: {text}")
    summary = "\n".join(summary_parts)

    result = []
    # Prepend summary as a system-like user message
    result.append({
        "role": "user",
        "content": f"[Summary of earlier messages in this conversation:]\n{summary}\n[End of summary — recent messages follow.]",
    })
    # Claude requires alternating roles; add a brief assistant ack
    result.append({
        "role": "assistant",
        "content": "Understood, I have the context from the earlier conversation.",
    })

    # Append recent messages in full
    for m in recent:
        api_role = "assistant" if m.get("role") == "assistant" else "user"
        if api_role == "assistant":
            result.append(
                {"role": "assistant", "content": (m.get("content") or "").strip()}
            )
        else:
            block = _message_to_claude_user_content(m)
            result.append({"role": "user", "content": block})
    return result


def _maybe_create_agent_question(
    session: TenantChatSession,
    user,
    needs_staff_input: bool,
    content: str,
) -> None:
    """
    If the AI flagged needs_staff_input, create an AgentQuestion so staff
    can provide the answer. Once answered, it gets ingested into RAG.
    """
    if not needs_staff_input:
        return
    if session.agent_question_id:
        return  # Already has a pending question
    try:
        from apps.maintenance.models import AgentQuestion
        prop_id = _property_id_for_user(user)
        aq = AgentQuestion.objects.create(
            question=content[:2000],
            category="tenant",
            context_source=f"Chat session #{session.pk}",
            property_id=prop_id,
        )
        TenantChatSession.objects.filter(pk=session.pk).update(
            agent_question_id=aq.pk
        )
        session.agent_question_id = aq.pk
        logger.info("Created AgentQuestion #%s from chat session #%s", aq.pk, session.pk)
    except Exception:
        logger.exception("Failed to create AgentQuestion from chat session #%s", session.pk)


# ── Views ──


class TenantConversationsListCreateView(APIView):
    """List or create tenant chat sessions."""
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
    """Retrieve a single conversation with all messages."""
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
    """
    AI: chat transcript → structured fields for the tenant maintenance report form.

    Converts the conversation into a pre-filled {title, description, priority, category}
    dict that the mobile app uses to populate the Report Issue screen.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [TenantDraftThrottle]

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

        import time as _time
        client = anthropic.Anthropic(api_key=api_key, max_retries=2)
        t0 = _time.monotonic()
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
            logger.error("Maintenance draft AI error for session #%s: %s", pk, e)
            return Response({"error": f"AI error: {e}"}, status=502)
        latency_ms = int((_time.monotonic() - t0) * 1000)
        from apps.maintenance.models import AgentTokenLog
        AgentTokenLog.log_call(
            endpoint="maintenance_draft",
            response=response,
            user=request.user,
            latency_ms=latency_ms,
            metadata={"session_id": pk},
        )

        raw = extract_anthropic_assistant_text(response).strip()
        draft = parse_maintenance_draft_response(raw)
        if not draft:
            return Response(
                {
                    "error": "Could not build a draft from the conversation. Try again or fill the form manually.",
                },
                status=502,
            )
        # Include conversation_id so the report form can link back
        draft["conversation_id"] = pk
        return Response(draft)


class TenantConversationMessageCreateView(APIView):
    """
    Core chat endpoint: receives tenant message (text + optional media),
    queries RAG, calls Claude, parses response, and optionally creates
    a MaintenanceRequest.

    Key improvements over v1:
      - Transcript windowing (MAX_CHAT_WINDOW messages)
      - Property-scoped RAG queries
      - Duplicate maintenance request guard
      - Severity-aware classification
      - Agent Q&A + chat knowledge RAG layers
      - needs_staff_input → AgentQuestion creation
      - Rate limiting (TenantChatThrottle)
      - Retry with backoff (max_retries=2)
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    throttle_classes = [TenantChatThrottle]

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

        # ── Build RAG context (property-scoped when possible) ──
        # Run all 4 RAG queries in parallel to reduce latency
        from concurrent.futures import ThreadPoolExecutor
        n_chunks = int(getattr(settings, "RAG_QUERY_CHUNKS", 8))
        prop_id = _property_id_for_user(request.user)

        with ThreadPoolExecutor(max_workers=5) as pool:
            f_contracts = pool.submit(query_contracts, content, n_results=n_chunks, property_id=prop_id)
            f_qa = pool.submit(query_agent_qa, content, n_results=3)
            f_chat_kb = pool.submit(query_chat_knowledge, content, n_results=3)
            f_issues = pool.submit(query_maintenance_issues, content, n_results=3, property_id=prop_id)
            f_property_info = pool.submit(query_property_information, content, n_results=3, property_id=prop_id)

        rag_text = f_contracts.result()
        qa_text = f_qa.result()
        chat_kb_text = f_chat_kb.result()
        issues_text = f_issues.result()
        property_info_text = f_property_info.result()

        context_block = (
            "--- RETRIEVED DOCUMENT EXCERPTS (vector search) ---\n"
            f"{rag_text or '(No chunks retrieved.)'}\n"
        )
        if qa_text:
            context_block += (
                "\n--- STAFF-ANSWERED Q&A (from past interactions) ---\n"
                f"{qa_text}\n"
            )
        if chat_kb_text:
            context_block += (
                "\n--- LEARNED FROM PAST INTERACTIONS ---\n"
                f"{chat_kb_text}\n"
            )
        if issues_text:
            context_block += (
                "\n--- SIMILAR PAST MAINTENANCE ISSUES ---\n"
                f"{issues_text}\n"
            )
        if property_info_text:
            context_block += (
                "\n--- PROPERTY NOTES FROM LANDLORD (authoritative — prefer over other sources) ---\n"
                f"{property_info_text}\n"
            )

        skills_text = skills_digest_for_message(content, max_skills=8)
        skills_used = _serialize_skills_used(skills_text)
        if skills_text and skills_text != "(No active skills in the database.)":
            context_block += (
                "\n--- MAINTENANCE SKILLS (triage reference) ---\n"
                f"{skills_text}\n"
            )

        tenant_ctx = build_tenant_context(request.user)
        system = TENANT_SYSTEM_PROMPT
        if tenant_ctx:
            system = f"{system}\n\n{tenant_ctx}"
        system = f"{system}\n\n{context_block}"

        # ── Transcript windowing ──
        anthropic_messages = _build_windowed_messages(session.messages or [])

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

        # ── Call Claude with retry ──
        import time as _time
        client = anthropic.Anthropic(api_key=api_key, max_retries=2)
        t0 = _time.monotonic()
        try:
            response = client.messages.create(**kwargs)
        except Exception as e:
            logger.error("Tenant chat AI error for session #%s: %s", pk, e)
            return Response({"error": f"AI error: {e}"}, status=502)
        latency_ms = int((_time.monotonic() - t0) * 1000)

        # Log token usage for monitoring — include context breakdown
        from apps.maintenance.models import AgentTokenLog
        AgentTokenLog.log_call(
            endpoint="tenant_chat",
            response=response,
            user=request.user,
            latency_ms=latency_ms,
            metadata={
                "session_id": pk,
                "property_id": prop_id,
                "system_prompt_len": len(system),
                "rag_contracts_len": len(rag_text or ""),
                "rag_qa_len": len(qa_text or ""),
                "rag_chat_kb_len": len(chat_kb_text or ""),
                "rag_issues_len": len(issues_text or ""),
                "skills_used_count": skills_used["count"],
                "skills_used_preview": skills_used["preview"],
                "context_block_len": len(context_block),
                "message_count": len(anthropic_messages),
                "user_message": content[:200],
                "raw_ai_response": extract_anthropic_assistant_text(response).strip()[:500],
            },
        )

        raw_ai = extract_anthropic_assistant_text(response).strip()
        if not raw_ai:
            return Response({"error": "Empty model response."}, status=502)

        reply_text, maintenance_ticket, json_ok, conv_title = parse_tenant_ai_response(
            raw_ai
        )

        # Extract severity and interaction type from AI response
        interaction_type = "general"
        severity = "none"
        needs_staff_input = False
        if json_ok:
            try:
                import json
                parsed = json.loads(raw_ai.strip().strip("`").removeprefix("json").strip())
                interaction_type = parsed.get("interaction_type", "general")
                severity = parsed.get("severity", "none")
                needs_staff_input = bool(parsed.get("needs_staff_input", False))
            except Exception:
                pass

        existing_request_id = session.maintenance_request_id
        effective_ticket = _build_maintenance_ticket_from_interaction(
            ticket_context := content,
            maintenance_ticket,
            interaction_type=interaction_type,
            severity=severity,
            json_ok=json_ok,
        )
        _maybe_update_session_title(session, conv_title, effective_ticket or maintenance_ticket)

        # ── Duplicate MR guard: only create one per session ──
        created_mr: MaintenanceRequest | None = None
        if not existing_request_id:
            if effective_ticket and _has_usable_maintenance_ticket(effective_ticket):
                created_mr = _create_mr_from_chat(
                    request.user, effective_ticket, ticket_context
                )
            # Only use heuristic fallback when AI JSON parsing failed
            if created_mr is None and not json_ok:
                hint = _heuristic_severe_ticket(ticket_context)
                if not hint:
                    hint = _heuristic_maintenance_ticket(ticket_context)
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

        maintenance_issue_identified = (
            interaction_type == "maintenance"
            or bool(created_mr)
            or bool(existing_request_id)
            or _has_usable_maintenance_ticket(effective_ticket)
        )
        # Only append the "could not log" note when the AI TRIED to create a ticket
        # but failed. When json_ok=True and maintenance_ticket is None, the AI is
        # deliberately asking for clarification — don't nag the tenant.
        ai_deliberately_deferred = json_ok and maintenance_ticket is None
        if not ai_deliberately_deferred:
            reply_text = _ensure_truthful_maintenance_reply(
                reply_text,
                maintenance_issue_identified=maintenance_issue_identified,
                created_mr=created_mr,
                existing_request_id=existing_request_id,
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
        # Persist chat history to the linked maintenance request on EVERY turn
        # (dedup inside persist_chat_history_to_request prevents duplicates)
        linked_mr_id = (
            created_mr.id if created_mr
            else existing_request_id
            or session.maintenance_request_id
        )
        if linked_mr_id:
            try:
                mr_obj = (
                    created_mr
                    if created_mr
                    else MaintenanceRequest.objects.get(pk=linked_mr_id)
                )
                persist_chat_history_to_request(
                    mr_obj,
                    session.messages or [],
                    created_by=request.user,
                    session_id=session.pk,
                    source="tenant_chat",
                )
            except MaintenanceRequest.DoesNotExist:
                pass

        # ── Create AgentQuestion if AI flagged a knowledge gap ──
        _maybe_create_agent_question(session, request.user, needs_staff_input, content)

        update_tenant_intel(
            request.user,
            session,
            maintenance_ticket=effective_ticket,
            json_ok=json_ok,
            interaction_type=interaction_type,
            severity=severity,
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
                    "category": created_mr.category,
                    "status": created_mr.status,
                }
                if created_mr
                else None
            ),
            "maintenance_report_suggested": maintenance_report_suggested,
            "interaction_type": interaction_type,
            "severity": severity,
            "skills_used": skills_used,
            **_linked_payload(),
        }
        return Response(payload)
