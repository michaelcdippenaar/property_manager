"""Formatter — "Layout Engineer" agent. Phase 3 implementation.

Per ``docs/system/lease-ai-agent-architecture.md`` §5.4 the Formatter owns
heading hierarchy, running headers, page breaks, per-page initials, table
layout, and readability.

The Gotenberg ``@page`` POC (``backend/scripts/spikes/per_page_initials_spike.py``)
confirmed Variant A (CSS ``@page`` margin boxes) works reliably in
Chromium/Gotenberg — this module emits that pattern exclusively.

Tools:
    * ``set_running_header``   — @top-right margin-box content
    * ``set_running_footer``   — @bottom-center margin-box content
    * ``set_per_page_initials`` — convenience wrapper for the SA-standard initials line
    * ``insert_page_break``    — ``<div style="page-break-after: always;">``
                                  after the targeted ``<h2 id="...">``

Loop behaviour:
    Single-turn tool-use loop (no pull-tool multi-turn pattern) capped at
    MAX_TOOL_CALLS (6). The Formatter applies a known transformation — it
    does not need to query RAG between turns.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.leases.agent_runner import LeaseAgentRunner

    from .context import LeaseContext

from apps.leases.agents.formatter_tools import TOOLS, dispatch_tool

logger = logging.getLogger(__name__)


# ── Persona ──────────────────────────────────────────────────────────── #


# The Formatter persona is the FIRST cache block on every Formatter call,
# matching the Drafter / Reviewer cache_control pattern (decision 18 + §6.6).
PERSONA_FORMATTER: str = """You are a typography and layout specialist for South African legal documents.

You handle:
- Running headers (top of every page)
- Running footers (bottom of every page) — including per-page initials placeholders
- Page break placement
- Heading hierarchy normalisation
- Readability

You NEVER change the wording of any clause. Your tools mutate CSS and structural HTML only — never the prose.

For per-page initials, the standard SA convention is:
  "I have read this page — initials: ____"
centred at the bottom margin of every page.

For running headers, the standard pattern is:
  "Residential Lease — page {page} of {pages}"
top-right.

Call your tools to make these changes. After your final tool call, emit a one-sentence summary of what was applied. Do not produce HTML in prose."""

# Keep the old public name for backward compatibility.
PERSONA: str = PERSONA_FORMATTER


# ── Result dataclass ─────────────────────────────────────────────────── #


@dataclass
class FormatterResult:
    """Output of :meth:`FormatterHandler.run`.

    ``html`` is the document state after all tool calls have been applied.
    ``applied_changes`` is the list of ``change_summary`` strings from each
    successful tool call — used by the SSE generator to emit ``text_chunk``
    events for the progress strip.
    ``cost_ledger_delta`` mirrors the per-agent call record shape so the
    view layer can surface cost attribution (currently unused by the view
    but reserved so the field exists when we add per-agent cost logging).
    """

    html: str
    applied_changes: list[str] = field(default_factory=list)
    conversational_reply: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    internal_turns: int = 0
    terminated_reason: str = "end_turn"
    cost_ledger_delta: dict[str, Any] = field(default_factory=dict)


# ── Handler ──────────────────────────────────────────────────────────── #


class FormatterHandler:
    """Drives the Formatter's single-turn tool-use loop.

    The Formatter receives the post-Reviewer HTML and applies layout
    transformations via its 4 tools. Unlike the Reviewer there is no
    pull-tool pattern — the Formatter always converges in at most
    MAX_TOOL_CALLS dispatches (budget cap = 6 per architecture §8.1).

    Loop invariant: each ``messages.create`` can return zero or more
    ``tool_use`` blocks. We apply each one, accumulate tool_results, and
    continue until the model returns ``stop_reason="end_turn"`` (or the
    tool cap is reached).
    """

    MAX_TOOL_CALLS: int = 6

    def __init__(self, *, model: str | None = None):
        from django.conf import settings

        self.model = model or getattr(
            settings, "LEASE_AI_FORMATTER_MODEL", "claude-haiku-4-5-20251001"
        )

    def run(
        self,
        *,
        runner: "LeaseAgentRunner",
        context: "LeaseContext",
        document_html: str,
        system_blocks: list[dict[str, Any]],
    ) -> FormatterResult:
        """Run the Formatter loop. Returns :class:`FormatterResult`.

        ``context`` is accepted for symmetry with DrafterHandler /
        ReviewerHandler and for potential future use (e.g. property_type
        may influence heading normalisation). It is not used in the tool
        dispatch today.
        """
        user_payload = (
            "Please apply standard SA residential lease formatting to the "
            "document below:\n"
            "1. Set a running header: \"Residential Lease — page {page} of {pages}\" at top-right.\n"
            "2. Set per-page initials: \"I have read this page — initials: ____\" at bottom-centre.\n"
            "3. Insert page breaks after major sections if the document "
            "   has <h2> elements with id= attributes (use insert_page_break).\n\n"
            "Call your tools and then emit a one-sentence summary.\n\n"
            f"<document>\n{document_html or '(empty)'}\n</document>"
        )
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": user_payload}
        ]

        html = document_html or ""
        applied_changes: list[str] = []
        tool_calls_log: list[dict[str, Any]] = []
        conversational_reply = ""
        terminated_reason = "end_turn"
        total_tool_calls = 0

        # Single dispatch: the Formatter is a single-turn agent per §8.2
        # ("format → Formatter only (1 LLM call)"). However, a single
        # response can carry multiple tool_use blocks (e.g. set_running_header
        # + set_per_page_initials in one turn). We run one LLM call and
        # execute all tool_use blocks in it, limited to MAX_TOOL_CALLS total.
        response = runner.dispatch(
            agent="formatter",
            model=self.model,
            messages=messages,
            system=system_blocks,
            tools=TOOLS,
        )

        for block in getattr(response, "content", []) or []:
            btype = getattr(block, "type", None)
            if btype == "text":
                text = (getattr(block, "text", "") or "").strip()
                if text:
                    conversational_reply = text
            elif btype == "tool_use":
                if total_tool_calls >= self.MAX_TOOL_CALLS:
                    terminated_reason = "tool_cap"
                    logger.warning(
                        "FormatterHandler: MAX_TOOL_CALLS=%d reached — "
                        "skipping remaining tool_use blocks.",
                        self.MAX_TOOL_CALLS,
                    )
                    break

                name = getattr(block, "name", "")
                inp = getattr(block, "input", {}) or {}
                result = dispatch_tool(name, inp, html)
                total_tool_calls += 1

                if result.get("ok"):
                    html = result["new_html"]
                    applied_changes.append(result["change_summary"])
                else:
                    # Tool failed but this is non-fatal; log and continue.
                    logger.warning(
                        "FormatterHandler: tool %r returned ok=False: %s",
                        name,
                        result.get("change_summary"),
                    )

                tool_calls_log.append(
                    {
                        "name": name,
                        "input": inp,
                        "ok": result.get("ok", False),
                        "result_summary": result.get("change_summary", ""),
                    }
                )

        stop_reason = getattr(response, "stop_reason", None)
        if terminated_reason == "end_turn":
            terminated_reason = stop_reason or "end_turn"

        # Cost ledger delta — mirrors _CallRecord shape for optional
        # per-agent cost attribution.
        usage = getattr(response, "usage", None)
        cost_ledger_delta: dict[str, Any] = {}
        if usage is not None:
            cost_ledger_delta = {
                "agent": "formatter",
                "model": self.model,
                "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
                "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
                "cache_read": int(
                    getattr(usage, "cache_read_input_tokens", 0) or 0
                ),
                "cache_created": int(
                    getattr(usage, "cache_creation_input_tokens", 0) or 0
                ),
            }

        return FormatterResult(
            html=html,
            applied_changes=applied_changes,
            conversational_reply=conversational_reply,
            tool_calls=tool_calls_log,
            internal_turns=1,
            terminated_reason=terminated_reason,
            cost_ledger_delta=cost_ledger_delta,
        )


__all__ = ["PERSONA", "PERSONA_FORMATTER", "TOOLS", "FormatterHandler", "FormatterResult"]
