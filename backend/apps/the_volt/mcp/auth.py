"""
MCP auth — resolve the calling vault owner from a raw API key.

The MCP server is a long-lived stdio process spawned by a client (Claude
Desktop). The client passes the owner's API key via the VOLT_OWNER_API_KEY
env var at spawn time. Every tool call resolves that key to a VaultOwner +
VaultOwnerAPIKey pair — failure raises McpAuthError which the tool layer
turns into a structured MCP error response.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class McpAuthError(Exception):
    """Raised when the MCP caller can't be resolved to a valid vault owner."""


@dataclass(frozen=True)
class VoltMcpContext:
    """Everything a tool needs to operate safely within one owner's vault."""

    vault_owner: object  # VaultOwner — avoid circular import at module load
    api_key: object      # VaultOwnerAPIKey

    @property
    def vault_id(self) -> int:
        return self.vault_owner.pk

    @property
    def user_email(self) -> str:
        return self.vault_owner.user.email


_ENV_VAR = "VOLT_OWNER_API_KEY"


def _resolve_raw_key(raw: str) -> VoltMcpContext:
    """Turn a raw API key string into a VoltMcpContext. Raises McpAuthError on failure."""
    from apps.the_volt.owners.models import VaultOwnerAPIKey

    key = VaultOwnerAPIKey.resolve(raw)
    if key is None:
        raise McpAuthError(
            "Invalid or revoked Volt owner API key. Generate a fresh one via "
            "/admin/the_volt/vaultownerapikey/ or the VaultOwner dashboard."
        )
    key.touch()
    return VoltMcpContext(vault_owner=key.vault_owner, api_key=key)


def _try_http_header_auth() -> VoltMcpContext | None:
    """Read the Authorization header from the current HTTP request, if any.

    Returns None if we're not in an HTTP request context (e.g. stdio mode).
    Raises McpAuthError if the header is present but invalid.
    """
    try:
        from fastmcp.server.dependencies import get_http_headers
        headers = get_http_headers()
    except Exception:
        return None

    if not headers:
        return None

    # Log header keys (not values) to diagnose what claude.ai actually sends
    safe_keys = [k for k in headers.keys()]
    logger.debug("Volt MCP incoming headers: %s", safe_keys)

    # Check common auth header variants (claude.ai connector may use different names)
    raw = None
    auth = headers.get("authorization") or headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        raw = auth[7:].strip()
    elif auth:
        # Could be a raw key without Bearer prefix
        raw = auth.strip()
    else:
        # Try alternative header names some connectors use
        for alt in ("x-api-key", "x-volt-api-key", "api-key"):
            val = headers.get(alt, "")
            if val:
                raw = val.strip()
                logger.debug("Volt MCP: found key in header '%s'", alt)
                break

    if not raw:
        logger.warning(
            "Volt MCP: HTTP request with no recognisable auth header. Keys seen: %s",
            safe_keys,
        )
        raise McpAuthError(
            "Missing Authorization header. Send 'Authorization: Bearer volt_owner_…' "
            f"(headers seen: {safe_keys})"
        )

    return _resolve_raw_key(raw)


def _try_env_auth() -> VoltMcpContext | None:
    """Read VOLT_OWNER_API_KEY from env (stdio transport path)."""
    raw = os.environ.get(_ENV_VAR, "").strip()
    if not raw:
        return None
    return _resolve_raw_key(raw)


# Stdio mode: one owner per process — cache. HTTP mode: cannot cache (different
# owners per request), so never fill this in the HTTP path.
_cached_stdio_context: VoltMcpContext | None = None


def get_context() -> VoltMcpContext:
    """Resolve the calling vault owner. HTTP first, then env fallback.

    HTTP transport: reads 'Authorization: Bearer …' on every call.
    Stdio transport: reads VOLT_OWNER_API_KEY env var once per process.
    """
    # Try HTTP first — this path is per-request so we must re-resolve each call
    http_ctx = _try_http_header_auth()
    if http_ctx is not None:
        return http_ctx

    # Stdio fallback — cache after first successful resolution
    global _cached_stdio_context
    if _cached_stdio_context is None:
        env_ctx = _try_env_auth()
        if env_ctx is None:
            raise McpAuthError(
                f"No credentials found. Set '{_ENV_VAR}' env var (stdio) or send "
                "'Authorization: Bearer volt_owner_…' header (HTTP)."
            )
        _cached_stdio_context = env_ctx
    return _cached_stdio_context
