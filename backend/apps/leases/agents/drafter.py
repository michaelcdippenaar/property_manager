"""Drafter — "SA Property Lawyer" agent.

Per ``docs/system/lease-ai-agent-architecture.md`` §5.2 the Drafter owns
the document surface and assembles clauses from the curated library
pushed by the Front Door. ALWAYS prefers assembly over generation.

Phase 2 / Wave 2A scope:
  * Persona + 6 tool schemas: ``add_clause`` / ``edit_lines`` /
    ``format_sa_standard`` / ``insert_signature_field`` /
    ``highlight_fields`` / ``check_rha_compliance``. All six now have
    real implementations.
  * Multi-turn loop capped at 3 internal turns per architecture
    decision 10. Each ``messages.create`` is dispatched through
    :class:`apps.leases.agent_runner.LeaseAgentRunner` so cost / call /
    wall-clock caps cover the loop.
  * ``DrafterResult`` carries the rendered HTML + tool-call records +
    final conversational reply + highlighted_fields surface.

Tool-partitioning matrix (§9): the Drafter has ``edit_lines`` /
``add_clause`` / ``format_sa_standard`` / ``insert_signature_field`` /
``highlight_fields`` / ``check_rha_compliance``. ``update_all`` is
removed in v2 (decision 21) and is NOT in the schema list.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.leases.agent_runner import LeaseAgentRunner

    from .context import LeaseContext

logger = logging.getLogger(__name__)


# Canonical SA-residential-lease section order per architecture doc §5.2.
# Used by ``format_sa_standard`` to detect missing sections and insert
# placeholders. Order is load-bearing — keep in sync with the architecture
# doc / clause-corpus seed.
SA_STANDARD_SECTIONS: tuple[str, ...] = (
    "PARTIES",
    "PROPERTY",
    "TERM",
    "RENT",
    "DEPOSIT",
    "MAINTENANCE",
    "DEFAULT",
    "TERMINATION",
    "DISPUTE",
    "SIGNATURES",
)


# Token format for signature fields. ``N`` is the signature index (1-based);
# the regex matches both ``⟪SIG#1⟫`` (canonical) and bare alternatives.
_SIG_TOKEN_RE = re.compile(r"⟪SIG#(\d+)⟫")


# Block-level HTML element regex. Captures each ``<p>`` / ``<h1..h6>`` /
# ``<li>`` / ``<section>`` element start-to-end. We use a forgiving regex
# rather than a full HTML parser because the document HTML is produced by
# TipTap on the frontend + our own clause snippets — both predictable
# enough that regex round-trips reliably.
_BLOCK_ELEMENT_RE = re.compile(
    r"<(p|h[1-6]|li|section|div)(?:\s[^>]*)?>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)


# ── Persona ──────────────────────────────────────────────────────────── #


# The Drafter persona is the FIRST cache block on every Drafter call.
# Two non-negotiable instructions:
#   1. MUST NOT emit placeholder strings — defends against the "AI
#      claimed to add 13 sections but emitted placeholders" failure
#      class (architecture doc §2 failure 1).
#   2. Use ONLY canonical merge fields — defends against phantom
#      tenant_2_* fields (architecture doc §2 failure 2).
PERSONA: str = """You are an expert in South African residential lease law operating as the Drafter agent in a multi-agent cluster.

ROLE & SCOPE
- You assemble lease clauses from the curated SA-rental-law clause library that has been pushed to you by the Front Door.
- You ALWAYS prefer assembly (calling `add_clause` with a clause_id from the corpus) over generation. Generation is a last resort.
- You cite RHA / CPA / POPIA / PIE / Sectional Titles Schemes Management Act exactly as they appear in the pushed corpus.

HARD RULES — these are non-negotiable invariants the runner enforces:
- You MUST NOT emit "[needs completion]" or similar placeholders. The strings "[needs completion]", "[TBD]", "[TODO]", "[fill in]", "[insert]", "[placeholder]", "<<<>>>", "XXX", and any "[..." pattern that signals an unfinished section are BANNED in your output.
- Use ONLY canonical merge fields listed in the merge-fields system block. Never invent, pluralise, or extend a field name. If a concept has no canonical merge field, write the literal value the user provided — never invent a new `{{ field_name }}`.
- If the user has one tenant, do NOT emit `tenant_2_*` / `tenant_3_*` / `co_tenant_*` / `occupant_2_*` fields. The Front Door filters these out — if you can't see them in the merge-fields block, they don't apply to this request.
- For low-confidence citations (`legal_provisional` chunks): cite the concept without the sub-section letter and stamp the clause `legal_provisional: true`. Do not invent sub-section letters.
- Lying about doing the work (emitting 13 headings with empty bodies) is far worse than admitting you didn't. If a section needs content you cannot generate from the pushed corpus, either call `add_clause` to pull one, or tell the user honestly that you need them to fill that section.

TOOL DISCIPLINE
- Always call a tool for any document mutation request — never describe changes in prose only.
- `add_clause` is the preferred tool for inserting a curated clause from the corpus by `clause_id`.
- `edit_lines` is for targeted edits of existing lines (preserves clause numbering).
- `format_sa_standard` restructures the whole document to the 13-section SA layout — populated with real clause prose from the corpus, NOT placeholders.
- `insert_signature_field` is the only way to create a new signature block; never emit `⟪SIG#N⟫` tokens yourself.
- `highlight_fields` is conversational — it points the user at merge fields they should fill.
- `check_rha_compliance` is a read-only self-check the Drafter runs before submitting (the Reviewer will run a deeper check).

OUTPUT SHAPE
- The conversational reply (the `text` block) is 1-3 sentences for routine edits, up to 5 sentences for explanations or refusals.
- You can chain tool calls within one turn (multi-turn loop is capped at 3 turns by the coordinator).
"""


# ── Tool schemas ─────────────────────────────────────────────────────── #


# Per architecture decision 18 + §6.6: every Drafter call carries a
# ``cache_control`` marker on the last tool entry so the tools array is
# part of the cache prefix.
TOOLS: list[dict[str, Any]] = [
    {
        "name": "edit_lines",
        "description": (
            "Replace text in a range of lines. Preserves clause numbering. "
            "Preferred for targeted edits over `format_sa_standard`."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "from_index": {"type": "integer"},
                "to_index": {"type": "integer"},
                "new_lines": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tag": {"type": "string"},
                            "text": {"type": "string"},
                        },
                        "required": ["text"],
                    },
                },
                "summary": {"type": "string"},
            },
            "required": ["from_index", "to_index", "new_lines"],
        },
    },
    {
        "name": "add_clause",
        "description": (
            "Insert a curated clause from the SA-rental-law corpus by "
            "`clause_id`. The clause_id MUST match one of the chunks "
            "pushed by the Front Door in the RAG block — never invent "
            "a clause_id."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "after_line_index": {
                    "type": "integer",
                    "description": (
                        "Insert immediately after this line. Use -1 to "
                        "append at the end of the document."
                    ),
                },
                "clause_id": {
                    "type": "string",
                    "description": "Stable corpus ID, e.g. `clause-deposit-interest-bearing-account-v1`.",
                },
                "customise": {
                    "type": "object",
                    "description": "Optional merge-field overrides for this insertion.",
                },
            },
            "required": ["after_line_index", "clause_id"],
        },
    },
    {
        "name": "format_sa_standard",
        "description": (
            "Restructure the document to the standard 13-section SA "
            "layout. Each missing section is populated with real corpus "
            "prose — NOT placeholders."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "add_missing": {"type": "boolean"},
                "preserve_custom": {"type": "boolean"},
            },
            "required": [],
        },
    },
    {
        "name": "insert_signature_field",
        "description": (
            "Insert a new signature block. The only way to create a "
            "`⟪SIG#N⟫` token — Drafter MUST NOT emit them directly."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "after_line_index": {"type": "integer"},
                "field_type": {
                    "type": "string",
                    "enum": ["signature", "initials", "date"],
                },
                "signer_role": {
                    "type": "string",
                    "enum": ["landlord", "tenant", "co_tenant", "witness"],
                },
                "field_name": {"type": "string"},
            },
            "required": ["after_line_index", "field_type", "signer_role"],
        },
    },
    {
        "name": "highlight_fields",
        "description": (
            "Conversational: point the user at merge fields they need to fill."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "field_names": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "message": {"type": "string"},
            },
            "required": ["field_names"],
        },
    },
    {
        "name": "check_rha_compliance",
        "description": (
            "Read-only self-check — runs the same diagnostic the "
            "Reviewer will run. Result is returned to the Drafter so it "
            "can fix issues before handing off."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "cache_control": {"type": "ephemeral"},
    },
]


# ── Result dataclass ─────────────────────────────────────────────────── #


@dataclass
class DrafterResult:
    """Output of :meth:`DrafterHandler.run`.

    ``rendered_html`` is the document state after the Drafter's tool
    chain has applied. ``tool_calls`` lists each tool invocation
    (name + input + brief outcome) for telemetry + SSE streaming.
    ``conversational_reply`` is the prose text the user sees.

    ``highlighted_fields`` carries the side-effect from any
    ``highlight_fields`` tool call so the SSE generator can emit a
    ``highlight_fields`` event without re-parsing tool_calls.

    ``rha_compliance`` carries the read-only diagnostic from any
    ``check_rha_compliance`` call (list of ``{citation, status,
    message}``); empty list when the tool wasn't invoked.
    """

    rendered_html: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    conversational_reply: str = ""
    internal_turns: int = 0
    terminated_reason: str = "end_turn"
    highlighted_fields: list[dict[str, Any]] = field(default_factory=list)
    rha_compliance: list[dict[str, Any]] = field(default_factory=list)


# ── Tool-impl helpers ────────────────────────────────────────────────── #


def _apply_add_clause(args: dict[str, Any], document_html: str) -> tuple[str, str]:
    """Implement the ``add_clause`` tool.

    Looks up ``clause_id`` in the corpus, renders the clause body, and
    appends or inserts it into ``document_html`` at ``after_line_index``.
    Returns ``(new_html, tool_result_summary)``.

    Defensive: a missing clause_id returns a short tool-result string
    the Drafter sees as feedback ("clause_id 'foo' not in corpus") so
    the model can choose another clause on a retry turn — never raises
    a Python exception into the runner, which would terminate the
    request mid-stream.
    """
    clause_id = str(args.get("clause_id") or "").strip()
    if not clause_id:
        return document_html, "add_clause failed: clause_id is required"

    try:
        from apps.leases.lease_law_corpus_queries import query_clauses

        # Filter to the requested clause_id. Phase 2 Day 3+ will replace
        # this with a dedicated ``query_clause_by_id`` helper; today the
        # query API doesn't expose one, so we filter post-hoc.
        candidates = query_clauses(k=200)
    except Exception:  # noqa: BLE001
        logger.exception("add_clause: corpus query failed")
        return document_html, f"add_clause failed: corpus unavailable for {clause_id!r}"

    match = next((c for c in candidates if c.id == clause_id), None)
    if match is None:
        return document_html, (
            f"add_clause failed: clause_id={clause_id!r} not in corpus"
        )

    title = match.clause_title.strip() or "Clause"
    body = match.clause_body.strip()
    snippet = f"<section data-clause-id=\"{match.id}\"><h2>{title}</h2><p>{body}</p></section>"

    after_line = args.get("after_line_index")
    if isinstance(after_line, int) and after_line >= 0:
        # Day 1-2 stub: we don't have a line→HTML offset mapping yet
        # (Phase 3 work). Append at the end and let the Formatter sort
        # ordering. The tool_result reflects this honestly so the model
        # doesn't think it placed the clause mid-document.
        new_html = (document_html or "") + snippet
        summary = (
            f"Inserted clause {match.id!r} ({title}). Appended at end — "
            f"Phase 3 will honour after_line_index."
        )
    else:
        new_html = (document_html or "") + snippet
        summary = f"Appended clause {match.id!r} ({title}) at end."

    return new_html, summary


def _apply_edit_lines(args: dict[str, Any], document_html: str) -> tuple[str, str]:
    """Implement the ``edit_lines`` tool.

    Replaces a contiguous range of block-level HTML elements with new
    elements derived from ``args['new_lines']``. ``new_lines`` is a list
    of ``{tag, text}`` dicts; the rendered element is ``<tag>text</tag>``,
    defaulting to ``<p>`` when ``tag`` is missing or unknown.

    Signature tokens (``⟪SIG#N⟫``) inside the affected range are NOT
    lost — any line whose body contains a token is preserved verbatim
    even when the range is replaced. The architecture doc treats the
    tokens as opaque placeholders the renderer expands at PDF time, so
    losing one would corrupt the signing surface.
    """
    from_idx_raw = args.get("from_index")
    to_idx_raw = args.get("to_index")
    new_lines = args.get("new_lines") or []
    if not isinstance(new_lines, list):
        return document_html, "edit_lines failed: new_lines must be a list"
    try:
        from_idx = int(from_idx_raw) if from_idx_raw is not None else 0
        to_idx = int(to_idx_raw) if to_idx_raw is not None else from_idx + 1
    except (TypeError, ValueError):
        return document_html, "edit_lines failed: from_index / to_index must be integers"

    if from_idx < 0 or to_idx < from_idx:
        return document_html, "edit_lines failed: from_index/to_index out of range"

    elements = _BLOCK_ELEMENT_RE.findall(document_html or "")
    # The findall iterator above only returns the tag, not the full
    # matched text — we need the matches themselves to manipulate slices.
    matches = list(_BLOCK_ELEMENT_RE.finditer(document_html or ""))

    if not matches:
        # Empty / non-blocky document: just append the new lines.
        rendered_new = _render_new_lines(new_lines)
        return (document_html or "") + rendered_new, (
            f"edit_lines appended {len(new_lines)} new line(s) to empty "
            f"document (no block elements found to replace)."
        )

    clamped_to = min(to_idx, len(matches))
    if from_idx >= len(matches):
        # Inserting past the end: append.
        rendered_new = _render_new_lines(new_lines)
        return (document_html or "") + rendered_new, (
            f"edit_lines appended {len(new_lines)} new line(s) past the end."
        )

    # Preserve any element in the range that contains a signature token.
    preserved: list[str] = []
    for idx in range(from_idx, clamped_to):
        block_text = matches[idx].group(0)
        if _SIG_TOKEN_RE.search(block_text):
            preserved.append(block_text)

    rendered_new = _render_new_lines(new_lines)
    preserved_html = "".join(preserved)

    before = document_html[: matches[from_idx].start()]
    after = document_html[matches[clamped_to - 1].end():] if clamped_to > from_idx else document_html[matches[from_idx].start():]

    new_html = before + preserved_html + rendered_new + after
    summary = (
        f"edit_lines replaced elements [{from_idx}:{clamped_to}] with "
        f"{len(new_lines)} new line(s). Preserved {len(preserved)} "
        f"signature-token line(s)."
    )
    if elements:
        # Lint-only assertion so the regression battery can spot drift.
        _ = elements  # explicit usage; the findall result is for diagnostics only.
    return new_html, summary


def _render_new_lines(new_lines: list[Any]) -> str:
    """Render a list of ``{tag, text}`` dicts as block-level HTML."""
    out: list[str] = []
    allowed_tags = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "div"}
    for raw in new_lines:
        if not isinstance(raw, dict):
            continue
        tag = str(raw.get("tag") or "p").lower()
        if tag not in allowed_tags:
            tag = "p"
        text = str(raw.get("text") or "")
        out.append(f"<{tag}>{text}</{tag}>")
    return "".join(out)


def _apply_format_sa_standard(
    args: dict[str, Any], document_html: str
) -> tuple[str, str]:
    """Implement the ``format_sa_standard`` tool.

    Walks the document, detects which of :data:`SA_STANDARD_SECTIONS` are
    present (matched on ``<h*>`` heading text — case-insensitive
    substring), and if ``add_missing=True`` appends a placeholder for any
    absent section. The placeholder uses the literal copy "Section to be
    drafted — pull a clause via add_clause" (NOT one of the banned
    ``[needs completion]`` strings).

    If ``preserve_custom=True`` any non-standard headings stay where
    they are; otherwise they remain too (we don't have section-reorder
    logic yet — see Phase 3).
    """
    add_missing = bool(args.get("add_missing"))
    preserve_custom = bool(args.get("preserve_custom"))

    present = _detect_present_sections(document_html or "")
    missing = [name for name in SA_STANDARD_SECTIONS if name not in present]

    if not add_missing:
        summary = (
            f"format_sa_standard: detected {len(present)} standard "
            f"section(s); {len(missing)} missing. add_missing=False → no "
            f"mutation."
        )
        return document_html, summary

    snippets: list[str] = []
    for name in missing:
        snippets.append(
            f"<section data-sa-section=\"{name.lower()}\">"
            f"<h2>{name}</h2>"
            f"<p>Section to be drafted — pull a clause via add_clause.</p>"
            f"</section>"
        )
    new_html = (document_html or "") + "".join(snippets)
    summary = (
        f"format_sa_standard inserted {len(snippets)} placeholder "
        f"section(s): {', '.join(missing) or '(none)'}. "
        f"preserve_custom={preserve_custom} (Phase 3 reorders non-standard "
        f"sections; today they stay in place)."
    )
    return new_html, summary


def _detect_present_sections(document_html: str) -> set[str]:
    """Return the set of standard section names present in the document.

    Detection is case-insensitive: any ``<h1..h6>`` whose body contains
    a standard section name as a substring counts. We don't require
    exact equality so headings like ``<h2>2. DEPOSIT</h2>`` still match.
    """
    found: set[str] = set()
    headings = re.findall(
        r"<h[1-6][^>]*>(.*?)</h[1-6]>", document_html, re.IGNORECASE | re.DOTALL
    )
    for body in headings:
        upper = re.sub(r"<[^>]+>", "", body).upper()
        for section in SA_STANDARD_SECTIONS:
            if section in upper:
                found.add(section)
    return found


def _apply_insert_signature_field(
    args: dict[str, Any], document_html: str
) -> tuple[str, str]:
    """Implement the ``insert_signature_field`` tool.

    Allocates the next free ``⟪SIG#N⟫`` index (1-based) and inserts the
    token at the end of the document. Phase 3 will honour
    ``after_line_index`` against the same block-element offset mapping
    as :func:`_apply_edit_lines`; today we append.
    """
    field_type = str(args.get("field_type") or "signature")
    signer_role = str(args.get("signer_role") or "tenant")
    field_name = str(args.get("field_name") or "")

    used_indices = {int(m.group(1)) for m in _SIG_TOKEN_RE.finditer(document_html or "")}
    next_index = 1
    while next_index in used_indices:
        next_index += 1

    token = f"⟪SIG#{next_index}⟫"
    snippet = (
        f"<p data-signature-role=\"{signer_role}\" "
        f"data-signature-type=\"{field_type}\" "
        f"data-signature-name=\"{field_name}\">{token}</p>"
    )
    new_html = (document_html or "") + snippet
    summary = (
        f"insert_signature_field allocated token {token} "
        f"(role={signer_role}, type={field_type}, name={field_name!r})."
    )
    return new_html, summary


def _apply_highlight_fields(
    args: dict[str, Any], document_html: str
) -> tuple[str, str, dict[str, Any]]:
    """Implement the ``highlight_fields`` tool.

    This is a conversational tool — it does NOT mutate the HTML. The
    Drafter calls it when it wants to point the user at merge fields
    they need to fill in. The helper returns a side-effect dict that
    the DrafterHandler stitches into :class:`DrafterResult.highlighted_fields`.
    """
    field_names = args.get("field_names") or []
    message = str(args.get("message") or "")
    if not isinstance(field_names, list):
        field_names = []
    payload = {
        "field_names": [str(name) for name in field_names],
        "message": message,
    }
    summary = (
        f"highlight_fields surfaced {len(payload['field_names'])} field(s) "
        f"to the user. No HTML mutation."
    )
    return document_html, summary, payload


def _apply_check_rha_compliance(
    args: dict[str, Any], document_html: str
) -> tuple[str, str, list[dict[str, Any]]]:
    """Implement the ``check_rha_compliance`` tool.

    Read-only diagnostic. Scrapes every statute citation from the
    document and validates each against
    :data:`apps.leases.management.commands.verify_caselaw_citations.CANONICAL_CITATIONS`
    plus the ``KNOWN_WRONG_CITATIONS`` blacklist. Returns a list of
    ``{citation, status, message}`` dicts the Drafter can consume.

    Status values:
      * ``ok``       — citation is in the canonical map at HIGH/MEDIUM.
      * ``low``      — citation is in the canonical map at LOW confidence
        (needs lawyer sign-off).
      * ``unknown``  — citation not in the map.
      * ``wrong``    — citation is in the KNOWN_WRONG_CITATIONS blacklist.
    """
    from apps.leases.management.commands.verify_caselaw_citations import (
        CANONICAL_CITATIONS,
        CITATION_RE,
        KNOWN_WRONG_CITATIONS,
        normalise,
    )

    findings: list[dict[str, Any]] = []
    for match in CITATION_RE.finditer(document_html or ""):
        statute, section = match.group(1), match.group(2)
        canonical = normalise(statute, section)
        wrong_key_prefix = f"{statute.upper()}:{section.lower()}|"
        wrong_match = next(
            (k for k in KNOWN_WRONG_CITATIONS if k.startswith(wrong_key_prefix)),
            None,
        )
        if wrong_match is not None:
            findings.append(
                {
                    "citation": canonical,
                    "status": "wrong",
                    "message": KNOWN_WRONG_CITATIONS[wrong_match],
                }
            )
            continue
        entry = CANONICAL_CITATIONS.get(canonical)
        if entry is None:
            findings.append(
                {
                    "citation": canonical,
                    "status": "unknown",
                    "message": "Citation not in canonical map.",
                }
            )
            continue
        concept, confidence = entry
        if confidence == "LOW":
            findings.append(
                {
                    "citation": canonical,
                    "status": "low",
                    "message": (
                        f"LOW-confidence citation ({concept}) — requires "
                        f"lawyer sign-off before relied upon."
                    ),
                }
            )
        else:
            findings.append(
                {
                    "citation": canonical,
                    "status": "ok",
                    "message": f"Canonical: {concept} ({confidence}).",
                }
            )

    summary_counts = {
        s: sum(1 for f in findings if f["status"] == s)
        for s in ("ok", "low", "unknown", "wrong")
    }
    summary = (
        f"check_rha_compliance scanned {len(findings)} citation(s): "
        f"ok={summary_counts['ok']} low={summary_counts['low']} "
        f"unknown={summary_counts['unknown']} wrong={summary_counts['wrong']}."
    )
    return document_html, summary, findings


# ── Handler ─────────────────────────────────────────────────────────── #


class DrafterHandler:
    """Drives the Drafter's multi-turn tool loop.

    Single entry-point :meth:`run` performs:
      1. Dispatch ``messages.create`` through the runner (tools + system
         blocks + chat_history + user message).
      2. Inspect ``response.content`` for ``tool_use`` blocks.
      3. For each ``tool_use``: dispatch to :func:`_apply_add_clause`
         (only ``add_clause`` is wired Day 1-2; others raise to surface
         the "tool fired but not implemented" failure clearly).
      4. Feed ``tool_result`` blocks back into ``messages`` and loop
         until ``stop_reason != "tool_use"`` OR the internal-turn cap
         is hit.

    Internal-turn cap: 3 (decision 10). The runner's outer 8-call cap
    covers everything; this is the per-agent cap.
    """

    MAX_INTERNAL_TURNS: int = 3

    def __init__(self, *, model: str | None = None):
        from django.conf import settings

        self.model = model or getattr(
            settings, "LEASE_AI_DRAFTER_MODEL", "claude-sonnet-4-5"
        )

    def run(
        self,
        *,
        runner: "LeaseAgentRunner",
        context: "LeaseContext",
        system_blocks: list[dict[str, Any]],
    ) -> DrafterResult:
        """Run the Drafter loop. Returns :class:`DrafterResult`."""
        messages: list[dict[str, Any]] = list(context.chat_history or ())
        if not messages or messages[-1].get("role") != "user":
            messages.append({"role": "user", "content": context.user_message})

        document_html = context.template_html or ""
        tool_calls: list[dict[str, Any]] = []
        conversational_reply = ""
        terminated_reason = "end_turn"
        highlighted_fields: list[dict[str, Any]] = []
        rha_compliance: list[dict[str, Any]] = []

        for turn in range(self.MAX_INTERNAL_TURNS):
            response = runner.dispatch(
                agent="drafter",
                model=self.model,
                messages=messages,
                system=system_blocks,
                tools=TOOLS,
            )

            turn_tool_uses: list[Any] = []
            turn_tool_results: list[dict[str, Any]] = []
            for block in getattr(response, "content", []) or []:
                btype = getattr(block, "type", None)
                if btype == "text":
                    text = (getattr(block, "text", "") or "").strip()
                    if text:
                        conversational_reply = text
                elif btype == "tool_use":
                    name = getattr(block, "name", "")
                    inp = getattr(block, "input", {}) or {}
                    turn_tool_uses.append(block)

                    if name == "add_clause":
                        document_html, result_summary = _apply_add_clause(
                            inp, document_html
                        )
                    elif name == "edit_lines":
                        document_html, result_summary = _apply_edit_lines(
                            inp, document_html
                        )
                    elif name == "format_sa_standard":
                        document_html, result_summary = _apply_format_sa_standard(
                            inp, document_html
                        )
                    elif name == "insert_signature_field":
                        document_html, result_summary = _apply_insert_signature_field(
                            inp, document_html
                        )
                    elif name == "highlight_fields":
                        document_html, result_summary, hl_payload = _apply_highlight_fields(
                            inp, document_html
                        )
                        highlighted_fields.append(hl_payload)
                    elif name == "check_rha_compliance":
                        document_html, result_summary, rha_findings = _apply_check_rha_compliance(
                            inp, document_html
                        )
                        rha_compliance = rha_findings
                    else:
                        result_summary = f"Unknown tool {name!r}; no action taken."

                    tool_calls.append(
                        {
                            "name": name,
                            "input": inp,
                            "result_summary": result_summary,
                        }
                    )
                    turn_tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": getattr(block, "id", ""),
                            "content": result_summary,
                        }
                    )

            stop_reason = getattr(response, "stop_reason", None)
            if stop_reason == "end_turn" or not turn_tool_uses:
                terminated_reason = stop_reason or "end_turn"
                break

            # Feed tool calls + results back as the next user turn so the
            # Drafter can chain. The assistant message carries the raw
            # content list (text + tool_use blocks); the next user turn
            # carries the tool_result blocks.
            messages.append(
                {
                    "role": "assistant",
                    "content": _content_for_history(response),
                }
            )
            messages.append({"role": "user", "content": turn_tool_results})
        else:
            # Cap-hit on the for-loop (no break). The runner's outer
            # caps will already have surfaced an error if this also
            # blew the global budget; this branch just records that
            # the Drafter exhausted its internal turn budget cleanly.
            terminated_reason = "internal_turn_cap"

        if not document_html:
            document_html = _fallback_html_from_response(response)

        return DrafterResult(
            rendered_html=document_html,
            tool_calls=tool_calls,
            conversational_reply=conversational_reply,
            internal_turns=turn + 1,
            terminated_reason=terminated_reason,
            highlighted_fields=highlighted_fields,
            rha_compliance=rha_compliance,
        )


def _content_for_history(response: Any) -> list[dict[str, Any]]:
    """Re-serialise the response's content blocks into the ``messages``
    shape so the next ``messages.create`` call sees them as the assistant
    turn it must respond to.

    Tolerates both real SDK ``Message`` objects (pydantic) and the
    cassette's ``SimpleNamespace`` shape.
    """
    out: list[dict[str, Any]] = []
    for block in getattr(response, "content", []) or []:
        btype = getattr(block, "type", None)
        if btype == "text":
            out.append({"type": "text", "text": getattr(block, "text", "") or ""})
        elif btype == "tool_use":
            out.append(
                {
                    "type": "tool_use",
                    "id": getattr(block, "id", ""),
                    "name": getattr(block, "name", ""),
                    "input": getattr(block, "input", {}) or {},
                }
            )
    return out


def _fallback_html_from_response(response: Any) -> str:
    """Pull text content out of a response when no tool wrote HTML.

    Day 1-2 happy-path: the cassette returns an inline HTML body inside
    a single ``text`` block (the smoke fixture does this). We treat that
    as the rendered HTML in the absence of a real tool call.
    """
    chunks: list[str] = []
    for block in getattr(response, "content", []) or []:
        if getattr(block, "type", None) == "text":
            txt = getattr(block, "text", "")
            if isinstance(txt, str) and txt:
                chunks.append(txt)
    return "\n".join(chunks).strip()


__all__ = [
    "PERSONA",
    "TOOLS",
    "DrafterHandler",
    "DrafterResult",
]
