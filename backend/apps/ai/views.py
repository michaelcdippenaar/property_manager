"""
AI Skills & Tools API views.

Provides endpoints for the Agent Monitor dashboard to list and inspect
Claude skills, maintenance skills, and MCP tools.
"""
from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.skills_registry import (
    get_claude_skills,
    get_full_registry,
    get_maintenance_skills,
    get_mcp_tools,
    get_mcp_resources,
)
from apps.maintenance.agent_assist_views import IsAgentOrAdmin


class SkillsRegistryView(APIView):
    """Full skills and tools registry for the dashboard, including usage counts."""
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]

    def get(self, request):
        data = get_full_registry()

        # Add usage counts from AgentTokenLog
        from datetime import timedelta
        from django.db.models import Count
        from django.utils import timezone
        from apps.maintenance.models import AgentTokenLog

        since = timezone.now() - timedelta(days=30)
        usage = dict(
            AgentTokenLog.objects.filter(created_at__gte=since)
            .values_list("endpoint")
            .annotate(c=Count("id"))
        )

        # Map endpoints to agent types for display
        endpoint_map = {
            "tenant_chat": "Tenant AI Chat",
            "agent_assist": "Agent Assist",
            "maintenance_chat_agent": "Maintenance @agent",
            "maintenance_draft": "Maintenance Draft",
            "lease_builder": "Lease Builder",
        }

        data["endpoint_usage"] = {
            k: {"label": v, "calls_30d": usage.get(k, 0)}
            for k, v in endpoint_map.items()
        }
        data["total_ai_calls_30d"] = sum(usage.values())

        return Response(data)


class ClaudeSkillDetailView(APIView):
    """Detail view for a single Claude Code skill."""
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]

    def get(self, request, skill_id):
        for skill in get_claude_skills():
            if skill["id"] == skill_id:
                return Response(skill)
        return Response({"error": "Skill not found"}, status=404)


class MaintenanceSkillDetailView(APIView):
    """Detail view for a single maintenance skill.

    Phase 2.7: scope to global skills (agency=None) plus the caller's own
    agency. ADMIN/superuser bypass and see all rows. Mirrors the
    MaintenanceSkillViewSet pattern from Phase 2.5.
    """
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]

    def get(self, request, pk):
        from apps.maintenance.models import MaintenanceSkill
        from django.db.models import Q
        from apps.accounts.scoping import _is_admin

        qs = MaintenanceSkill.objects.filter(pk=pk, is_active=True)
        if not _is_admin(request.user):
            agency_id = getattr(request.user, "agency_id", None)
            qs = qs.filter(Q(agency__isnull=True) | Q(agency_id=agency_id))
        try:
            s = qs.get()
        except MaintenanceSkill.DoesNotExist:
            return Response({"error": "Skill not found"}, status=404)

        return Response({
            "id": s.pk,
            "name": s.name,
            "trade": s.trade,
            "trade_display": s.get_trade_display(),
            "difficulty": s.difficulty,
            "difficulty_display": s.get_difficulty_display(),
            "symptom_phrases": s.symptom_phrases or [],
            "steps": s.steps or [],
            "notes": s.notes or "",
            "is_active": s.is_active,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        })


class MCPToolDetailView(APIView):
    """Detail view for a single MCP tool."""
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]

    def get(self, request, tool_id):
        for tool in get_mcp_tools():
            if tool["id"] == tool_id:
                return Response(tool)
        return Response({"error": "Tool not found"}, status=404)
