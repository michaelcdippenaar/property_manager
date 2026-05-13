"""One-shot cassette regenerator for the lease-AI smoke battery.

The Wave 2A pipeline shape exercises the new multi-turn Reviewer loop
without forcing the Drafter to chain through multiple tool calls
(which would require a clause corpus seeded with one chunk per
SA-standard section — not yet available at the smoke-battery layer):

  * Drafter call 1: model returns one ``text`` block with the full
    rendered lease HTML and ``stop_reason='end_turn'``. The handler's
    fallback path lifts the HTML into ``DrafterResult.rendered_html``.
  * Reviewer call 1: ``tool_choice='auto'``; model returns
    ``tool_use(query_statute)`` — a representative pull tool call so
    the cassette exercises the multi-turn surface.
  * Reviewer call 2: ``tool_choice='auto'``; model returns
    ``tool_use(submit_audit_report)`` — the structured critique.

Total: 3 LLM calls per smoke run (Drafter + 2 Reviewer). The Reviewer
multi-turn exercises decision 22's grounded-finding path; the forced
final dispatch is unit-tested in ``test_reviewer.py``.

Run:
    cd backend && .venv/bin/python -m scripts.spikes.regenerate_day_1_2_cassette

No live API calls. No DB writes. Idempotent — re-running overwrites the
cassette deterministically.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

if __name__ == "__main__":
    # Bootstrap Django so apps.leases.* imports work.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    import django

    django.setup()


from apps.leases.agents.drafter import TOOLS as DRAFTER_TOOLS
from apps.leases.agents.reviewer import TOOLS as REVIEWER_TOOLS
from apps.leases.training.cassette import (
    DAY_1_2_CORPUS_HASH,
    CassetteEntry,
    hash_request,
)
from apps.leases.training.harness import (
    DRAFTER_MODEL_DEFAULT,
    LeaseTrainingHarness,
    Scenario,
)


SCENARIO_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "leases"
    / "training"
    / "fixtures"
    / "happy"
    / "generate-sectional-title-1-tenant-fixed.yaml"
)
CASSETTE_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "leases"
    / "training"
    / "cassettes"
)


_DRAFTER_DOC_HTML = (
    "<section><h2>PARTIES</h2><p>This lease is entered into between "
    "Alex Tester and {{ tenant_name }}, in compliance with RHA s5(3)(a)."
    "</p></section>"
    "<section><h2>PROPERTY</h2><p>The dwelling at 1 Test Way, "
    "Stellenbosch, forming part of Test Scheme — body corporate "
    "registered with CSOS — per RHA s5(3)(b).</p></section>"
    "<section><h2>TERM</h2><p>Fixed-term 12 months, in line with RHA "
    "s5(3)(d) and CPA s14.</p></section>"
    "<section><h2>RENT</h2><p>Monthly rent of R{{ monthly_rent }} "
    "payable in advance on the first business day of each month per "
    "RHA s5(3)(g).</p></section>"
    "<section><h2>DEPOSIT</h2><p>The deposit of R{{ deposit }} is held "
    "in an interest-bearing account; interest accrues to the Tenant "
    "per RHA s5(3)(e) and RHA s5(3)(f) (provisional).</p></section>"
    "<section><h2>POPIA CONSENT</h2><p>Tenant consents to processing "
    "under POPIA s11(1)(b) and POPIA s14.</p></section>"
    "<section><h2>SIGNATURES</h2><p>Signed at Stellenbosch on "
    "2026-05-15.</p></section>"
)


_DRAFTER_REPLY = "Generated the sectional-title lease as requested."



def _build_dispatch():
    scenario = Scenario.load(SCENARIO_PATH)
    harness = LeaseTrainingHarness(SCENARIO_PATH, mode="replay")
    context = harness._scenario_to_context(scenario)
    from apps.leases.agents import build_dispatch

    dispatch = build_dispatch(context)
    return scenario, context, dispatch


# ── Drafter call 1: user → tool_use(add_clause) ──────────────────────── #


def _drafter_messages_call1(context) -> list[dict]:
    messages = list(context.chat_history or ())
    if not messages or messages[-1].get("role") != "user":
        messages.append({"role": "user", "content": context.user_message})
    return messages


# ── Reviewer call 1: tool_use(query_statute) ────────────────────────── #


_REVIEWER_USER_PAYLOAD_TEMPLATE = (
    "Please audit the document below against SA rental law. "
    "You may use the pull tools (query_statute, query_clauses, "
    "query_case_law, list_pitfall_patterns, check_rha_compliance) "
    "to ground specific findings, then emit `submit_audit_report` "
    "with the final critique.\n\n"
    "<document>\n{document_html}\n</document>"
)


def _reviewer_user_payload(document_html: str) -> str:
    return _REVIEWER_USER_PAYLOAD_TEMPLATE.format(
        document_html=document_html or "(empty)"
    )


def _reviewer_req1(context, dispatch, document_html: str) -> dict:
    return {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 4096,
        "messages": [
            {"role": "user", "content": _reviewer_user_payload(document_html)}
        ],
        "system": dispatch.system_blocks,
        "tools": REVIEWER_TOOLS,
        "tool_choice": {"type": "auto"},
    }


def _reviewer_resp1() -> dict:
    return {
        "id": "msg_cassette_reviewer_S1_call1",
        "type": "message",
        "role": "assistant",
        "model": "claude-haiku-4-5-20251001",
        "stop_reason": "tool_use",
        "stop_sequence": None,
        "content": [
            {
                "type": "tool_use",
                "id": "toolu_reviewer_query_statute_1",
                "name": "query_statute",
                "input": {"citation": "RHA s7"},
            }
        ],
        "usage": {
            "input_tokens": 1480,
            "output_tokens": 40,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 1840,
        },
    }


# ── Reviewer call 2: submit_audit_report ─────────────────────────────── #


def _compute_reviewer_query_statute_result() -> str:
    """Compute the actual ``_execute_pull_tool('query_statute', ...)`` result.

    Same rationale as :func:`_compute_drafter_tool_result_summary` —
    hardcoding the JSON is fragile because it depends on whether the
    legal_rag corpus has a fact for ``RHA s7``. We call through the
    outer wrapper (not the inner exec) so the regen produces the same
    error-handled string the runner will see at replay time even when
    the underlying DB / corpus is unavailable.
    """
    from apps.leases.agents.reviewer import _execute_pull_tool

    return _execute_pull_tool(
        "query_statute", {"citation": "RHA s7"}, document_html=""
    )


def _reviewer_req2(
    context, dispatch, document_html: str, query_statute_result: str
) -> dict:
    return {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 4096,
        "messages": [
            {"role": "user", "content": _reviewer_user_payload(document_html)},
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_reviewer_query_statute_1",
                        "name": "query_statute",
                        "input": {"citation": "RHA s7"},
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_reviewer_query_statute_1",
                        "content": query_statute_result,
                    }
                ],
            },
        ],
        "system": dispatch.system_blocks,
        "tools": REVIEWER_TOOLS,
        "tool_choice": {"type": "auto"},
    }


def _reviewer_resp2() -> dict:
    return {
        "id": "msg_cassette_reviewer_S1_call2",
        "type": "message",
        "role": "assistant",
        "model": "claude-haiku-4-5-20251001",
        "stop_reason": "tool_use",
        "stop_sequence": None,
        "content": [
            {
                "type": "tool_use",
                "id": "toolu_cassette_S1_audit",
                "name": "submit_audit_report",
                "input": {
                    "verdict": "pass",
                    "summary": (
                        "Lease compliant against the RHA / CPA / POPIA "
                        "surface. No blocking findings."
                    ),
                    "statute_findings": [],
                    "case_law_findings": [],
                    "format_findings": [],
                },
            }
        ],
        "usage": {
            "input_tokens": 1520,
            "output_tokens": 120,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 1840,
        },
    }


# ── Main ─────────────────────────────────────────────────────────────── #


def _drafter_single_req(context, dispatch) -> dict:
    """Drafter sends a single text-only response with full HTML."""
    return {
        "model": DRAFTER_MODEL_DEFAULT,
        "max_tokens": 4096,
        "messages": _drafter_messages_call1(context),
        "system": dispatch.system_blocks,
        "tools": DRAFTER_TOOLS,
    }


def _drafter_single_resp() -> dict:
    """Drafter response: full HTML in a single text block, end_turn."""
    return {
        "id": "msg_cassette_drafter_S1",
        "type": "message",
        "role": "assistant",
        "model": DRAFTER_MODEL_DEFAULT,
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "content": [
            {"type": "text", "text": _DRAFTER_REPLY + " " + _DRAFTER_DOC_HTML},
        ],
        "usage": {
            "input_tokens": 1840,
            "output_tokens": 520,
            "cache_creation_input_tokens": 1840,
            "cache_read_input_tokens": 0,
        },
    }


def main() -> int:
    scenario, context, dispatch = _build_dispatch()

    rendered_html = _DRAFTER_REPLY + " " + _DRAFTER_DOC_HTML

    # Reviewer pull-tool result string — computed from the live helper so
    # the cassette stays aligned with whatever the indexed corpus
    # produces today. Re-record if the corpus changes.
    reviewer_query_statute_result = _compute_reviewer_query_statute_result()

    entries: list[CassetteEntry] = []
    summary_lines: list[str] = []

    # Drafter (single call: text only, full lease HTML).
    req = _drafter_single_req(context, dispatch)
    resp = _drafter_single_resp()
    h = hash_request(req)
    entries.append(
        CassetteEntry(
            hash=h, req={k: v for k, v in req.items() if k != "max_tokens"}, resp=resp
        )
    )
    summary_lines.append(f"  Drafter call hash: {h}")

    # Reviewer call 1 (auto → query_statute).
    req = _reviewer_req1(context, dispatch, rendered_html)
    resp = _reviewer_resp1()
    h = hash_request(req)
    entries.append(
        CassetteEntry(
            hash=h, req={k: v for k, v in req.items() if k != "max_tokens"}, resp=resp
        )
    )
    summary_lines.append(f"  Reviewer call 1 hash: {h}")

    # Reviewer call 2 (auto → submit_audit_report).
    req = _reviewer_req2(
        context, dispatch, rendered_html, reviewer_query_statute_result
    )
    resp = _reviewer_resp2()
    h = hash_request(req)
    entries.append(
        CassetteEntry(
            hash=h, req={k: v for k, v in req.items() if k != "max_tokens"}, resp=resp
        )
    )
    summary_lines.append(f"  Reviewer call 2 hash: {h}")

    CASSETTE_DIR.mkdir(parents=True, exist_ok=True)
    cassette_path = (
        CASSETTE_DIR
        / f"{scenario.id}__{DAY_1_2_CORPUS_HASH}.jsonl"
    )
    with cassette_path.open("w", encoding="utf-8") as f:
        for entry in entries:
            f.write(entry.to_jsonl() + "\n")

    print(f"Wrote {cassette_path}")
    for line in summary_lines:
        print(line)
    print(
        f"  Drafter system blocks: {len(dispatch.system_blocks)}; "
        f"persona/merge/rag lens: "
        f"{len(dispatch._persona_text)}/{len(dispatch._merge_fields_text)}/{len(dispatch._rag_text)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
