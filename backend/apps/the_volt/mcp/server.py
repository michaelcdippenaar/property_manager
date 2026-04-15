#!/usr/bin/env python
"""
Volt Owner MCP — stdio server for Claude Desktop / Claude Code.

Launch (from the backend dir, venv active):

    VOLT_OWNER_API_KEY=volt_owner_xxx… \\
    DJANGO_SETTINGS_MODULE=config.settings.local \\
    python -m apps.the_volt.mcp.server

Or register in Claude Desktop config (~/Library/Application Support/Claude/claude_desktop_config.json):

    {
      "mcpServers": {
        "volt": {
          "command": "/absolute/path/to/.venv/bin/python",
          "args": ["-m", "apps.the_volt.mcp.server"],
          "cwd": "/absolute/path/to/backend",
          "env": {
            "VOLT_OWNER_API_KEY": "volt_owner_…",
            "DJANGO_SETTINGS_MODULE": "config.settings.local"
          }
        }
      }
    }

See apps/the_volt/mcp/README.md for full setup.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# ── Bootstrap Django before importing models ──
_backend = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_backend))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django  # noqa: E402

django.setup()

from fastmcp import FastMCP  # noqa: E402

from apps.the_volt.mcp.tools import read as read_tools  # noqa: E402
from apps.the_volt.mcp.tools import write as write_tools  # noqa: E402

mcp = FastMCP(
    name="volt-owner",
    instructions=(
        "The Volt — the owner's personal data sovereignty vault. "
        "Expose read + write tools scoped to a single vault owner via the "
        "VOLT_OWNER_API_KEY env var. Supports South African entity types: "
        "personal, trust, company, close_corporation, sole_proprietary, asset. "
        "All writes encrypted at rest and audited to VaultWriteAudit. "
        "Use ensure_vault first to confirm the session owner. Then upsert_owner, "
        "upsert_property, upsert_tenant, link_entities, attach_document to "
        "populate. Use list_entities, find_entity, get_entity, list_documents "
        "to query."
    ),
)

read_tools.register(mcp)
write_tools.register(mcp)


def main() -> None:
    # FastMCP defaults to stdio transport
    mcp.run()


if __name__ == "__main__":
    main()
