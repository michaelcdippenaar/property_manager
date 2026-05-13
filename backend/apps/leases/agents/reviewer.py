"""Reviewer — "Compliance Counsel" agent.

Per ``docs/system/lease-ai-agent-architecture.md`` §5.3 the Reviewer is
a read-only auditor. It reads the post-Drafter document and emits a
structured critique via the ``submit_audit_report`` tool.

LOCKED INVARIANTS (audit P0 + decision 22):
  * Final dispatch sets
    ``tool_choice={"type":"tool","name":"submit_audit_report"}`` — at
    that moment the model MUST emit exactly one ``tool_use`` block.
  * ``input_schema`` declares ``additionalProperties: false`` at the
    root + every nested object (strict-mode JSON Schema doesn't allow
    ``oneOf`` / conditionals / discriminated unions, so we keep the
    schema flat).
  * Caller MUST check :meth:`LeaseAgentRunner.is_truncated_tool_use`
    on the forced response — when forced ``tool_choice`` hits
    ``max_tokens`` the response still has one ``tool_use`` block but
    the ``tool_use.input`` is truncated partial-JSON. We raise
    :class:`ReviewerTruncatedError` so the caller can either bump
    ``max_tokens`` and retry or escalate.

Wave 2A scope: the Reviewer now multi-turns with the 5 pull tools
(``query_statute`` / ``query_clauses`` / ``query_case_law`` /
``list_pitfall_patterns`` / ``check_rha_compliance``) BEFORE its final
forced ``submit_audit_report`` call. Max 3 internal turns (decision 10
analogue). The first ``MAX_INTERNAL_TURNS - 1`` turns dispatch with
``tool_choice='auto'``; the final turn forces ``submit_audit_report``.
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


class ReviewerInvalidToolError(RuntimeError):
    """Raised when the Reviewer emits a ``tool_use`` for an unknown tool.

    Defends against the failure class where the model hallucinates a tool
    name that isn't in :data:`TOOLS`. We surface the offending name so
    diagnostics can show what the model tried to call.
    """

    def __init__(self, tool_name: str, message: str = ""):
        self.tool_name = tool_name
        super().__init__(
            message or f"Reviewer emitted unknown tool {tool_name!r}; expected one "
            f"of: query_statute / query_clauses / query_case_law / "
            f"list_pitfall_patterns / check_rha_compliance / submit_audit_report."
        )


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

    ``pull_tool_calls`` is the chronological list of pull-tool dispatches
    the Reviewer issued before submitting the audit report — each entry
    is ``{"name", "input", "result_summary"}`` so diagnostics can show
    which RAG facts the model consulted.

    ``internal_turns`` is the number of LLM dispatches issued for this
    Reviewer pass (1..MAX_INTERNAL_TURNS). ``terminated_reason`` reports
    why the loop ended: ``submit_audit_report`` / ``internal_turn_cap`` /
    ``stale_progress``.
    """

    verdict: str
    summary: str
    findings: list[dict[str, Any]] = field(default_factory=list)
    raw_input: dict[str, Any] = field(default_factory=dict)
    pull_tool_calls: list[dict[str, Any]] = field(default_factory=list)
    internal_turns: int = 1
    terminated_reason: str = "submit_audit_report"


# ── Handler ─────────────────────────────────────────────────────────── #


class ReviewerHandler:
    """Drives the Reviewer's multi-turn pull-tool loop.

    The Reviewer is given the post-Drafter document plus the 5 read-only
    pull tools (``query_statute`` / ``query_clauses`` / ``query_case_law``
    / ``list_pitfall_patterns`` / ``check_rha_compliance``) and the
    terminal ``submit_audit_report``. It iterates up to
    :attr:`MAX_INTERNAL_TURNS` times, executing pull-tool calls between
    turns. The final turn ALWAYS forces ``tool_choice`` on
    ``submit_audit_report`` so the loop is guaranteed to terminate with
    a structured payload (decision 22 invariant).

    Per-turn behaviour:
      * Turns ``1..MAX-1``: dispatch with ``tool_choice='auto'``. The
        model may emit a pull-tool ``tool_use`` block (we execute it via
        :mod:`apps.legal_rag.queries` / :mod:`apps.leases.lease_law_corpus_queries`
        and feed the result back), OR emit ``submit_audit_report`` (we
        accept it and end the loop), OR emit text only (we force the
        next turn to submit).
      * Final turn: forced ``submit_audit_report``. ``is_truncated_tool_use``
        is checked and raises :class:`ReviewerTruncatedError` on
        ``stop_reason='max_tokens'``.

    Unknown tool names raise :class:`ReviewerInvalidToolError`.
    """

    MAX_INTERNAL_TURNS: int = 3

    # Pull tools the Reviewer is allowed to call between turns. Unknown
    # tool names raise ReviewerInvalidToolError.
    _PULL_TOOL_NAMES: frozenset[str] = frozenset(
        {
            "query_statute",
            "query_clauses",
            "query_case_law",
            "list_pitfall_patterns",
            "check_rha_compliance",
        }
    )

    _SUBMIT_TOOL_NAME: str = "submit_audit_report"

    def __init__(self, *, model: str | None = None):
        from django.conf import settings

        self.model = model or getattr(
            settings, "LEASE_AI_REVIEWER_MODEL", "claude-haiku-4-5-20251001"
        )

    # ── Public surface ───────────────────────────────────────────────── #

    def run(
        self,
        *,
        runner: "LeaseAgentRunner",
        context: "LeaseContext",
        document_html: str,
        system_blocks: list[dict[str, Any]],
    ) -> ReviewerResult:
        """Run the Reviewer loop. Returns :class:`ReviewerResult`."""
        user_payload = (
            "Please audit the document below against SA rental law. "
            "You may use the pull tools (query_statute, query_clauses, "
            "query_case_law, list_pitfall_patterns, check_rha_compliance) "
            "to ground specific findings, then emit `submit_audit_report` "
            "with the final critique.\n\n"
            f"<document>\n{document_html or '(empty)'}\n</document>"
        )
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": user_payload}
        ]
        pull_tool_calls: list[dict[str, Any]] = []
        force_submit_next = False
        terminated_reason = self._SUBMIT_TOOL_NAME

        for turn in range(self.MAX_INTERNAL_TURNS):
            is_last_turn = turn == self.MAX_INTERNAL_TURNS - 1
            force_submit = is_last_turn or force_submit_next

            tool_choice: dict[str, Any] | None = (
                {"type": "tool", "name": self._SUBMIT_TOOL_NAME}
                if force_submit
                else {"type": "auto"}
            )

            response = runner.dispatch(
                agent="reviewer",
                model=self.model,
                messages=messages,
                system=system_blocks,
                tools=TOOLS,
                tool_choice=tool_choice,
            )

            # When we forced submit, check truncation FIRST — a truncated
            # tool_use is the failure class decision 22 calls out.
            if force_submit and runner.is_truncated_tool_use(
                response, tool_choice
            ):
                raise ReviewerTruncatedError(
                    "Reviewer tool_use hit max_tokens — partial-JSON input. "
                    "Bump max_tokens and retry."
                )

            tool_use_blocks = _collect_tool_use_blocks(response)
            submit_block = _find_block_by_name(
                tool_use_blocks, self._SUBMIT_TOOL_NAME
            )

            if submit_block is not None:
                # Reviewer self-decided (or was forced) to submit. End loop.
                if not force_submit:
                    terminated_reason = self._SUBMIT_TOOL_NAME
                return self._finalise_submission(
                    submit_block,
                    pull_tool_calls=pull_tool_calls,
                    internal_turns=turn + 1,
                    terminated_reason=terminated_reason,
                )

            # No submit_audit_report this turn. If the loop forced submit
            # and the model still didn't comply, that's a schema violation.
            if force_submit:
                raise ReviewerSchemaError(
                    "Reviewer response did not contain a "
                    f"{self._SUBMIT_TOOL_NAME} tool_use block even with "
                    "forced tool_choice (decision 22 invariant violation)."
                )

            if not tool_use_blocks:
                # Reviewer emitted text only — force submit on next turn.
                logger.info(
                    "Reviewer turn %d emitted no tool_use; forcing submit on next turn.",
                    turn + 1,
                )
                force_submit_next = True
                terminated_reason = "stale_progress"
                messages.append(
                    {
                        "role": "assistant",
                        "content": _content_for_history(response),
                    }
                )
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Please emit `submit_audit_report` now with the "
                            "structured critique. Do not call any more pull tools."
                        ),
                    }
                )
                continue

            # Pull-tool turn: execute every pull tool the model called.
            tool_results: list[dict[str, Any]] = []
            for block in tool_use_blocks:
                name = getattr(block, "name", "")
                if name not in self._PULL_TOOL_NAMES:
                    raise ReviewerInvalidToolError(name)
                inp = getattr(block, "input", {}) or {}
                result_summary = _execute_pull_tool(name, inp, document_html)
                pull_tool_calls.append(
                    {
                        "name": name,
                        "input": inp,
                        "result_summary": result_summary,
                    }
                )
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": getattr(block, "id", ""),
                        "content": result_summary,
                    }
                )

            messages.append(
                {
                    "role": "assistant",
                    "content": _content_for_history(response),
                }
            )
            messages.append({"role": "user", "content": tool_results})

        # Loop fell through without break (no return) — schema violation.
        # Shouldn't be reachable because the last iteration force-submits
        # and either returns or raises ReviewerSchemaError above.
        raise ReviewerSchemaError(
            "Reviewer multi-turn loop exited without submit_audit_report."
        )

    # ── Internals ───────────────────────────────────────────────────── #

    def _finalise_submission(
        self,
        submit_block: Any,
        *,
        pull_tool_calls: list[dict[str, Any]],
        internal_turns: int,
        terminated_reason: str,
    ) -> ReviewerResult:
        """Validate the submit_audit_report payload + build the result."""
        raw_input = getattr(submit_block, "input", {}) or {}
        _validate_audit_report(raw_input)

        verdict = str(raw_input.get("verdict") or "pass")
        summary = str(raw_input.get("summary") or "")
        findings: list[dict[str, Any]] = []
        for bucket in (
            "statute_findings",
            "case_law_findings",
            "format_findings",
        ):
            for f in raw_input.get(bucket) or []:
                findings.append({**f, "bucket": bucket})

        return ReviewerResult(
            verdict=verdict,
            summary=summary,
            findings=findings,
            raw_input=dict(raw_input),
            pull_tool_calls=pull_tool_calls,
            internal_turns=internal_turns,
            terminated_reason=terminated_reason,
        )


# ── Internals ──────────────────────────────────────────────────────── #


def _collect_tool_use_blocks(response: Any) -> list[Any]:
    """Return every ``tool_use`` block on ``response.content``."""
    out: list[Any] = []
    for block in getattr(response, "content", []) or []:
        if getattr(block, "type", None) == "tool_use":
            out.append(block)
    return out


def _find_block_by_name(blocks: list[Any], name: str) -> Any | None:
    """Return the first ``tool_use`` block whose ``name`` matches."""
    for block in blocks:
        if getattr(block, "name", "") == name:
            return block
    return None


def _content_for_history(response: Any) -> list[dict[str, Any]]:
    """Re-serialise the response's content blocks for the next dispatch.

    The next ``messages.create`` call needs the assistant turn shaped as
    plain dicts the SDK accepts (``text`` / ``tool_use``). Tolerates the
    cassette's ``SimpleNamespace`` blocks plus real SDK pydantic shapes.
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


def _execute_pull_tool(name: str, inp: dict[str, Any], document_html: str) -> str:
    """Dispatch a Reviewer pull-tool call to the underlying RAG API.

    Returns a JSON-stringified summary the model can consume as a
    ``tool_result``. All exceptions are caught and surfaced as compact
    error strings (rather than crashing the request) — Reviewer is
    read-only so failures should never abort the audit.
    """
    try:
        if name == "query_statute":
            return _exec_query_statute(inp)
        if name == "query_clauses":
            return _exec_query_clauses(inp)
        if name == "query_case_law":
            return _exec_query_case_law(inp)
        if name == "list_pitfall_patterns":
            return _exec_list_pitfall_patterns(inp)
        if name == "check_rha_compliance":
            return _exec_check_rha_compliance(document_html)
    except Exception:  # noqa: BLE001
        logger.exception("Reviewer pull tool %s raised; returning error summary.", name)
        return f'{{"error": "pull tool {name!r} failed; see server logs."}}'
    return f'{{"error": "unsupported pull tool {name!r}"}}'


def _exec_query_statute(inp: dict[str, Any]) -> str:
    """Look up one statute provision; serialise the LegalFact compactly."""
    import json as _json

    from apps.legal_rag.exceptions import LegalFactNotFound
    from apps.legal_rag.queries import query_statute

    citation = str(inp.get("citation") or "").strip()
    if not citation:
        return '{"error": "citation is required"}'
    try:
        fact = query_statute(citation)
    except LegalFactNotFound as exc:
        return _json.dumps({"error": str(exc), "citation": citation})

    return _json.dumps(_legal_fact_to_dict(fact))


def _exec_query_clauses(inp: dict[str, Any]) -> str:
    """Pull clause chunks the document SHOULD have."""
    import json as _json

    from apps.leases.lease_law_corpus_queries import query_clauses

    topic_tags = inp.get("topic_tags") or []
    property_type = inp.get("property_type")
    tenant_count = inp.get("tenant_count")

    chunks = query_clauses(
        topic_tags=list(topic_tags) or None,
        property_type=property_type,
        tenant_count=tenant_count,
        k=10,
    )
    payload = [
        {
            "id": c.id,
            "clause_title": c.clause_title,
            "topic_tags": list(c.topic_tags),
            "related_citations": list(c.related_citations),
            "citation_confidence": c.citation_confidence,
            "legal_provisional": c.legal_provisional,
        }
        for c in chunks
    ]
    return _json.dumps({"results": payload, "count": len(payload)})


def _exec_query_case_law(inp: dict[str, Any]) -> str:
    """Filter the legal corpus to ``type='case_law'``."""
    import json as _json

    from apps.legal_rag.queries import query_case_law

    facts = query_case_law(
        topic_tags=list(inp.get("topic_tags") or []) or None,
        jurisdiction=inp.get("jurisdiction"),
        since_year=inp.get("since_year"),
        k=10,
    )
    return _json.dumps(
        {
            "results": [_legal_fact_to_dict(f) for f in facts],
            "count": len(facts),
        }
    )


def _exec_list_pitfall_patterns(inp: dict[str, Any]) -> str:
    """List pitfall patterns matching the given topic tags."""
    import json as _json

    from apps.legal_rag.queries import list_pitfall_patterns

    facts = list_pitfall_patterns(
        topic_tags=list(inp.get("topic_tags") or []) or None
    )
    return _json.dumps(
        {
            "results": [_legal_fact_to_dict(f) for f in facts],
            "count": len(facts),
        }
    )


def _exec_check_rha_compliance(document_html: str) -> str:
    """Read-only diagnostic: enumerate mandatory RHA sections.

    Day 1-2 stub returns a small structured summary listing whether the
    13 mandatory section headings (PARTIES / PROPERTY / TERM / RENT /
    DEPOSIT / MAINTENANCE / DEFAULT / TERMINATION / DISPUTE /
    SIGNATURES) are present in the rendered HTML. Phase 3 will expand to
    the full 13-section + 7-clause matrix from the architecture doc.
    """
    import json as _json

    mandatory = (
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
    upper_html = (document_html or "").upper()
    presence = {section: section in upper_html for section in mandatory}
    return _json.dumps(
        {
            "section_presence": presence,
            "missing": [s for s, present in presence.items() if not present],
        }
    )


def _legal_fact_to_dict(fact: Any) -> dict[str, Any]:
    """Compact dict-ify a :class:`LegalFact` for tool_result serialisation.

    We only ship the fields a Reviewer needs to decide on a finding —
    citation_string, plain_english_summary, citation_confidence,
    legal_provisional, topic_tags. The full LegalFact is overkill in
    a tool_result and would burn output tokens.
    """
    return {
        "concept_id": getattr(fact, "concept_id", ""),
        "citation_string": getattr(fact, "citation_string", ""),
        "plain_english_summary": getattr(fact, "plain_english_summary", ""),
        "citation_confidence": getattr(fact, "citation_confidence", ""),
        "legal_provisional": bool(getattr(fact, "legal_provisional", False)),
        "topic_tags": list(getattr(fact, "topic_tags", ()) or ()),
    }


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
    "ReviewerInvalidToolError",
    "ReviewerResult",
    "ReviewerSchemaError",
    "ReviewerTruncatedError",
]
