"""
Lightweight rule-based updater for TenantIntelligence.

Called after every AI response is appended to a TenantChatSession.
No extra AI call — we rely on the structured JSON the Claude response
already provides (category, maintenance_ticket, etc.) plus simple
keyword extraction from the tenant's own messages.
"""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from apps.ai.models import TenantChatSession, TenantIntelligence
from apps.leases.models import Lease


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


def update_tenant_intel(
    user,
    session: TenantChatSession,
    *,
    maintenance_ticket: dict | None = None,
    json_ok: bool = True,
) -> TenantIntelligence:
    """
    Upsert TenantIntelligence for *user* after a new AI exchange in *session*.

    Parameters
    ----------
    user : User instance
    session : the TenantChatSession that was just updated
    maintenance_ticket : parsed ticket dict from the AI response (or None)
    json_ok : whether the AI response was valid JSON
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

    # ── Timestamp ──
    intel.last_chat_at = timezone.now()

    intel.save()
    return intel
