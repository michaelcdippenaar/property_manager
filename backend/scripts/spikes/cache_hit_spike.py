"""
Phase 0.5 spike — Anthropic prompt-cache hit validation for the Lease AI Drafter.

Validates the cache layout committed to in `docs/system/lease-ai-agent-architecture.md`
§6.6 + decision 18. The Drafter call structure pins `cache_control: ephemeral` on:

    1. The tools array (last tool block)
    2. The PERSONA_DRAFTER system block (3rd-from-last cache breakpoint)
    3. The MERGE_FIELDS_BLOCK system block (2nd-from-last breakpoint)
    4. The RAG_CHUNKS_BLOCK system block (last breakpoint)

The user message (per-request data) lives in `messages=[...]` AFTER the last
breakpoint, so it does not invalidate the cache.

Pass criteria:
    Call #1 → cache_creation_input_tokens > 0, cache_read_input_tokens == 0
    Calls #2-5 → cache_read_input_tokens > 0

If any of #2-5 misses cache, the architecture's cost projection (§8.1 +
decision 23) is invalid. Exit 1 in that case.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    backend/.venv/bin/python backend/scripts/spikes/cache_hit_spike.py
"""
from __future__ import annotations

import os
import sys
import time
from typing import Any

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic SDK not installed. Run: pip install anthropic", file=sys.stderr)
    sys.exit(1)


# Sonnet 4.6 — Drafter model per decision 23.
DRAFTER_MODEL = "claude-sonnet-4-5"

# Cache requires at least 1024 input tokens on Sonnet. We pad each block
# generously so the test exercises real cache creation, not a sub-threshold
# call that silently degrades to no-cache.

PERSONA_DRAFTER = """You are an expert in South African residential lease law.
You assemble lease clauses from the curated clause library that has been pushed
to you. You ALWAYS prefer assembly over generation. You cite RHA / CPA / POPIA /
PIE Act / Sectional Titles Schemes Management Act where the clause warrants.
You use ONLY the canonical merge fields listed.

You are part of a multi-agent system: a Front Door coordinator (Python) builds
the LeaseContext object, queries the RAG store, and pushes 15-25 pre-filtered
clauses into your system prompt. A Reviewer agent audits your output against
statute; a Formatter agent handles heading hierarchy, page layout, running
headers, and per-page initials placeholders.

You do not handle formatting. You do not handle page layout. You do not handle
running headers. You assemble legal content with statutory citations.

Always prefer assembling from the pushed clause library over generating new
clause text. If the user asks for a clause that is not in the library, you
should still cite the relevant statute and note that the clause is a
best-effort assembly rather than from the curated library.

Your tools are: edit_lines, add_clause, format_sa_standard, insert_signature_field,
highlight_fields, and check_rha_compliance. You do NOT have update_all (removed
in v2 per decision 21).

When a user asks for an edit, prefer surgical edit_lines or add_clause over
rewriting whole sections. When a user asks to insert a clause, pull the
clause_id from the pushed RAG chunks and use add_clause to insert it.

Cite statute for every clause you assemble. Use the form RHA s5(3)(f), POPIA
s16, CPA s14. If you are unsure of the sub-section letter, cite the concept
without the letter and stamp the clause legal_provisional: true.
""" * 3  # Padded to clear the 1024-token cache threshold for Sonnet.

MERGE_FIELDS_BLOCK = """CANONICAL MERGE FIELDS (use only these — no inventions):

Property:
- property_address, property_suburb, property_city, property_province, property_postal_code
- unit_number, unit_type, building_name
- erf_number, ms_number, scheme_name, body_corporate_name

Parties:
- landlord_name, landlord_reg_number, landlord_id_number, landlord_address, landlord_email, landlord_phone
- agent_name, agent_reg_number, agent_address, agent_email, agent_phone
- infraco_name, infraco_reg_number, infraco_address, infraco_email
- tenant_name, tenant_id_number, tenant_address, tenant_email, tenant_phone
- co_tenant_name, co_tenant_id_number, co_tenant_address, co_tenant_email, co_tenant_phone
- tenant_2_name, tenant_2_id_number, tenant_2_address, tenant_2_email, tenant_2_phone
- tenant_3_name, tenant_3_id_number, tenant_3_address, tenant_3_email, tenant_3_phone
- guarantor_name, guarantor_id_number, guarantor_address, guarantor_email, guarantor_phone

Lease term:
- lease_start_date, lease_end_date, key_return_date
- lease_term_months, lease_type
- monthly_rent, monthly_rent_words, deposit, deposit_words, deposit_multiplier
- escalation_percent, late_payment_interest_rate, notice_period_days

Banking:
- bank_name, bank_branch, bank_account_number, bank_reference, bank_account_type
- infraco_bank_name, infraco_bank_branch, infraco_bank_account, infraco_bank_reference

Signatures and initials:
- landlord_signature_1, tenant_signature_1, co_tenant_signature_1, guarantor_signature_1
- landlord_initials_1, tenant_initials_1, co_tenant_initials_1, guarantor_initials_1
- witness_1_signature, witness_2_signature, witness_1_name, witness_2_name

Dates:
- signing_date, signing_city, joint_inspection_date
- deposit_paid_date, first_rent_due_date

If you need a field not listed here, STOP and ask the user — do not invent
field names. Inventing fields breaks the downstream PDF merge pipeline.
""" * 3

RAG_CHUNKS_BLOCK = """LEASE-LAW CORPUS CHUNKS (pushed by Front Door, pre-filtered
by LeaseContext):

CHUNK 1 — clause-deposit-interest-bearing-account-v1
  topic_tags: [deposit, sectional_title, freehold]
  citations: [RHA_5_3_f]
  confidence_level: mc_reviewed
  text: |
    The deposit, totalling R{{ deposit }} ({{ deposit_words }}), will be held
    in an interest-bearing account with a registered financial institution.
    The interest accrued, less any reasonable account fees, accrues to the
    Tenant. Mandatory clause per RHA s5(3)(f). Interest accrual to tenant is
    statutory; cannot be waived.

CHUNK 2 — clause-deposit-refund-window-v1
  topic_tags: [deposit, refund]
  citations: [RHA_5_3_h, RHA_5_3_j]
  confidence_level: mc_reviewed
  text: |
    Within 14 (fourteen) days after the expiration of the lease, the Landlord
    shall refund the Tenant the deposit plus interest, less any amounts
    lawfully deducted for repairs to damage caused by the Tenant during the
    lease (excluding fair wear and tear). The refund period is 7 (seven)
    days where no damages are claimed, and 21 (twenty-one) days where the
    Tenant fails to attend the joint inspection.

CHUNK 3 — clause-joint-inspection-v1
  topic_tags: [inspection, move_in, move_out]
  citations: [RHA_5_3_k]
  confidence_level: mc_reviewed
  text: |
    The parties shall jointly inspect the dwelling within 7 (seven) days
    prior to the Tenant's occupation, and within 7 (seven) days prior to the
    expiration of the lease. The Landlord shall provide the Tenant with a
    written list of defects identified at each inspection.

CHUNK 4 — clause-tenant-multi-joint-and-several-v1
  topic_tags: [multi_tenant, liability]
  citations: [RHA_5_3_a, common_law_suretyship]
  confidence_level: mc_reviewed
  text: |
    Where more than one Tenant is party to this lease, each Tenant shall be
    jointly and severally liable for the full performance of all obligations
    under the lease, including the payment of rent. The Landlord may recover
    the full rent from any one Tenant without first proceeding against the
    others.

CHUNK 5 — pitfall-self-help-eviction-v1
  topic_tags: [eviction, self_help, unfair_practice]
  citations: [RHA_4A, PIE_4_5, common_law_spoliation]
  confidence_level: mc_reviewed
  pattern: void-self-help
  text: |
    Clauses purporting to "consent to lockout, disconnection of services, or
    removal of possessions on default" are VOID as contrary to RHA s4A,
    PIE Act ss4-5, and the common-law mandament van spolie. The Reviewer
    must flag any clause attempting this. The only lawful eviction route
    is a court order or Rental Housing Tribunal ruling.

CHUNK 6 — clause-rha-s5-3-a-parties-v1
  topic_tags: [parties, structure]
  citations: [RHA_5_3_a]
  confidence_level: mc_reviewed
  text: |
    This lease is entered into between {{ landlord_name }} (ID/Registration
    {{ landlord_id_number }}), of {{ landlord_address }}, hereinafter
    referred to as "the Landlord", and {{ tenant_name }} (ID
    {{ tenant_id_number }}), of {{ tenant_address }}, hereinafter referred
    to as "the Tenant". Each party's address above shall serve as their
    domicilium citandi et executandi for the duration of this lease and any
    subsequent dispute.

CHUNK 7 — clause-popia-consent-tenant-data-v1
  topic_tags: [popia, consent]
  citations: [POPIA_s11_1_b, POPIA_s13, POPIA_s14, POPIA_s17, POPIA_s18]
  confidence_level: mc_reviewed
  text: |
    The Tenant consents to the processing of their personal information by
    the Landlord and/or the Landlord's appointed managing agent for the
    purposes of: (a) administering this lease (POPIA s11(1)(b) — contract);
    (b) conducting credit checks (POPIA s11(1)(f) — legitimate interest);
    (c) Rental Housing Tribunal referral (POPIA s11(1)(c) — legal
    obligation). Retention: 5 years post-termination per POPIA s14.

CHUNK 8 — clause-rha-s4-non-discrimination-v1
  topic_tags: [non_discrimination]
  citations: [RHA_4_1]
  confidence_level: mc_reviewed
  text: |
    Neither party shall unfairly discriminate against the other on any
    ground listed in section 9 of the Constitution. The Landlord
    specifically warrants that the offer to lease was extended without
    discrimination on the basis of race, gender, sexual orientation,
    nationality, marital status, or disability, in compliance with RHA s4(1).

CHUNK 9 — clause-cpa-s14-cancellation-v1
  topic_tags: [cpa, cancellation]
  citations: [CPA_s14]
  confidence_level: mc_reviewed
  text: |
    Where this lease constitutes a fixed-term consumer agreement under the
    Consumer Protection Act 68/2008, the Tenant may cancel by giving 20
    (twenty) business days written notice (CPA s14(2)(b)(i)). The Landlord
    may impose a reasonable cancellation penalty in accordance with CPA
    s14(3) and regulation 5 of the CPA regulations, not exceeding the
    Landlord's reasonable losses.

CHUNK 10 — clause-sectional-title-conduct-rules-v1
  topic_tags: [sectional_title, conduct_rules]
  citations: [STSMA_8_2011, CSOS_9_2011]
  confidence_level: mc_reviewed
  text: |
    The Tenant acknowledges that the dwelling forms part of a sectional
    title scheme and that the Tenant is bound by the conduct rules of the
    Body Corporate as registered with CSOS, and by the Sectional Titles
    Schemes Management Act 8/2011. A copy of the current conduct rules is
    annexed to this lease as Annexure A.
""" * 2


def build_drafter_request(*, iteration: int) -> dict[str, Any]:
    """Build a Drafter messages.create payload with the locked cache layout.

    Returns the kwargs dict (model, max_tokens, tools, system, messages).
    """
    # Tools block — only the last tool carries the cache_control marker,
    # which marks the entire tools array as a cache breakpoint.
    tools = [
        {
            "name": "edit_lines",
            "description": "Replace lines [from_index, to_index] with new_lines.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "from_index": {"type": "integer"},
                    "to_index": {"type": "integer"},
                    "new_lines": {"type": "string"},
                    "summary": {"type": "string"},
                },
                "required": ["from_index", "to_index", "new_lines", "summary"],
            },
        },
        {
            "name": "add_clause",
            "description": "Surgically insert a clause from the RAG by clause_id.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "after_line_index": {"type": "integer"},
                    "clause_id": {"type": "string"},
                    "customise": {"type": "string"},
                },
                "required": ["after_line_index", "clause_id"],
            },
            "cache_control": {"type": "ephemeral"},
        },
    ]

    # System prompt — 3 cached blocks per §6.6.
    system = [
        {"type": "text", "text": PERSONA_DRAFTER, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": MERGE_FIELDS_BLOCK, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": RAG_CHUNKS_BLOCK, "cache_control": {"type": "ephemeral"}},
    ]

    # Per-request user data — short, lives AFTER the last cache breakpoint
    # so it does not invalidate the cache. Different per iteration so we are
    # testing system+tools cache, not message-replay cache.
    user_text = (
        f"Iteration {iteration}: rewrite the deposit clause to make the "
        f"interest-accrual-to-tenant language slightly more concise. Respond "
        f"in 1-2 sentences."
    )

    return {
        "model": DRAFTER_MODEL,
        "max_tokens": 256,
        "tools": tools,
        "system": system,
        "messages": [{"role": "user", "content": user_text}],
    }


def main() -> int:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        # Fall back to backend/.env (matches template_views._get_anthropic_api_key)
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

    client = anthropic.Anthropic(api_key=api_key, timeout=20.0)

    print(f"Cache-hit spike — model={DRAFTER_MODEL}, 5 sequential calls")
    print("-" * 78)

    hit_count = 0
    miss_after_first = 0
    started = time.monotonic()

    for i in range(1, 6):
        kwargs = build_drafter_request(iteration=i)
        t0 = time.monotonic()
        resp = client.messages.create(**kwargs)
        duration_ms = int((time.monotonic() - t0) * 1000)

        usage = resp.usage
        created = usage.cache_creation_input_tokens or 0
        read = usage.cache_read_input_tokens or 0
        inp = usage.input_tokens
        out = usage.output_tokens

        if i == 1:
            tag = "[baseline]"
            if created > 0 and read == 0:
                expected = "ok"
            else:
                expected = f"UNEXPECTED (created={created}, read={read})"
        else:
            if read > 0:
                tag = "✓ cache hit"
                hit_count += 1
                expected = "ok"
            else:
                tag = "✗ cache MISS"
                miss_after_first += 1
                expected = "MISS — breakpoints likely wrong"

        print(
            f"Call {i}: created={created} read={read} "
            f"input={inp} output={out} duration={duration_ms}ms  {tag}"
        )
        if expected != "ok":
            print(f"  -> {expected}")

    total_s = time.monotonic() - started
    print("-" * 78)
    print(f"Wall-clock: {total_s:.2f}s")

    if hit_count == 4 and miss_after_first == 0:
        print("PASS: 4/4 follow-up calls hit cache. Cache layout valid per §6.6.")
        return 0

    print(
        f"FAIL: only {hit_count}/4 follow-up calls hit cache. "
        f"{miss_after_first} miss(es). Architecture cost projection is invalid "
        f"until the breakpoint layout is fixed."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
