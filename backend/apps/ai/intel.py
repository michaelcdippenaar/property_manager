"""
Lightweight rule-based updater for TenantIntelligence.

Called after every AI response is appended to a TenantChatSession.
No extra AI call — we rely on the structured JSON the Claude response
already provides (category, maintenance_ticket, severity, interaction_type)
plus simple keyword extraction from the tenant's own messages.

Features:
  - Property/unit resolution from active lease
  - Total chats & messages counting
  - Question category tracking (maintenance_ticket vs general_enquiry)
  - Complaint score calculation (ratio of maintenance to total)
  - Severity tracking (stores highest severity seen)
  - Fact extraction from tenant messages (contact preferences, known issues, etc.)
"""

from __future__ import annotations

import logging
import re

from django.db.models import Q
from django.utils import timezone

from apps.ai.models import TenantChatSession, TenantIntelligence
from apps.leases.models import Lease

logger = logging.getLogger(__name__)

# ── Severity ranking for tracking worst-case ──
_SEVERITY_RANK = {
    "none": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

# ── Fact extraction patterns ──
# Simple keyword-based extraction from tenant messages.
# Each pattern maps to a fact key and a regex to extract the value.
_FACT_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    # Contact preference
    ("contact_preference", "whatsapp", re.compile(r"\b(prefer|use|contact\s+me\s+on|via)\s+whatsapp\b", re.I)),
    ("contact_preference", "email", re.compile(r"\b(prefer|use|contact\s+me\s+on|via)\s+email\b", re.I)),
    ("contact_preference", "phone", re.compile(r"\b(prefer|call|phone)\s+me\b", re.I)),
    # Pets
    ("has_pets", "true", re.compile(r"\b(my\s+(dog|cat|pet)|i\s+have\s+a?\s*(dog|cat|pet))\b", re.I)),
    # Parking
    ("has_vehicle", "true", re.compile(r"\b(my\s+(car|vehicle|bike)|i\s+park|parking\s+bay)\b", re.I)),
    # Work-from-home
    ("works_from_home", "true", re.compile(r"\b(work\s+from\s+home|wfh|home\s+office)\b", re.I)),
    # Known recurring issues
    ("recurring_issue", "water_pressure", re.compile(r"\b(low\s+water\s+pressure|water\s+pressure\s+(is\s+)?low)\b", re.I)),
    ("recurring_issue", "load_shedding", re.compile(r"\b(load\s*shedding|power\s+cuts?|no\s+electricity)\b", re.I)),
]


def _resolve_property_and_unit(user):
    """Best-effort: active lease → (property, unit) for the user."""
    lease = (
        Lease.objects.filter(
            Q(primary_tenant__linked_user=user)
            | Q(co_tenants__person__linked_user=user)
            | Q(occupants__person__linked_user=user),
            status=Lease.Status.ACTIVE,
        )
        .select_related("unit__property")
        .order_by("-start_date")
        .first()
    )
    if lease and lease.unit:
        return lease.unit.property, lease.unit
    return None, None


def _classify_category(
    maintenance_ticket: dict | None,
    json_ok: bool,
) -> str:
    """Return a simple category string for the question_categories counter."""
    if json_ok and maintenance_ticket and (maintenance_ticket.get("title") or "").strip():
        return "maintenance_ticket"
    return "general_enquiry"


def _extract_facts(messages: list) -> dict:
    """
    Extract key-value facts from tenant messages using pattern matching.

    Returns a dict of discovered facts, e.g.:
        {"contact_preference": "whatsapp", "has_pets": "true"}

    Only processes the last 10 user messages to keep it fast.
    """
    facts: dict = {}
    user_msgs = [
        m for m in (messages or [])
        if m.get("role") == "user"
    ][-10:]  # Last 10 user messages only

    for msg in user_msgs:
        text = msg.get("content") or ""
        for fact_key, fact_value, pattern in _FACT_PATTERNS:
            if pattern.search(text):
                facts[fact_key] = fact_value

    return facts


def update_tenant_intel(
    user,
    session: TenantChatSession,
    *,
    maintenance_ticket: dict | None = None,
    json_ok: bool = True,
    interaction_type: str = "general",
    severity: str = "none",
) -> TenantIntelligence:
    """
    Upsert TenantIntelligence for *user* after a new AI exchange in *session*.

    Parameters
    ----------
    user : User instance
    session : the TenantChatSession that was just updated
    maintenance_ticket : parsed ticket dict from the AI response (or None)
    json_ok : whether the AI response was valid JSON
    interaction_type : "general" or "maintenance" (from AI classification)
    severity : "none", "low", "medium", "high", or "critical"
    """
    intel, _created = TenantIntelligence.objects.get_or_create(user=user)

    # ── Property / unit (set once, refresh if missing) ──
    if not intel.property_ref or not intel.unit_ref:
        prop, unit = _resolve_property_and_unit(user)
        if prop:
            intel.property_ref = prop
        if unit:
            intel.unit_ref = unit

    # ── Counts ──
    all_sessions = TenantChatSession.objects.filter(user=user)
    intel.total_chats = all_sessions.count()
    intel.total_messages = sum(
        len(s.messages or []) for s in all_sessions.only("messages")
    )

    # ── Question category ──
    cat = _classify_category(maintenance_ticket, json_ok)
    cats = dict(intel.question_categories or {})
    cats[cat] = cats.get(cat, 0) + 1
    intel.question_categories = cats

    # ── Complaint score (ratio of maintenance chats to total) ──
    maintenance_count = cats.get("maintenance_ticket", 0)
    total_interactions = sum(cats.values()) or 1
    intel.complaint_score = round(maintenance_count / total_interactions, 3)

    # ── Facts extraction from tenant messages ──
    try:
        new_facts = _extract_facts(session.messages)
        if new_facts:
            existing_facts = dict(intel.facts or {})
            existing_facts.update(new_facts)
            # Track interaction type and severity in facts
            if interaction_type != "general":
                existing_facts["last_interaction_type"] = interaction_type
            if severity not in ("none", ""):
                # Keep track of highest severity seen
                current_max = existing_facts.get("max_severity", "none")
                if _SEVERITY_RANK.get(severity, 0) > _SEVERITY_RANK.get(current_max, 0):
                    existing_facts["max_severity"] = severity
                existing_facts["last_severity"] = severity
            intel.facts = existing_facts
    except Exception:
        logger.exception("Fact extraction failed for user %s", user.pk)

    # Always track severity even if no pattern-based facts extracted
    if severity not in ("none", ""):
        existing_facts = dict(intel.facts or {})
        current_max = existing_facts.get("max_severity", "none")
        if _SEVERITY_RANK.get(severity, 0) > _SEVERITY_RANK.get(current_max, 0):
            existing_facts["max_severity"] = severity
        existing_facts["last_severity"] = severity
        existing_facts["last_interaction_type"] = interaction_type
        intel.facts = existing_facts

    # ── Timestamp ──
    intel.last_chat_at = timezone.now()

    intel.save()
    return intel
