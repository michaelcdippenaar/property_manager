"""
Audit helpers for MCP write tools.

Every mutation performed through an MCP tool must call write_audit() with a
before/after snapshot. This is the POPIA §17 processing log.
"""
from __future__ import annotations

import logging
from typing import Any

from .auth import VoltMcpContext

logger = logging.getLogger(__name__)


def write_audit(
    ctx: VoltMcpContext,
    operation: str,
    target_model: str,
    target_id: int | None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    tool_name: str = "",
) -> None:
    """Record one mutation to VaultWriteAudit. Never raises — audit must not
    block the actual write. Errors are logged and swallowed so the operation
    itself still succeeds for the owner.
    """
    try:
        from apps.the_volt.gateway.models import VaultWriteAudit
        VaultWriteAudit.objects.create(
            vault=ctx.vault_owner,
            api_key=ctx.api_key,
            operation=operation,
            target_model=target_model,
            target_id=target_id,
            before=before or {},
            after=after or {},
            client_info={
                "tool": tool_name,
                "api_key_prefix": ctx.api_key.api_key_prefix,
            },
        )
    except Exception:
        logger.exception(
            "VaultWriteAudit write failed: op=%s target=%s:%s", operation, target_model, target_id
        )
