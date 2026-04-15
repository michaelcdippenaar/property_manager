"""
Run the Volt MCP server over streamable HTTP.

Usage:

    python manage.py volt_mcp_http                     # 127.0.0.1:8765/mcp/
    python manage.py volt_mcp_http --host 0.0.0.0      # bind all interfaces
    python manage.py volt_mcp_http --port 9000
    python manage.py volt_mcp_http --path /api/volt-mcp/

Auth: clients send 'Authorization: Bearer volt_owner_<rest>' on every request.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run the Volt owner MCP server over streamable HTTP."

    def add_arguments(self, parser):
        parser.add_argument("--host", default="127.0.0.1")
        parser.add_argument("--port", type=int, default=8765)
        parser.add_argument("--path", default="/mcp/")

    def handle(self, *args, **opts):
        # Import here so Django is already bootstrapped by the management cmd
        from apps.the_volt.mcp.http_server import mcp

        host = opts["host"]
        port = opts["port"]
        path = opts["path"]

        self.stdout.write(self.style.SUCCESS(
            f"Volt MCP (HTTP) listening on http://{host}:{port}{path}"
        ))
        self.stdout.write(
            "Auth: send 'Authorization: Bearer volt_owner_…' with every request.\n"
            "Local claude.ai connector? Tunnel with: "
            f"cloudflared tunnel --url http://{host}:{port}\n"
        )

        mcp.run(
            transport="streamable-http",
            host=host,
            port=port,
            path=path,
            stateless_http=True,
        )
