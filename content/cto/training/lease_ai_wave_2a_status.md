# Lease-AI Wave 2A status — five Phase-2 concerns closed

> **Status:** Implemented, tests green, not committed.
> **Date:** 2026-05-13
> **Scope:** the 5 deferred concerns from
> `lease_ai_phase_2_day_1_2_status.md` (commit `fbeaf660`).

## What landed

### 1. Reviewer multi-turn pull-tool loop

`backend/apps/leases/agents/reviewer.py::ReviewerHandler.run` now
drives a 3-turn loop. Per-turn behaviour:

| Turn | `tool_choice` | Allowed response |
| --- | --- | --- |
| 1..MAX-1 | `{"type":"auto"}` | pull tool ∨ submit_audit_report ∨ text-only |
| MAX (or forced after text-only stale turn) | `{"type":"tool","name":"submit_audit_report"}` | submit_audit_report only |

The 5 pull tools — `query_statute`, `query_clauses`, `query_case_law`,
`list_pitfall_patterns`, `check_rha_compliance` — dispatch to
`apps.legal_rag.queries.*` and
`apps.leases.lease_law_corpus_queries.query_clauses`. Each underlying
exception is caught and surfaced as an error-shaped JSON
`tool_result` so a missing fact never aborts the audit.

New exception: `ReviewerInvalidToolError`. Raised when the model
emits a `tool_use` for a name outside the allowed pull-tool set;
carries the offending name for diagnostics.

New `ReviewerResult` fields: `pull_tool_calls` (chronological list),
`internal_turns` (1..MAX), `terminated_reason`
(`submit_audit_report` | `stale_progress` | etc.).

Decision 22's invariant (forced `tool_choice` on the FINAL dispatch)
is preserved and `is_truncated_tool_use` still raises
`ReviewerTruncatedError` on the forced response only.

### 2. All 5 remaining Drafter tools

`backend/apps/leases/agents/drafter.py` — five new tool helpers:

* **`_apply_edit_lines`** — replaces `<p>`/`<h*>`/`<li>` element ranges
  with new lines; preserves any element containing `⟪SIG#N⟫`.
* **`_apply_format_sa_standard`** — appends placeholder sections for
  any missing entry of `SA_STANDARD_SECTIONS` (PARTIES, PROPERTY,
  TERM, RENT, DEPOSIT, MAINTENANCE, DEFAULT, TERMINATION, DISPUTE,
  SIGNATURES). Placeholder copy is `"Section to be drafted — pull a
  clause via add_clause"` (never the banned `[needs completion]`).
* **`_apply_insert_signature_field`** — allocates the next free
  `⟪SIG#N⟫` index; tags the inserted block with `data-signature-role`
  and `data-signature-type`.
* **`_apply_highlight_fields`** — read-only; surfaces a
  `{field_names, message}` payload via the new
  `DrafterResult.highlighted_fields`.
* **`_apply_check_rha_compliance`** — scans citations against
  `CANONICAL_CITATIONS` + `KNOWN_WRONG_CITATIONS` from
  `verify_caselaw_citations.py`; emits `[{citation, status, message}]`
  on the new `DrafterResult.rha_compliance`.

### 3. V2 view: `runner.finalize()` wired

`backend/apps/leases/template_views_v2.py`. The SSE pipeline now ends
with:

1. `event: done` (existing).
2. New `event: audit_persisted` with `{run_id, request_id,
   terminated_reason}` — emitted from a new helper
   `_finalize_and_emit` after every terminal path
   (success, `LeaseAgentBudgetExceeded`, `ReviewerTruncatedError`,
   generic `Exception`).

If `runner.finalize()` itself raises, the failure is logged + Sentry-
captured and the SSE stream closes cleanly without the
`audit_persisted` frame.

### 4. Front Door RAG fallback

`backend/apps/leases/agents/front_door.py::_pull_clauses` and
`_pull_statutes`. `ImportError`/`RuntimeError`/empty results now log a
`logger.warning("RAG corpus not indexed; rendering empty system
block")` and return `[]`. `_build_rag_chunks_block` emits the new
`RAG_CORPUS_UNAVAILABLE_PLACEHOLDER` string so the 3-block cache
layout (decision 18) stays intact when the corpus isn't indexed.

### 5. S1 cassette regenerated

`backend/scripts/spikes/regenerate_day_1_2_cassette.py` rewritten to
produce a 3-call cassette:

1. Drafter call (text-only, full lease HTML, `stop_reason=end_turn`).
2. Reviewer call 1 (auto → `tool_use(query_statute, RHA s7)`).
3. Reviewer call 2 (auto → `tool_use(submit_audit_report, verdict=pass)`).

The tool_result strings are computed by calling the real helpers
(`_execute_pull_tool`) so the cassette stays aligned with whatever
deterministic error string the runner produces at replay time.

Smoke-test assertion bumped: `llm_call_count == 3` (was 2).

## Files modified

* `backend/apps/leases/agents/reviewer.py` (multi-turn loop + 5 pull-tool dispatchers)
* `backend/apps/leases/agents/drafter.py` (5 new `_apply_*` helpers; result fields)
* `backend/apps/leases/agents/front_door.py` (RAG fallback + placeholder)
* `backend/apps/leases/agents/__init__.py` (export `ReviewerInvalidToolError`)
* `backend/apps/leases/template_views_v2.py` (`runner.finalize()` + `audit_persisted` event)
* `backend/apps/leases/training/cassettes/generate-sectional-title-1-tenant-fixed__day-1-2-stub.jsonl` (regenerated; 3 entries)
* `backend/apps/leases/tests/test_reviewer.py` (updated 2, added 3 tests)
* `backend/apps/leases/tests/test_drafter.py` (added 7 tests)
* `backend/apps/leases/tests/test_front_door.py` (added 1 test)
* `backend/apps/leases/tests/test_template_views_v2.py` (added 1 test)
* `backend/apps/leases/tests/test_training_smoke.py` (bumped `llm_call_count` assertion)
* `backend/scripts/spikes/regenerate_day_1_2_cassette.py` (3-call shape)

## Test counts

* `apps/leases/tests/` + `apps/legal_rag/tests/` → **365 passed**
  (was 352; +13 new assertions, no regressions).
* New tests:
  * Drafter: `_apply_edit_lines` × 2, `_apply_format_sa_standard` × 2,
    `_apply_insert_signature_field`, `_apply_highlight_fields`,
    `_apply_check_rha_compliance` (7).
  * Reviewer: `can_use_query_statute_pull_tool`,
    `force_submits_when_3_internal_turns_exceeded`,
    `handles_unknown_tool_name_gracefully` (3 new + 2 reshaped).
  * Front Door: `rag_fallback_when_corpus_missing` (1).
  * V2 view: `persists_ailease_agent_run` (1).

## Sample SSE event sequence (S1 smoke)

```
event: status
data: {"phase":"front_door","message":"Routing intent=generate → drafter+reviewer.","request_id":"..."}

event: agent_started
data: {"agent":"drafter","phase":"drafting","request_id":"..."}

event: text_chunk
data: {"agent":"drafter","text":"Generated the sectional-title lease as requested."}

event: agent_finished
data: {"agent":"drafter","llm_calls":1,"duration_ms":12}

event: agent_handoff
data: {"from_agent":"drafter","to_agent":"reviewer","reason":"gate"}

event: agent_started
data: {"agent":"reviewer","phase":"audit","request_id":"..."}

event: audit_report
data: {"agent":"reviewer","verdict":"pass","summary":"Lease compliant ...","report":{...}}

event: agent_finished
data: {"agent":"reviewer","llm_calls":1,"duration_ms":48}

event: done
data: {"reply":"Generated ...","total_calls":3,"total_latency_ms":50,"total_cost_usd":0.000123,...}

event: audit_persisted
data: {"run_id":"42","request_id":"...","terminated_reason":"completed"}
```

The Reviewer's multi-turn loop is internal to the handler — only the
final `audit_report` event is emitted to the SSE consumer. Phase 2B+
may surface `pull_tool_calls` via a dedicated diagnostic event if the
frontend wants to show which RAG facts the audit consulted.

## Concerns for Wave 2B

* **Smoke battery expansion to 8 scenarios** (per plan §3.3 — S1..S8).
  Each scenario will need a regenerated cassette plus matching
  scenario YAML. The regen script currently hard-codes the S1 scenario
  ID; extend to take a `--scenario` flag.
* **`add_clause`-driven full document.** Today the smoke cassette uses
  a single text-only Drafter response carrying the full lease HTML.
  The architectural intent is multiple `add_clause` tool calls
  building up the document from corpus chunks. Once the clause corpus
  has all 10 SA-standard sections seeded, the cassette can switch to
  the chained-tool shape (and the regen script's now-removed call-2
  scaffolding can be revived).
* **Remaining 5 legal-skill renderers.** Only the test renderer
  landed in Phase 2 Day 1-2. Wave 2B should finish the renderer set.
* **First lawyer attestation.** Once the multi-turn pull-tool loop is
  drilling into the legal_rag store, we need at least one fact at
  `verification_status=lawyer_reviewed` so the Reviewer can confidently
  cite at MEDIUM/HIGH confidence rather than reading every fact as
  `ai_curated`.
* **`_apply_add_clause` after_line_index** is still pagination-pending
  per concern 1 of the Day 1-2 status note; out of Wave 2A scope.
* **`Drafter.MAX_INTERNAL_TURNS` interaction with `add_clause`.** The
  3-turn cap remains; once the cassette shape exercises sequential
  `add_clause` calls (one per section), we may need a soft retry to
  cover all 10 SA sections in one Drafter pass.
