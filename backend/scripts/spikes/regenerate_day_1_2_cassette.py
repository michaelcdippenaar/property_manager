"""One-shot cassette regenerator for Phase 2 Day 1-2.

The Phase 1 Day 1-2 cassette was hand-crafted against a single Drafter
dispatch with a minimal system block. Phase 2 Day 1-2 reshapes the
harness's pipeline (Front Door + Drafter + Reviewer), which changes the
request hash and breaks the existing cassette.

This script:
  1. Loads the S1 scenario YAML.
  2. Runs the Front Door + builds the Drafter / Reviewer request kwargs
     exactly as the agents do.
  3. Hashes each request with the canonical cassette hasher.
  4. Writes a hand-crafted JSONL cassette under the canonical path
     ``backend/apps/leases/training/cassettes/<scenario>__<hash>.jsonl``
     containing the synthesised Drafter response (a tool_use that
     `add_clause`s an example clause, then an end_turn turn with the
     final rendered lease HTML) and the Reviewer response (a single
     forced `submit_audit_report` tool_use that passes).

Run with:

    cd backend && .venv/bin/python -m scripts.spikes.regenerate_day_1_2_cassette

No live API calls. No DB writes. Idempotent — re-running overwrites the
cassette deterministically.
"""
from __future__ import annotations

import json
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


def _build_drafter_request(context, dispatch) -> dict:
    """Mirror DrafterHandler.run's first dispatch kwargs."""
    messages = list(context.chat_history or ())
    if not messages or messages[-1].get("role") != "user":
        messages.append({"role": "user", "content": context.user_message})
    return {
        "model": DRAFTER_MODEL_DEFAULT,
        "max_tokens": 4096,
        "messages": messages,
        "system": dispatch.system_blocks,
        "tools": DRAFTER_TOOLS,
    }


def _build_drafter_response() -> dict:
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


def _build_reviewer_request(context, dispatch, document_html: str) -> dict:
    """Mirror ReviewerHandler.run's dispatch kwargs."""
    user_payload = (
        "Please audit the document below against SA rental law. "
        "Emit `submit_audit_report` with all findings. Do NOT emit "
        "any text blocks.\n\n"
        f"<document>\n{document_html or '(empty)'}\n</document>"
    )
    return {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": user_payload}],
        "system": dispatch.system_blocks,
        "tools": REVIEWER_TOOLS,
        "tool_choice": {"type": "tool", "name": "submit_audit_report"},
    }


def _build_reviewer_response() -> dict:
    return {
        "id": "msg_cassette_reviewer_S1",
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
            "input_tokens": 1480,
            "output_tokens": 120,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 1840,
        },
    }


def main() -> int:
    scenario, context, dispatch = _build_dispatch()

    drafter_req = _build_drafter_request(context, dispatch)
    drafter_hash = hash_request(drafter_req)
    drafter_resp = _build_drafter_response()
    drafter_entry = CassetteEntry(
        hash=drafter_hash,
        req={k: v for k, v in drafter_req.items() if k != "max_tokens"},
        resp=drafter_resp,
    )

    rendered_html = _DRAFTER_REPLY + " " + _DRAFTER_DOC_HTML
    reviewer_req = _build_reviewer_request(context, dispatch, rendered_html)
    reviewer_hash = hash_request(reviewer_req)
    reviewer_resp = _build_reviewer_response()
    reviewer_entry = CassetteEntry(
        hash=reviewer_hash,
        req={k: v for k, v in reviewer_req.items() if k != "max_tokens"},
        resp=reviewer_resp,
    )

    CASSETTE_DIR.mkdir(parents=True, exist_ok=True)
    cassette_path = (
        CASSETTE_DIR
        / f"{scenario.id}__{DAY_1_2_CORPUS_HASH}.jsonl"
    )
    with cassette_path.open("w", encoding="utf-8") as f:
        f.write(drafter_entry.to_jsonl() + "\n")
        f.write(reviewer_entry.to_jsonl() + "\n")

    print(f"Wrote {cassette_path}")
    print(f"  Drafter request hash: {drafter_hash}")
    print(f"  Reviewer request hash: {reviewer_hash}")
    print(
        f"  Drafter system blocks: {len(dispatch.system_blocks)}; "
        f"persona/merge/rag lens: "
        f"{len(dispatch._persona_text)}/{len(dispatch._merge_fields_text)}/{len(dispatch._rag_text)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
