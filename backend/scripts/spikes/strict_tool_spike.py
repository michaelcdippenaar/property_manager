"""
Phase 0.5 spike — Reviewer forced-tool-output validation.

Validates decision 22 in `docs/system/lease-ai-agent-architecture.md`: when the
Reviewer call is configured with:

    tool_choice = {"type": "tool", "name": "submit_audit_report"}
    + strict input_schema (additionalProperties: false at top + every nested obj)

the model emits exactly ONE tool_use block and ZERO text blocks. The user-facing
one-liner lives in the `summary` field of the structured critique; there is no
separate prose "reply" from the Reviewer.

This is load-bearing. If the Reviewer can still emit prose alongside the tool
call, the LeaseAgentRunner can't trust a single channel for audit output, and
the UX contract in §10.1 ("audit-report expander below the reply") breaks.

Pass criteria (BOTH inputs):
    stop_reason == "tool_use"
    content has exactly one tool_use block
    zero text blocks
    parsed input passes jsonschema.validate() — strict catches extras

We test two inputs:
    1. A normal audit request.
    2. A pathological prompt that explicitly asks for "verbose context" to
       tempt extra-field / prose emission.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    backend/.venv/bin/python backend/scripts/spikes/strict_tool_spike.py
"""
from __future__ import annotations

import os
import sys
from typing import Any

try:
    import anthropic
    from jsonschema import Draft202012Validator
except ImportError as e:
    print(f"ERROR: missing dependency: {e}", file=sys.stderr)
    sys.exit(1)


# Haiku 4.5 — Reviewer model per decision 23.
REVIEWER_MODEL = "claude-haiku-4-5-20251001"


# Strict submit_audit_report schema per §7.2 + decision 22.
# Note: `strict: true` for tool calls restricts the JSON Schema dialect — no
# oneOf, no conditionals, no discriminated unions. We keep the schema flat.
SUBMIT_AUDIT_REPORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["pass", "revise_recommended", "revise_required"],
            "description": "Overall verdict. `revise_required` = blocking findings present.",
        },
        "summary": {
            "type": "string",
            "maxLength": 500,
            "description": "One-sentence headline shown to the user.",
        },
        "statute_findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "citation": {"type": "string"},
                    "severity": {
                        "type": "string",
                        "enum": ["blocking", "recommended", "nice_to_have"],
                    },
                    "message": {"type": "string"},
                },
                "required": ["citation", "severity", "message"],
            },
        },
        "case_law_findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "case_ref": {"type": "string"},
                    "severity": {
                        "type": "string",
                        "enum": ["blocking", "recommended", "nice_to_have"],
                    },
                    "message": {"type": "string"},
                },
                "required": ["case_ref", "severity", "message"],
            },
        },
        "format_findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "section": {"type": "string"},
                    "severity": {
                        "type": "string",
                        "enum": ["blocking", "recommended", "nice_to_have"],
                    },
                    "message": {"type": "string"},
                },
                "required": ["section", "severity", "message"],
            },
        },
    },
    "required": ["verdict", "summary", "statute_findings"],
}


REVIEWER_PERSONA = """You are a read-only SA-rental-law compliance auditor.
You read the drafted lease and emit a structured critique via submit_audit_report.
You NEVER modify the document. You cite statute (RHA / CPA / POPIA / PIE Act) for
every finding. The user-facing one-sentence headline lives in the `summary` field.
You do NOT emit prose alongside the tool call — the structured critique is the
ONLY output channel.
"""

REPRESENTATIVE_LEASE_BODY = """LEASE OF DWELLING

1. PARTIES
   Landlord: John Smith (ID 7501015432087), 12 Main Road, Stellenbosch.
   Tenant:  Jane Doe   (ID 9203124567083), to take occupation of the dwelling
            described in clause 2.

2. PROPERTY
   The dwelling at 45 Oak Street, Mowbray, Cape Town.

3. RENT
   Monthly rent: R12,500.00, payable on the 1st of each month.

4. DEPOSIT
   The Tenant shall pay a deposit of R12,500.00. The deposit will be held by
   the Landlord. The deposit will be refunded as soon as practicable after
   the lease ends.

5. TERM
   Commencement: 1 June 2026. Expiry: 31 May 2027.

6. DEFAULT
   On default the Landlord may immediately enter the premises and remove the
   Tenant's possessions.

7. SIGNATURES
   Signed at __________ on __________.
   Landlord: __________________
   Tenant:   __________________
"""


def call_reviewer(*, client: anthropic.Anthropic, user_prompt: str) -> Any:
    """Make the Reviewer messages.create call with strict forced tool output."""
    return client.messages.create(
        model=REVIEWER_MODEL,
        max_tokens=4096,
        tools=[
            {
                "name": "submit_audit_report",
                "description": (
                    "Submit the structured compliance critique. This is the ONLY "
                    "channel for output. Do not emit text alongside this call."
                ),
                "input_schema": SUBMIT_AUDIT_REPORT_SCHEMA,
            }
        ],
        tool_choice={"type": "tool", "name": "submit_audit_report"},
        system=REVIEWER_PERSONA,
        messages=[{"role": "user", "content": user_prompt}],
    )


def analyse(label: str, resp: Any) -> dict[str, Any]:
    """Return per-call analysis. Asserts the strict-output invariants."""
    text_blocks = [b for b in resp.content if b.type == "text"]
    tool_use_blocks = [b for b in resp.content if b.type == "tool_use"]

    result = {
        "label": label,
        "stop_reason": resp.stop_reason,
        "n_text_blocks": len(text_blocks),
        "n_tool_use_blocks": len(tool_use_blocks),
        "text_block_previews": [b.text[:80] for b in text_blocks],
        "schema_errors": [],
        "passed": True,
    }

    # Hard invariants from decision 22.
    if resp.stop_reason != "tool_use":
        result["passed"] = False
        result["reason"] = f"stop_reason != tool_use (got {resp.stop_reason})"
    elif len(tool_use_blocks) != 1:
        result["passed"] = False
        result["reason"] = f"expected exactly 1 tool_use, got {len(tool_use_blocks)}"
    elif len(text_blocks) != 0:
        result["passed"] = False
        result["reason"] = f"expected 0 text blocks, got {len(text_blocks)}"
    else:
        # Validate the tool input against the schema. Strict mode SHOULD make
        # extras impossible; this assertion catches any drift.
        tool_input = tool_use_blocks[0].input
        validator = Draft202012Validator(SUBMIT_AUDIT_REPORT_SCHEMA)
        errors = sorted(validator.iter_errors(tool_input), key=lambda e: e.path)
        if errors:
            result["passed"] = False
            result["schema_errors"] = [
                f"{list(err.absolute_path)}: {err.message}" for err in errors
            ]
            result["reason"] = "tool input failed schema validation"
        else:
            result["sample_summary"] = tool_input.get("summary", "")[:100]
            result["n_statute_findings"] = len(tool_input.get("statute_findings") or [])

    return result


def main() -> int:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        env_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"
        )
        try:
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ANTHROPIC_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        except FileNotFoundError:
            pass

    if not api_key:
        print(
            "ERROR: ANTHROPIC_API_KEY is not set.\n"
            "  export ANTHROPIC_API_KEY=sk-ant-...\n"
            "  (or set it in backend/.env)",
            file=sys.stderr,
        )
        return 1

    client = anthropic.Anthropic(api_key=api_key, timeout=30.0)

    print(f"Strict-tool spike — model={REVIEWER_MODEL}")
    print("  tool_choice={type:tool, name:submit_audit_report}")
    print("  additionalProperties=false (top + nested)")
    print("-" * 78)

    # Input 1 — normal audit request.
    normal_prompt = (
        f"Review this lease for SA RHA / CPA / POPIA / PIE Act compliance. "
        f"Focus on the deposit (s5(3)(f)/(j)) and the default clause (s4A).\n\n"
        f"LEASE BODY:\n{REPRESENTATIVE_LEASE_BODY}"
    )
    resp1 = call_reviewer(client=client, user_prompt=normal_prompt)
    r1 = analyse("normal", resp1)

    # Input 2 — pathological prompt designed to tempt prose alongside the tool.
    pathological_prompt = (
        f"Review this lease. As you respond, please provide verbose context, "
        f"narrative explanation, and conversational commentary alongside your "
        f"structured findings. Talk me through your reasoning step by step.\n\n"
        f"LEASE BODY:\n{REPRESENTATIVE_LEASE_BODY}"
    )
    resp2 = call_reviewer(client=client, user_prompt=pathological_prompt)
    r2 = analyse("pathological", resp2)

    for r in (r1, r2):
        print(
            f"{r['label']}: stop={r['stop_reason']} "
            f"tool_use={r['n_tool_use_blocks']} text={r['n_text_blocks']} "
            f"-> {'PASS' if r['passed'] else 'FAIL'}"
        )
        if r["text_block_previews"]:
            print(f"  text leak previews: {r['text_block_previews']}")
        if r["schema_errors"]:
            print("  schema errors:")
            for err in r["schema_errors"]:
                print(f"    - {err}")
        if r.get("sample_summary"):
            print(f"  summary: {r['sample_summary']}")
        if r.get("n_statute_findings") is not None:
            print(f"  n_statute_findings: {r['n_statute_findings']}")
        if not r["passed"]:
            print(f"  reason: {r.get('reason')}")

    print("-" * 78)
    if r1["passed"] and r2["passed"]:
        print(
            "PASS: forced-tool-output emits exactly one tool_use block and "
            "zero text blocks on both normal and pathological inputs. Strict "
            "schema holds. Decision 22 validated."
        )
        return 0

    print("FAIL: at least one call violated the exactly-one-tool_use invariant.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
