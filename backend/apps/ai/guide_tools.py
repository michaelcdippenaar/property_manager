"""
AI Guide tool definitions and portal-role allowlisting.

Each tool maps to a navigable action in the admin SPA.  The `PORTAL_TOOLS`
dict gates which tools are available per portal (agent / owner / supplier).
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Tool schemas (Anthropic format)
# ---------------------------------------------------------------------------

ALL_TOOLS: list[dict[str, Any]] = [
    {
        "name": "go_to_dashboard",
        "description": "Navigate the user to the main dashboard / home overview.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "create_property",
        "description": "Navigate to the Add Property form so the user can create a new property listing.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "list_properties",
        "description": "Navigate to the Properties list page.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "list_leases",
        "description": "Navigate to the Leases page where the user can view, draft, and sign lease agreements.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "view_maintenance",
        "description": "Navigate to the Maintenance Issues page.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "list_tenants",
        "description": "Navigate to the Tenants list page.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "list_payments",
        "description": "Navigate to the Payments / Reconciliation page.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "owner_list_properties",
        "description": "Navigate the owner to their My Properties page.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "owner_list_leases",
        "description": "Navigate the owner to their Leases overview.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "owner_go_to_dashboard",
        "description": "Navigate the owner to the Owner Dashboard.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]

# ---------------------------------------------------------------------------
# Tool → GuideAction mapping
# ---------------------------------------------------------------------------

# Each entry: tool_name → GuideAction-compatible dict (serialised directly to
# the frontend).
TOOL_ACTION_MAP: dict[str, dict[str, Any]] = {
    "go_to_dashboard": {
        "route": "/",
        "label": "Dashboard",
    },
    "create_property": {
        "route": "/properties",
        "elementSelector": '[data-guide="add-property"]',
        "label": "Add Property",
        "confirmationRequired": False,
    },
    "list_properties": {
        "route": "/properties",
        "label": "Properties",
    },
    "list_leases": {
        "route": "/leases",
        "label": "Leases",
    },
    "view_maintenance": {
        "route": "/maintenance/issues",
        "label": "Maintenance Issues",
        "elementSelector": '[data-guide="new-issue"]',
    },
    "list_tenants": {
        "route": "/tenants",
        "label": "Tenants",
    },
    "list_payments": {
        "route": "/payments",
        "label": "Payments",
    },
    "owner_list_properties": {
        "route": "/owner/properties",
        "label": "My Properties",
    },
    "owner_list_leases": {
        "route": "/owner/leases",
        "label": "My Leases",
    },
    "owner_go_to_dashboard": {
        "route": "/owner",
        "label": "Owner Dashboard",
    },
}

# ---------------------------------------------------------------------------
# Role-scoped allowlists
# ---------------------------------------------------------------------------

# Tool names available to each portal value.
PORTAL_TOOLS: dict[str, list[str]] = {
    "agent": [
        "go_to_dashboard",
        "create_property",
        "list_properties",
        "list_leases",
        "view_maintenance",
        "list_tenants",
        "list_payments",
    ],
    "owner": [
        "owner_go_to_dashboard",
        "owner_list_properties",
        "owner_list_leases",
    ],
    "supplier": [
        "go_to_dashboard",
        "view_maintenance",
    ],
}

_TOOL_BY_NAME: dict[str, dict[str, Any]] = {t["name"]: t for t in ALL_TOOLS}


def get_tools_for_portal(portal: str) -> list[dict[str, Any]]:
    """Return the Anthropic tool schemas allowed for *portal*."""
    allowed = PORTAL_TOOLS.get(portal, PORTAL_TOOLS["agent"])
    return [_TOOL_BY_NAME[name] for name in allowed if name in _TOOL_BY_NAME]


def is_tool_allowed(tool_name: str, portal: str) -> bool:
    """Return True if *tool_name* is in the allowlist for *portal*."""
    return tool_name in PORTAL_TOOLS.get(portal, [])
