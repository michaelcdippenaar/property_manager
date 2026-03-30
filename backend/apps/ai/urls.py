from django.urls import path

from apps.ai.views import (
    ClaudeSkillDetailView,
    MCPToolDetailView,
    MaintenanceSkillDetailView,
    SkillsRegistryView,
)

urlpatterns = [
    path("registry/", SkillsRegistryView.as_view(), name="ai-skills-registry"),
    path("skills/claude/<str:skill_id>/", ClaudeSkillDetailView.as_view(), name="ai-claude-skill-detail"),
    path("skills/maintenance/<int:pk>/", MaintenanceSkillDetailView.as_view(), name="ai-maintenance-skill-detail"),
    path("tools/mcp/<str:tool_id>/", MCPToolDetailView.as_view(), name="ai-mcp-tool-detail"),
]
