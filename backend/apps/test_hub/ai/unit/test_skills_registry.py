"""Unit tests for apps/ai/skills_registry.py."""
import pytest
from unittest.mock import patch, MagicMock


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# get_mcp_tools — pure function (no DB, no filesystem)
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_get_mcp_tools_returns_non_empty_list():
    """get_mcp_tools() must return at least one tool."""
    from apps.ai.skills_registry import get_mcp_tools
    tools = get_mcp_tools()
    assert isinstance(tools, list)
    assert len(tools) > 0


@pytest.mark.green
def test_get_mcp_tools_each_has_name_and_description():
    """Every MCP tool must have 'name' and 'description' keys."""
    from apps.ai.skills_registry import get_mcp_tools
    for tool in get_mcp_tools():
        assert "name" in tool, f"Tool missing 'name': {tool}"
        assert "description" in tool, f"Tool missing 'description': {tool}"


@pytest.mark.green
def test_get_mcp_tools_no_duplicate_names():
    """No two MCP tools should share the same name."""
    from apps.ai.skills_registry import get_mcp_tools
    names = [t["name"] for t in get_mcp_tools()]
    assert len(names) == len(set(names)), f"Duplicate MCP tool names: {names}"


@pytest.mark.green
def test_get_mcp_tools_each_has_id():
    """Every MCP tool must have an 'id' key."""
    from apps.ai.skills_registry import get_mcp_tools
    for tool in get_mcp_tools():
        assert "id" in tool, f"Tool missing 'id': {tool}"


@pytest.mark.green
def test_get_mcp_tools_each_has_category():
    """Every MCP tool must have a 'category' key."""
    from apps.ai.skills_registry import get_mcp_tools
    for tool in get_mcp_tools():
        assert "category" in tool, f"Tool missing 'category': {tool}"


# ---------------------------------------------------------------------------
# get_mcp_resources — pure function
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_get_mcp_resources_returns_non_empty_list():
    """get_mcp_resources() must return at least one resource."""
    from apps.ai.skills_registry import get_mcp_resources
    resources = get_mcp_resources()
    assert isinstance(resources, list)
    assert len(resources) > 0


@pytest.mark.green
def test_get_mcp_resources_each_has_uri_and_description():
    """Every MCP resource must have 'uri' and 'description' keys."""
    from apps.ai.skills_registry import get_mcp_resources
    for resource in get_mcp_resources():
        assert "uri" in resource, f"Resource missing 'uri': {resource}"
        assert "description" in resource, f"Resource missing 'description': {resource}"


# ---------------------------------------------------------------------------
# get_full_registry — depends on DB (maintenance skills) and filesystem (claude skills)
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_get_full_registry_structure():
    """get_full_registry() must return a dict with expected top-level keys."""
    from apps.ai.skills_registry import get_full_registry

    # Mock DB-dependent and filesystem-dependent parts
    with patch("apps.ai.skills_registry.get_claude_skills", return_value=[
        {"id": "s1", "name": "test-skill", "title": "Test", "description": "A skill", "category": "general", "source": "claude", "steps": 0, "references": [], "body": ""},
    ]):
        with patch("apps.ai.skills_registry.get_maintenance_skills", return_value=[]):
            registry = get_full_registry()

    assert "claude_skills" in registry
    assert "maintenance_skills" in registry
    assert "mcp_tools" in registry
    assert "mcp_resources" in registry
    assert "totals" in registry


@pytest.mark.green
def test_get_full_registry_totals_match_lists():
    """Totals in get_full_registry() must equal actual list lengths."""
    from apps.ai.skills_registry import get_full_registry

    with patch("apps.ai.skills_registry.get_claude_skills", return_value=[
        {"id": "s1", "name": "skill-a", "title": "A", "description": "x", "category": "general", "source": "claude", "steps": 0, "references": [], "body": ""},
        {"id": "s2", "name": "skill-b", "title": "B", "description": "y", "category": "lease", "source": "claude", "steps": 1, "references": [], "body": ""},
    ]):
        with patch("apps.ai.skills_registry.get_maintenance_skills", return_value=[]):
            registry = get_full_registry()

    assert registry["totals"]["claude_skills"] == len(registry["claude_skills"])
    assert registry["totals"]["maintenance_skills"] == len(registry["maintenance_skills"])
    assert registry["totals"]["mcp_tools"] == len(registry["mcp_tools"])
    assert registry["totals"]["mcp_resources"] == len(registry["mcp_resources"])


# ---------------------------------------------------------------------------
# get_claude_skills — filesystem-dependent, test graceful fallback
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_get_claude_skills_returns_empty_if_dir_missing():
    """get_claude_skills() returns [] when the skills directory does not exist."""
    from apps.ai.skills_registry import get_claude_skills
    with patch("apps.ai.skills_registry._SKILLS_DIR") as mock_dir:
        mock_dir.is_dir.return_value = False
        result = get_claude_skills()
    assert result == []


# ---------------------------------------------------------------------------
# _parse_skill_md — pure parser (no FS I/O if we mock path.read_text)
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_parse_skill_md_extracts_name_and_description():
    """_parse_skill_md extracts name and description from valid frontmatter."""
    from apps.ai.skills_registry import _parse_skill_md
    from pathlib import Path
    from unittest.mock import MagicMock

    mock_path = MagicMock(spec=Path)
    mock_path.read_text.return_value = (
        "---\n"
        "name: my-skill\n"
        "description: Does something useful\n"
        "---\n"
        "# My Skill Title\n\n"
        "### Step 1: Do this\n"
        "### Step 2: Then that\n"
    )
    mock_path.parent.__truediv__ = lambda self, other: MagicMock(is_dir=lambda: False)

    result = _parse_skill_md(mock_path)
    assert result is not None
    assert result["name"] == "my-skill"
    assert result["description"] == "Does something useful"
    assert result["steps"] == 2


@pytest.mark.green
def test_parse_skill_md_returns_none_without_name():
    """_parse_skill_md returns None if frontmatter has no 'name' key."""
    from apps.ai.skills_registry import _parse_skill_md
    from unittest.mock import MagicMock

    mock_path = MagicMock()
    mock_path.read_text.return_value = (
        "---\n"
        "description: No name here\n"
        "---\n"
        "# Body\n"
    )
    result = _parse_skill_md(mock_path)
    assert result is None


@pytest.mark.green
def test_parse_skill_md_security_category():
    """Security-related skill names should resolve to category 'security'."""
    from apps.ai.skills_registry import _parse_skill_md
    from unittest.mock import MagicMock

    mock_path = MagicMock()
    mock_path.read_text.return_value = (
        "---\n"
        "name: security-audit\n"
        "description: Audits security\n"
        "---\n"
        "# Security Audit\n"
    )
    mock_path.parent.__truediv__ = lambda self, other: MagicMock(is_dir=lambda: False)
    result = _parse_skill_md(mock_path)
    assert result["category"] == "security"


@pytest.mark.green
def test_parse_skill_md_lease_category():
    """Lease-related skill names should resolve to category 'lease'."""
    from apps.ai.skills_registry import _parse_skill_md
    from unittest.mock import MagicMock

    mock_path = MagicMock()
    mock_path.read_text.return_value = (
        "---\n"
        "name: lease-tiptap\n"
        "description: TipTap lease editor\n"
        "---\n"
        "# Lease TipTap\n"
    )
    mock_path.parent.__truediv__ = lambda self, other: MagicMock(is_dir=lambda: False)
    result = _parse_skill_md(mock_path)
    assert result["category"] == "lease"
