"""Reviewer — "Compliance Counsel" agent.

Per ``docs/system/lease-ai-agent-architecture.md`` §5.3 the Reviewer is
a read-only auditor. It reads the post-Drafter document and emits a
structured critique via the ``submit_audit_report`` tool.

LOCKED INVARIANTS (audit P0 + decision 22):
  * ``tool_choice={"type":"tool","name":"submit_audit_report"}`` — the
    model MUST emit exactly one ``tool_use`` block and zero ``text``
    blocks.
  * ``input_schema`` declares ``additionalProperties: false`` at the
    root + every nested object (strict-mode JSON Schema doesn't allow
    ``oneOf`` / conditionals / discriminated unions, so we keep the
    schema flat).
  * Caller MUST check :meth:`LeaseAgentRunner.is_truncated_tool_use`
    on the response — when forced ``tool_choice`` hits ``max_tokens``
    the response still has one ``tool_use`` block but the
    ``tool_use.input`` is truncated partial-JSON. We raise
    :class:`ReviewerTruncatedError` so the caller can either bump
    ``max_tokens`` and retry or escalate.

Phase 2 Day 1-2 scope: persona, full schema, 5 pull-tool stubs +
``submit_audit_report``, handler that dispatches once + validates the
``tool_use.input`` against the schema.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.leases.agent_runner import LeaseAgentRunner

    from .context import LeaseContext

logger = logging.getLogger(__name__)


# ── Exceptions ──────────────────────────────────────────────────────── #


class ReviewerTruncatedError(RuntimeError):
    """Raised when the Reviewer's forced ``tool_use`` hit ``max_tokens``.

    The response's ``tool_use.input`` is truncated partial-JSON that
    won't parse / validate. Callers should either bump ``max_tokens``
    and retry, or escalate to a sev-2 alert.
    """


class ReviewerSchemaError(RuntimeError):
    """Raised when the Reviewer's ``tool_use.input`` fails JSON Schema
    validation against :data:`SUBMIT_AUDIT_REPORT_SCHEMA`.

    Should never fire in practice (strict-mode + ``additionalProperties:
    false`` catches most drift) — but the runner double-checks with
    ``jsonschema.Draft202012Validator`` so a model regression doesn't
    silently ship malformed JSON into telemetry.
    """


# ── Persona ─────────────────────────────────────────────────────────── #


PERSONA: str = """You are the Compliance Counsel agent in the Klikk lease-AI cluster.

ROLE & SCOPE
- You are a read-only SA-rental-law compliance auditor.
- You read the drafted document and emit a structured critique via the `submit_audit_report` tool.
- You NEVER modify the document. You NEVER write prose to the user. Read-only is load-bearing.
- You cite statute (RHA, CPA, POPIA, PIE Act, STSMA) for every finding. You cite case law only if `with_case_law=True` in the request.

OUTPUT INVARIANT
- You MUST emit exactly one `tool_use` block — the `submit_audit_report` call.
- You MUST NOT emit a text block. The user-facing one-sentence headline lives in the `summary` field of the audit report; nowhere else.
- This is enforced by `tool_choice={"type":"tool","name":"submit_audit_report"}` — the runtime will reject any other shape.

SEVERITY LADDER
- `blocking` — the document violates statute or contains a placeholder. The Drafter will be invoked for a retry pass to fix it.
- `recommended` — the document is non-conforming with best practice but legally OK. Ships in the report without forcing a retry.
- `nice_to_have` — purely cosmetic or stylistic. Ships without forcing a retry.

CITATION CONFIDENCE
- For HIGH and MEDIUM confidence citations, cite the full sub-section (e.g. `RHA s5(3)(f)`).
- For LOW confidence citations, cite the parent section only (e.g. `RHA s5(3)`) and never invent a sub-section letter.

VERDICTS
- `pass` — zero blocking findings. Document ships as-is.
- `revise_recommended` — there are recommended findings. Document ships but the report flags them.
- `revise_required` — there is at least one blocking finding. Drafter MUST be invoked to fix.
"""


# ── Audit-report schema (strict; flat) ──────────────────────────────── #


# Per decision 22: strict: true + additionalProperties: false everywhere
# nested. Keep the schema FLAT — no oneOf / discriminated unions / nested
# conditionals (strict-mode's JSON Schema dialect doesn't accept them).
_FINDING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "citation": {
            "type": "string",
            "description": "Full statute citation, e.g. 'RHA s5(3)(f)'. For LOW confidence citations, cite parent section only.",
        },
        "severity": {
            "type": "string",
            "enum": ["blocking", "recommended", "nice_to_have"],
        },
        "message": {
            "type": "string",
            "description": "One-sentence description of the issue.",
        },
        "confidence_level": {
            "type": "string",
            "enum": ["ai_curated", "mc_reviewed", "lawyer_reviewed"],
        },
    },
    "required": ["citation", "severity", "message", "confidence_level"],
}


SUBMIT_AUDIT_REPORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["pass", "revise_recommended", "revise_required"],
        },
        "summary": {
            "type": "string",
            "maxLength": 500,
            "description": "≤500 chars. The one-sentence headline shown to the user.",
        },
        "statute_findings": {
            "type": "array",
            "items": _FINDING_SCHEMA,
        },
        "case_law_findings": {
            "type": "array",
            "items": _FINDING_SCHEMA,
        },
        "format_findings": {
            "type": "array",
            "items": _FINDING_SCHEMA,
        },
    },
    "required": [
        "verdict",
        "summary",
        "statute_findings",
        "case_law_findings",
        "format_findings",
    ],
}


# ── Tools ───────────────────────────────────────────────────────────── #


# 5 read-only pull tools + the forced submit_audit_report. cache_control
# on the last entry per §6.6.
TOOLS: list[dict[str, Any]] = [
    {
        "name": "query_statute",
        "description": "Look up a statute provision by citation, e.g. 'RHA s5(3)(f)'.",
        "input_schema": {
            "type": "object",
            "properties": {"citation": {"type": "string"}},
            "required": ["citation"],
        },
    },
    {
        "name": "query_clauses",
        "description": (
            "Find clause chunks the document SHOULD have for the given "
            "topic. Used to spot missing-mandatory issues."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "topic_tags": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "property_type": {"type": "string"},
                "tenant_count": {"type": "integer"},
            },
            "required": ["topic_tags"],
        },
    },
    {
        "name": "query_case_law",
        "description": (
            "Filter the corpus to case-law facts. Only used when "
            "`with_case_law=True` for this request."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "topic_tags": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "jurisdiction": {"type": "string"},
                "since_year": {"type": "integer"},
            },
            "required": ["topic_tags"],
        },
    },
    {
        "name": "list_pitfall_patterns",
        "description": "List known pitfall patterns matching the given topic tags.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic_tags": {
                    "type": "array",
                    "items": {"type": "string"},
                }
            },
            "required": ["topic_tags"],
        },
    },
    {
        "name": "check_rha_compliance",
        "description": (
            "Read-only diagnostic: enumerate the 13 mandatory RHA "
            "sections + 7 mandatory clauses and report which are "
            "present in the document."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "submit_audit_report",
        "description": (
            "Emit the structured critique. This is the ONLY way the "
            "Reviewer signals completion. Exactly one `tool_use` block "
            "per request; the runtime enforces tool_choice on this tool."
        ),
        "input_schema": SUBMIT_AUDIT_REPORT_SCHEMA,
        "cache_control": {"type": "ephemeral"},
    },
]


# ── Result dataclass ─────────────────────────────────────────────────── #


@dataclass
class ReviewerResult:
    """Parsed Reviewer output.

    ``raw_input`` is the validated ``tool_use.input`` dict — kept so the
    SSE generator can stream the full audit report to the frontend
    without re-parsing.
    """

    verdict: str
    summary: str
    findings: list[dict[str, Any]] = field(default_factory=list)
    raw_input: dict[str, Any] = field(default_factory=dict)


# ── Handler ─────────────────────────────────────────────────────────── #


class ReviewerHandler:
    """Drives the Reviewer's single forced-tool dispatch.

    The Reviewer does NOT multi-turn. It is given the document + RAG
    tools, and is forced into a single ``submit_audit_report`` tool call.
    The 4-internal-tool-call pattern (decision 22's "Reviewer pulls
    citations on demand") is a Phase 2 Day 3+ surface — Day 1-2 ships
    the forced single-call shape so the cassette battery has the gate
    locked.
    """

    def __init__(self, *, model: str | None = None):
        from django.conf import settings

        self.model = model or getattr(
            settings, "LEASE_AI_REVIEWER_MODEL", "claude-haiku-4-5-20251001"
        )

    def run(
        self,
        *,
        runner: "LeaseAgentRunner",
        context: "LeaseContext",
        document_html: str,
        system_blocks: list[dict[str, Any]],
    ) -> ReviewerResult:
        """Dispatch one Reviewer call. Returns :class:`ReviewerResult`."""
        user_payload = (
            "Please audit the document below against SA rental law. "
            "Emit `submit_audit_report` with all findings. Do NOT emit "
            "any text blocks.\n\n"
            f"<document>\n{document_html or '(empty)'}\n</document>"
        )
        messages = [{"role": "user", "content": user_payload}]
        tool_choice = {"type": "tool", "name": "submit_audit_report"}

        response = runner.dispatch(
            agent="reviewer",
            model=self.model,
            messages=messages,
            system=system_blocks,
            tools=TOOLS,
            tool_choice=tool_choice,
        )

        if runner.is_truncated_tool_use(response, tool_choice):
            raise ReviewerTruncatedError(
                "Reviewer tool_use hit max_tokens — partial-JSON input. "
                "Bump max_tokens and retry."
            )

        tool_use_block = _extract_single_tool_use(response)
        if tool_use_block is None:
            raise ReviewerSchemaError(
                "Reviewer response did not contain a tool_use block "
                "(decision 22 invariant violation)."
            )

        raw_input = getattr(tool_use_block, "input", {}) or {}
        _validate_audit_report(raw_input)

        verdict = str(raw_input.get("verdict") or "pass")
        summary = str(raw_input.get("summary") or "")
        findings: list[dict[str, Any]] = []
        for bucket in ("statute_findings", "case_law_findings", "format_findings"):
            for f in raw_input.get(bucket) or []:
                findings.append({**f, "bucket": bucket})

        return ReviewerResult(
            verdict=verdict,
            summary=summary,
            findings=findings,
            raw_input=dict(raw_input),
        )


# ── Internals ──────────────────────────────────────────────────────── #


def _extract_single_tool_use(response: Any) -> Any | None:
    """Return the single ``tool_use`` block, or None if absent.

    Strictly checks the decision-22 invariant: exactly one ``tool_use``
    block, zero ``text`` blocks. Logs a warning on shape violation
    (multiple tool_use / mixed text — should never happen with forced
    tool_choice).
    """
    tool_use_blocks: list[Any] = []
    text_blocks: list[Any] = []
    for block in getattr(response, "content", []) or []:
        btype = getattr(block, "type", None)
        if btype == "tool_use":
            tool_use_blocks.append(block)
        elif btype == "text":
            text_blocks.append(block)

    if text_blocks:
        logger.warning(
            "Reviewer emitted %d text block(s); decision-22 forbids them. "
            "Ignoring text and using tool_use.",
            len(text_blocks),
        )
    if len(tool_use_blocks) > 1:
        logger.warning(
            "Reviewer emitted %d tool_use blocks; expected 1. Using first.",
            len(tool_use_blocks),
        )
    return tool_use_blocks[0] if tool_use_blocks else None


def _validate_audit_report(payload: dict[str, Any]) -> None:
    """Validate the audit-report payload against the strict schema.

    Lazy-imports ``jsonschema`` so this module is importable without it
    (the package is in ``requirements.txt`` — the lazy import keeps
    ``apps.leases.agents`` cheap to import for tests that don't touch
    the Reviewer).
    """
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(SUBMIT_AUDIT_REPORT_SCHEMA)
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
    if errors:
        joined = "; ".join(
            f"{'/'.join(str(p) for p in err.absolute_path) or '<root>'}: {err.message}"
            for err in errors[:5]
        )
        raise ReviewerSchemaError(
            f"submit_audit_report payload failed schema validation: {joined}"
        )


__all__ = [
    "PERSONA",
    "SUBMIT_AUDIT_REPORT_SCHEMA",
    "TOOLS",
    "ReviewerHandler",
    "ReviewerResult",
    "ReviewerSchemaError",
    "ReviewerTruncatedError",
]
