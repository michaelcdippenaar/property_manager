"""Formatter — "Layout Engineer" agent. Phase 2 Day 3+ implementation.

Per ``docs/system/lease-ai-agent-architecture.md`` §5.4 the Formatter
owns heading hierarchy, running headers, page breaks, per-page initials,
table layout, readability. Phase 2 Day 1-2 ships the front-door route
that targets the Formatter but the real implementation lands when:

  1. Phase 3 R5 — the Gotenberg `@page` POC confirms the CSS approach
     works for per-page initials.
  2. The 4 new layout tools land (``set_running_header``,
     ``set_running_footer``, ``set_per_page_initials``,
     ``insert_page_break``).
  3. The persona + cache-control markers are wired.

Until then any attempt to dispatch the Formatter raises a clear
:class:`NotImplementedError` so a routing bug surfaces fast rather than
silently no-op'ing.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.leases.agent_runner import LeaseAgentRunner

    from .context import LeaseContext


PERSONA: str = (
    "You are the Layout Engineer agent — Phase 2 Day 3+ implementation. "
    "This persona is a placeholder; do not invoke."
)

TOOLS: list[dict[str, Any]] = []


class FormatterHandler:
    """Not implemented until Phase 2 Day 3+."""

    def run(
        self,
        *,
        runner: "LeaseAgentRunner",
        context: "LeaseContext",
        document_html: str,
        system_blocks: list[dict[str, Any]],
    ) -> None:
        raise NotImplementedError("Phase 2 Day 3+")


__all__ = ["PERSONA", "TOOLS", "FormatterHandler"]
