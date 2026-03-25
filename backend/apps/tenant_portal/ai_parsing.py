"""Pure parsing helpers for tenant AI JSON (unit-tested, no Django requests)."""

from __future__ import annotations

import json
import re

# Mobile report form categories (must match Flutter ReportIssueScreen).
MAINTENANCE_DRAFT_CATEGORIES = frozenset(
    {"plumbing", "electrical", "roof", "appliance", "security", "pest", "garden", "other"}
)
MAINTENANCE_DRAFT_PRIORITIES = frozenset({"low", "medium", "high", "urgent"})

MAINTENANCE_DRAFT_SYSTEM_PROMPT = """You convert a Tremly tenant↔AI support chat (South African residential rentals) into \
one structured maintenance report for the tenant app form.

Return **ONLY** valid JSON (no markdown code fences, no commentary). Shape:
{
  "title": "Short actionable title for staff, max ~80 chars",
  "description": "Full detail for maintenance staff from the whole conversation — what broke, where in the unit, urgency, access notes",
  "priority": "low" | "medium" | "high" | "urgent",
  "category": "plumbing" | "electrical" | "roof" | "appliance" | "security" | "pest" | "garden" | "other"
}

**priority**
- **urgent**: break-in / burglary / safety / gas smell / major flood or fire risk / no water or power to whole unit
- **high**: serious defect affecting habitability but not immediate danger
- **medium**: normal repairs (default when unsure)
- **low**: minor or cosmetic

**category**: best single fit; use **other** if unclear.

The conversation already reflects a maintenance-related issue — produce the best possible structured report even if some details are vague."""


def strip_json_fence(raw: str) -> str:
    cleaned = (raw or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned).strip()
    return cleaned


def parse_tenant_ai_response(raw: str) -> tuple[str, dict | None, bool, str | None]:
    """Parse assistant JSON for normal tenant chat. Returns (reply, maintenance_ticket|None, json_ok, conversation_title|None)."""
    cleaned = strip_json_fence(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return (raw or "").strip(), None, False, None
    reply = data.get("reply")
    if not isinstance(reply, str) or not reply.strip():
        reply = raw
    mt = data.get("maintenance_ticket")
    if mt is not None and not isinstance(mt, dict):
        mt = None
    ct = data.get("conversation_title")
    if isinstance(ct, str):
        ct = ct.strip()[:200] or None
    else:
        ct = None
    return reply.strip(), mt, True, ct


def parse_maintenance_draft_response(raw: str) -> dict | None:
    """Parse model output into {title, description, priority, category} or None."""
    cleaned = strip_json_fence(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    title = str(data.get("title") or "").strip()[:200]
    if not title:
        return None
    desc = str(data.get("description") or "").strip()[:8000]
    pr = str(data.get("priority") or "medium").lower().strip()
    if pr not in MAINTENANCE_DRAFT_PRIORITIES:
        pr = "medium"
    cat = str(data.get("category") or "other").lower().strip()
    if cat not in MAINTENANCE_DRAFT_CATEGORIES:
        cat = "other"
    return {
        "title": title,
        "description": desc,
        "priority": pr,
        "category": cat,
    }
