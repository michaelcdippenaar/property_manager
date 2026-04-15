"""
Volt MCP — owner-facing MCP server for The Volt.

Exposes read + write tools for a single vault owner, authenticated via
a per-owner API key (VaultOwnerAPIKey). Run as a stdio MCP server for
Claude Desktop / Claude Code / local agents.

Entry point: apps/the_volt/mcp/server.py
"""
