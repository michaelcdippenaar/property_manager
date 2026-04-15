#!/usr/bin/env python
"""
Volt Owner MCP — streamable HTTP server.

Same tool set as the stdio variant (apps.the_volt.mcp.server), but exposed
over HTTP so it can be used as a claude.ai custom connector or hosted at
https://backend.klikk.co.za/mcp/ behind a reverse proxy.

Run locally:

    cd backend
    DJANGO_SETTINGS_MODULE=config.settings.local \\
    ./.venv/bin/python -m apps.the_volt.mcp.http_server --port 8765

Or via management command:

    ./.venv/bin/python manage.py volt_mcp_http --port 8765 --host 0.0.0.0

Auth: every request must carry a bearer token —

    Authorization: Bearer volt_owner_<rest>

See apps/the_volt/mcp/README.md for tunnel setup (cloudflared / ngrok) and
staging reverse proxy notes.
"""
from __future__ import annotations

import argparse
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
        "The Volt — owner's personal data sovereignty vault. "
        "Authenticate each request with 'Authorization: Bearer volt_owner_…'. "
        "All tools are scoped to the owner resolved from that token. "
        "SA entity types: personal, trust, company, close_corporation, "
        "sole_proprietary, asset. All writes encrypted at rest and audited."
    ),
)

read_tools.register(mcp)
write_tools.register(mcp)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run the Volt MCP HTTP server")
    p.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    p.add_argument("--port", type=int, default=8765, help="Bind port (default: 8765)")
    p.add_argument(
        "--path",
        default="/mcp/",
        help="URL path to mount the MCP endpoint at (default: /mcp/)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    mcp.run(
        transport="streamable-http",
        host=args.host,
        port=args.port,
        path=args.path,
        stateless_http=True,
    )


if __name__ == "__main__":
    main()
