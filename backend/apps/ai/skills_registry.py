"""
AI Skills Registry — loads skill definitions from .claude/skills/ and the
MaintenanceSkill database, providing a unified catalogue for the dashboard.

Skills are categorised as:
  - claude: Claude Code skills from .claude/skills/ (lease, security, compliance)
  - maintenance: DB-backed skills from MaintenanceSkill model (plumbing, electrical, etc.)
  - mcp: MCP server tools (tenant, lease, maintenance, property, user, monitor)
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

# ── Claude Code skills directory ──────────────────────────────────────
_SKILLS_DIR = Path(settings.BASE_DIR).parent / ".claude" / "skills"


def _parse_skill_md(path: Path) -> dict | None:
    """Parse a SKILL.md file, extracting YAML frontmatter and body."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None

    # Split frontmatter (between --- markers)
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None

    frontmatter = parts[1].strip()
    body = parts[2].strip()

    # Parse simple YAML-like frontmatter
    meta: dict = {}
    current_key = None
    current_val_lines: list[str] = []

    for line in frontmatter.splitlines():
        m = re.match(r"^(\w+):\s*(.*)$", line)
        if m:
            # Save previous key
            if current_key:
                meta[current_key] = " ".join(current_val_lines).strip()
            current_key = m.group(1)
            current_val_lines = [m.group(2).lstrip(">").strip()]
        elif current_key and line.startswith("  "):
            current_val_lines.append(line.strip())

    if current_key:
        meta[current_key] = " ".join(current_val_lines).strip()

    if not meta.get("name"):
        return None

    # Extract first heading as title
    title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else meta["name"]

    # Determine category from name/description
    name = meta["name"]
    if any(kw in name for kw in ("security", "vulnerability", "auth", "compliance", "user-model", "api-security")):
        category = "security"
    elif any(kw in name for kw in ("lease", "rental", "format-lease", "parse-lease")):
        category = "lease"
    elif "docuseal" in name:
        category = "esigning"
    else:
        category = "general"

    # Count workflow steps
    steps = len(re.findall(r"^###\s+Step\s+\d+", body, re.MULTILINE))

    # Check for reference files
    refs_dir = path.parent / "references"
    references = []
    if refs_dir.is_dir():
        references = [f.name for f in refs_dir.iterdir() if f.is_file()]

    return {
        "id": name,
        "name": meta["name"],
        "title": title,
        "description": meta.get("description", ""),
        "category": category,
        "source": "claude",
        "steps": steps,
        "references": references,
        "body": body,
        "path": str(path.relative_to(Path(settings.BASE_DIR).parent)),
    }


def get_claude_skills() -> list[dict]:
    """Load all Claude Code skill definitions from .claude/skills/."""
    skills = []
    if not _SKILLS_DIR.is_dir():
        return skills

    for skill_dir in sorted(_SKILLS_DIR.iterdir()):
        skill_md = skill_dir / "SKILL.md"
        if skill_md.is_file():
            parsed = _parse_skill_md(skill_md)
            if parsed:
                skills.append(parsed)
    return skills


def get_maintenance_skills() -> list[dict]:
    """Load active maintenance skills from the database."""
    from apps.maintenance.models import MaintenanceSkill

    skills = []
    for s in MaintenanceSkill.objects.filter(is_active=True).order_by("trade", "name"):
        skills.append({
            "id": f"maint_{s.pk}",
            "name": s.name,
            "title": s.name,
            "description": f"{s.get_trade_display()} skill — {s.get_difficulty_display()} difficulty",
            "category": s.trade,
            "source": "maintenance",
            "difficulty": s.difficulty,
            "trade": s.trade,
            "symptom_phrases": s.symptom_phrases or [],
            "steps": s.steps or [],
            "notes": s.notes or "",
        })
    return skills


def get_mcp_tools() -> list[dict]:
    """Return the full MCP tool catalogue with descriptions."""
    return [
        {
            "id": "get_chat_session",
            "name": "get_chat_session",
            "category": "tenant",
            "description": "Fetch a single chat session with full message thread",
            "parameters": ["session_id"],
        },
        {
            "id": "list_tenant_chats",
            "name": "list_tenant_chats",
            "category": "tenant",
            "description": "List chat sessions for a tenant with optional maintenance request filter",
            "parameters": ["user_id", "maintenance_only"],
        },
        {
            "id": "get_tenant_context",
            "name": "get_tenant_context",
            "category": "tenant",
            "description": "Full intelligence profile: unit, property, complaint score, facts, recent chats",
            "parameters": ["user_id"],
        },
        {
            "id": "search_tenant_chats",
            "name": "search_tenant_chats",
            "category": "tenant",
            "description": "Keyword search across a tenant's chat message history",
            "parameters": ["user_id", "query"],
        },
        {
            "id": "list_property_chats",
            "name": "list_property_chats",
            "category": "tenant",
            "description": "All recent chat sessions from tenants at a property",
            "parameters": ["property_id", "limit"],
        },
        {
            "id": "list_lease_templates",
            "name": "list_lease_templates",
            "category": "lease",
            "description": "List all templates with id, name, version, field count",
            "parameters": [],
        },
        {
            "id": "get_lease_template",
            "name": "get_lease_template",
            "category": "lease",
            "description": "Full template details: HTML content, merge fields, header/footer",
            "parameters": ["template_id"],
        },
        {
            "id": "update_lease_template",
            "name": "update_lease_template",
            "category": "lease",
            "description": "Update template content, fields, or metadata",
            "parameters": ["template_id", "content_html", "fields_schema", "name"],
        },
        {
            "id": "create_lease_template",
            "name": "create_lease_template",
            "category": "lease",
            "description": "Create a new lease template",
            "parameters": ["name", "version", "province"],
        },
        {
            "id": "get_maintenance_chat",
            "name": "get_maintenance_chat",
            "category": "maintenance",
            "description": "Get activity/chat history for a maintenance request",
            "parameters": ["request_id", "limit"],
        },
        {
            "id": "post_maintenance_chat",
            "name": "post_maintenance_chat",
            "category": "maintenance",
            "description": "Post a message to a maintenance request chat thread",
            "parameters": ["request_id", "message", "activity_type"],
        },
        {
            "id": "list_maintenance_requests",
            "name": "list_maintenance_requests",
            "category": "maintenance",
            "description": "List maintenance requests with status, category, priority filters",
            "parameters": ["status", "category", "priority", "property_id", "limit"],
        },
        {
            "id": "get_maintenance_request",
            "name": "get_maintenance_request",
            "category": "maintenance",
            "description": "Full details of a maintenance request including unit, tenant, supplier",
            "parameters": ["request_id"],
        },
        {
            "id": "search_maintenance_issues",
            "name": "search_maintenance_issues",
            "category": "maintenance",
            "description": "Full-text search across maintenance request titles and descriptions",
            "parameters": ["query", "status", "category", "priority", "property_id"],
        },
        {
            "id": "find_similar_issues",
            "name": "find_similar_issues",
            "category": "maintenance",
            "description": "RAG vector search for similar past maintenance issues",
            "parameters": ["query", "property_id", "category", "n_results"],
        },
        {
            "id": "get_property",
            "name": "get_property",
            "category": "property",
            "description": "Property details with units, tenants (via active leases), and unit items",
            "parameters": ["property_id"],
        },
        {
            "id": "list_properties",
            "name": "list_properties",
            "category": "property",
            "description": "List all properties with pagination",
            "parameters": ["limit", "offset"],
        },
        {
            "id": "get_user",
            "name": "get_user",
            "category": "user",
            "description": "User profile with role-specific data (tenant: requests, intel)",
            "parameters": ["user_id"],
        },
        {
            "id": "list_users",
            "name": "list_users",
            "category": "user",
            "description": "List users with optional role filter",
            "parameters": ["role", "limit"],
        },
        {
            "id": "get_maintenance_stats",
            "name": "get_maintenance_stats",
            "category": "monitor",
            "description": "Issue counts by status, category, priority (property-scoped or global)",
            "parameters": ["property_id"],
        },
        {
            "id": "agent_monitor_dashboard",
            "name": "agent_monitor_dashboard",
            "category": "monitor",
            "description": "Full AI ecosystem dashboard: RAG stats, MCP, skills, tokens",
            "parameters": [],
        },
        {
            "id": "agent_health_check",
            "name": "agent_health_check",
            "category": "monitor",
            "description": "Run diagnostic probes across the AI ecosystem",
            "parameters": [],
        },
        {
            "id": "get_token_usage_report",
            "name": "get_token_usage_report",
            "category": "monitor",
            "description": "Token usage analytics with per-endpoint breakdown",
            "parameters": ["days"],
        },
    ]


def get_mcp_resources() -> list[dict]:
    """Return MCP resource definitions."""
    return [
        {"uri": "tenant://chats/{user_id}", "description": "All chat sessions for a tenant"},
        {"uri": "tenant://chats/{user_id}/latest", "description": "Most recent 5 chat sessions"},
        {"uri": "tenant://intel/{user_id}", "description": "Intelligence profile for a tenant"},
        {"uri": "tenant://property/{property_id}/chats", "description": "All chats at a property"},
        {"uri": "template://lease/{template_id}", "description": "Full lease template content"},
        {"uri": "monitor://dashboard", "description": "AI ecosystem monitoring dashboard"},
    ]


def get_full_registry() -> dict:
    """Return the complete skills and tools registry."""
    claude_skills = get_claude_skills()
    maint_skills = get_maintenance_skills()
    mcp_tools = get_mcp_tools()
    mcp_resources = get_mcp_resources()

    return {
        "claude_skills": claude_skills,
        "maintenance_skills": maint_skills,
        "mcp_tools": mcp_tools,
        "mcp_resources": mcp_resources,
        "totals": {
            "claude_skills": len(claude_skills),
            "maintenance_skills": len(maint_skills),
            "mcp_tools": len(mcp_tools),
            "mcp_resources": len(mcp_resources),
        },
    }
