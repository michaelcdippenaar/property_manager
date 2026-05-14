"""Formatter agent — 4 layout tools (implementation + Anthropic schema).

Each tool returns a structured result dict::

    {
        "ok": bool,
        "new_html": str,
        "change_summary": str,
    }

The four tools:

    set_running_header(text)
        Inserts/replaces ``@page { @top-right { content: ... } }``.
        Supports ``{page}`` / ``{pages}`` placeholders.

    set_running_footer(text)
        Same, ``@bottom-center``. Empty string clears the footer rule.

    set_per_page_initials(text)
        Convenience wrapper: calls ``set_running_footer`` with the
        standard SA initials line, or a custom override.

    insert_page_break(after_section_id)
        Inserts ``<div style="page-break-after: always;"></div>``
        immediately after the ``<h2 id="<after_section_id>">...</h2>``
        element. The Drafter emits ``id=`` attributes on every ``<h2>``;
        if the id is not found, the tool reports that honestly and
        returns the HTML unchanged.

All tool implementations are thin — they delegate to
:class:`apps.leases.agents.page_css_builder.PageCssBuilder`.
"""
from __future__ import annotations

import re
from typing import Any

from apps.leases.agents.page_css_builder import PageCssBuilder


# ── Default SA convention strings ────────────────────────────────────── #

DEFAULT_INITIALS_TEXT: str = "I have read this page — initials: ____"
DEFAULT_HEADER_TEXT: str = "Residential Lease — page {page} of {pages}"


# ── Tool implementations ─────────────────────────────────────────────── #


def apply_set_running_header(args: dict[str, Any], html: str) -> dict[str, Any]:
    """Implement the ``set_running_header`` tool.

    Reads any existing ``@page`` block out of ``html``, sets
    ``running_header`` on the builder, and writes back. Returns the
    structured result dict.
    """
    text = str(args.get("text") or "").strip()
    builder = PageCssBuilder.from_html(html)
    builder.running_header = text
    try:
        new_html = builder.write_back(html)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "new_html": html,
            "change_summary": f"set_running_header failed: {exc}",
        }
    summary = (
        f"set_running_header: @top-right content set to {text!r}."
        if text
        else "set_running_header: @top-right rule cleared."
    )
    return {"ok": True, "new_html": new_html, "change_summary": summary}


def apply_set_running_footer(args: dict[str, Any], html: str) -> dict[str, Any]:
    """Implement the ``set_running_footer`` tool.

    Empty string clears the ``@bottom-center`` rule.
    """
    text = str(args.get("text") or "").strip()
    builder = PageCssBuilder.from_html(html)
    builder.running_footer = text
    try:
        new_html = builder.write_back(html)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "new_html": html,
            "change_summary": f"set_running_footer failed: {exc}",
        }
    summary = (
        f"set_running_footer: @bottom-center content set to {text!r}."
        if text
        else "set_running_footer: @bottom-center rule cleared."
    )
    return {"ok": True, "new_html": new_html, "change_summary": summary}


def apply_set_per_page_initials(args: dict[str, Any], html: str) -> dict[str, Any]:
    """Implement the ``set_per_page_initials`` tool.

    Convenience wrapper for :func:`apply_set_running_footer` using the
    standard SA initials line as default. Delegates entirely so the
    ``@page`` block is always consistent.
    """
    text = str(args.get("text") or DEFAULT_INITIALS_TEXT).strip()
    if not text:
        text = DEFAULT_INITIALS_TEXT
    result = apply_set_running_footer({"text": text}, html)
    if result["ok"]:
        result = dict(result)
        result["change_summary"] = (
            f"set_per_page_initials: per-page initials placeholder set to {text!r}."
        )
    return result


def apply_insert_page_break(args: dict[str, Any], html: str) -> dict[str, Any]:
    """Implement the ``insert_page_break`` tool.

    Inserts ``<div style="page-break-after: always;"></div>`` immediately
    after the closing tag of the ``<h2>`` element whose ``id`` attribute
    equals ``after_section_id``. The Drafter is responsible for placing
    ``id=`` attributes on its ``<h2>`` headings.

    Regex strategy: match ``<h2 ... id="<id>" ...>...</h2>`` (possibly
    with other attributes). This is safe given the Drafter's predictable
    HTML output.
    """
    section_id = str(args.get("after_section_id") or "").strip()
    if not section_id:
        return {
            "ok": False,
            "new_html": html,
            "change_summary": "insert_page_break: after_section_id is required.",
        }

    # Match a <h2> whose id= attribute equals section_id (tolerates
    # single/double quotes, arbitrary attribute order).
    pattern = re.compile(
        r"(<h2\b[^>]*\bid=['\"]"
        + re.escape(section_id)
        + r"['\"][^>]*>.*?</h2>)",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(html or "")
    if match is None:
        return {
            "ok": False,
            "new_html": html,
            "change_summary": (
                f"insert_page_break: no <h2 id=\"{section_id}\"> found in document. "
                "Check that the Drafter emitted the id attribute on this heading."
            ),
        }

    PAGE_BREAK_DIV = '<div style="page-break-after: always;"></div>'
    insert_at = match.end()
    new_html = html[:insert_at] + PAGE_BREAK_DIV + html[insert_at:]
    return {
        "ok": True,
        "new_html": new_html,
        "change_summary": (
            f"insert_page_break: page break inserted after section id={section_id!r}."
        ),
    }


# ── Anthropic tool schemas ────────────────────────────────────────────── #


# Per architecture §9 + decision 18: all Formatter tool entries include
# ``cache_control`` on the last entry so the tools array is part of the
# cache prefix, matching the Drafter pattern exactly.
TOOLS: list[dict[str, Any]] = [
    {
        "name": "set_running_header",
        "description": (
            "Set or replace the running header that appears at the top-right "
            "corner of every page via CSS @page @top-right margin box. "
            "Supports ``{page}`` (current page number) and ``{pages}`` (total pages) "
            "placeholders — these expand to CSS counter() expressions. "
            "Empty string clears the @top-right rule."
        ),
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "text": {
                    "type": "string",
                    "description": (
                        "Header text. Use {page} and {pages} for page numbering. "
                        "E.g.: \"Residential Lease — page {page} of {pages}\". "
                        "Empty string clears the rule."
                    ),
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "set_running_footer",
        "description": (
            "Set or replace the running footer that appears at the bottom-centre "
            "of every page via CSS @page @bottom-center margin box. "
            "Supports ``{page}`` / ``{pages}`` placeholders. "
            "Empty string clears the @bottom-center rule."
        ),
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "text": {
                    "type": "string",
                    "description": (
                        "Footer text. Empty string clears the rule. "
                        "For per-page initials use set_per_page_initials instead."
                    ),
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "set_per_page_initials",
        "description": (
            "Place a per-page initials placeholder at the bottom of every page — "
            "the standard SA convention. Uses the @bottom-center CSS margin box. "
            "Default text: \"I have read this page — initials: ____\". "
            "Call without a ``text`` argument (or pass the default) for the "
            "SA-standard wording. Override only when the client requests "
            "different wording."
        ),
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "text": {
                    "type": "string",
                    "description": (
                        "Custom initials line. "
                        "Defaults to \"I have read this page — initials: ____\" "
                        "when omitted or empty."
                    ),
                },
            },
            "required": [],
        },
    },
    {
        "name": "insert_page_break",
        "description": (
            "Insert a forced page break after a specific document section. "
            "The section is identified by the ``id`` attribute on its ``<h2>`` "
            "heading — the Drafter emits ``<h2 id=\"section-id\">`` on every "
            "top-level heading. Inserts "
            "``<div style=\"page-break-after: always;\"></div>`` immediately "
            "after the closing ``</h2>`` tag."
        ),
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "after_section_id": {
                    "type": "string",
                    "description": (
                        "The ``id=`` attribute value of the <h2> heading after "
                        "which the page break should be inserted. "
                        "E.g. \"deposit\" for <h2 id=\"deposit\">."
                    ),
                },
            },
            "required": ["after_section_id"],
        },
        "cache_control": {"type": "ephemeral"},
    },
]


# ── Dispatch helper ──────────────────────────────────────────────────── #


def dispatch_tool(name: str, args: dict[str, Any], html: str) -> dict[str, Any]:
    """Dispatch a Formatter tool call by name.

    Returns the structured ``{ok, new_html, change_summary}`` dict.
    Unknown tool names return ``ok=False`` with an explanatory summary.
    Never raises — failures are surfaced in the result dict so the loop
    can pass them back to the model as ``tool_result`` content.
    """
    try:
        if name == "set_running_header":
            return apply_set_running_header(args, html)
        if name == "set_running_footer":
            return apply_set_running_footer(args, html)
        if name == "set_per_page_initials":
            return apply_set_per_page_initials(args, html)
        if name == "insert_page_break":
            return apply_insert_page_break(args, html)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "new_html": html,
            "change_summary": f"Tool {name!r} raised unexpectedly: {exc}",
        }
    return {
        "ok": False,
        "new_html": html,
        "change_summary": f"Unknown Formatter tool: {name!r}.",
    }


__all__ = [
    "TOOLS",
    "DEFAULT_HEADER_TEXT",
    "DEFAULT_INITIALS_TEXT",
    "apply_insert_page_break",
    "apply_set_per_page_initials",
    "apply_set_running_footer",
    "apply_set_running_header",
    "dispatch_tool",
]
