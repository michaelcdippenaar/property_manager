# Lease AI Phase 2 Day 1-2 — Implementation Status

| Field | Value |
|---|---|
| **Phase** | 2 (Drafter + Reviewer scaffold) |
| **Day** | 1-2 |
| **Status** | Shipped — agents package + V2 view + Caddy snippet + tests, all green |
| **Date** | 2026-05-13 |
| **LLM calls** | 0 live — full cassette replay |
| **DB migrations** | 0 |

---

## 1. Scope landed

The four-specialist cluster is wired structurally, against cassette
replay. No live Anthropic traffic — the harness battery + the V2 view's
SSE pipeline both go through `LeaseAgentRunner.dispatch`, which receives
a scripted response from either `CassetteAnthropicClient` (harness path)
or a `_ScriptedClient` (test fakes).

### Files created

```
backend/apps/leases/agents/
├── __init__.py                  # public surface
├── context.py                   # IntentEnum + frozen LeaseContext
├── front_door.py                # classify_intent + build_dispatch +
│                                # FrontDoorDispatch (3 cached system blocks,
│                                # clarifying-question detection)
├── drafter.py                   # PERSONA + 6 TOOLS + DrafterHandler +
│                                # _apply_add_clause impl
├── reviewer.py                  # PERSONA + SUBMIT_AUDIT_REPORT_SCHEMA +
│                                # 6 TOOLS + ReviewerHandler + truncation guard
└── formatter.py                 # Stub — NotImplementedError("Phase 2 Day 3+")

backend/apps/leases/template_views_v2.py    # async-def Django View; SSE pipeline
backend/scripts/spikes/regenerate_day_1_2_cassette.py    # one-shot cassette generator

backend/apps/leases/tests/test_drafter.py            # 3 tests
backend/apps/leases/tests/test_reviewer.py           # 4 tests
backend/apps/leases/tests/test_front_door.py         # 5 tests
backend/apps/leases/tests/test_template_views_v2.py  # 3 tests

deploy/Caddyfile.lease_ai_v2_handler.snippet         # flush_interval -1 block
content/cto/training/lease_ai_phase_2_day_1_2_status.md (this file)
```

### Files modified

```
backend/apps/leases/urls.py                       # path → LeaseTemplateAIChatV2View
backend/apps/leases/training/harness.py           # _run_pipeline delegates to agents/
backend/apps/leases/tests/test_training_smoke.py  # llm_call_count assertion: 1 → 2
backend/apps/leases/training/cassettes/
   generate-sectional-title-1-tenant-fixed__day-1-2-stub.jsonl   # regenerated
```

### Locked files NOT touched

- `backend/apps/leases/agent_runner.py`
- `backend/apps/legal_rag/*` outside the read API
- `content/legal/*`
- The architecture / plan / canonical-map docs
- `deploy/Caddyfile` (snippet shipped separately)

---

## 2. Test results

`cd backend && .venv/bin/python -m pytest apps/leases/tests/ apps/legal_rag/tests/ -q`

```
====================== 353 passed, 53 warnings in 25.16s =======================
```

Breakdown per the new test files:

| File | Count |
|---|---|
| `test_drafter.py` | 3/3 pass |
| `test_reviewer.py` | 4/4 pass |
| `test_front_door.py` | 5/5 pass (+ 6 subtests for intent table) |
| `test_template_views_v2.py` | 3/3 pass |

S1 smoke battery (`test_training_smoke.py`): 6/6 pass — the `llm_call_count`
assertion updated from 1 → 2 because the harness now runs Drafter +
Reviewer for `generate` intent. The cassette has 2 JSONL lines (one per
agent dispatch). Cassette regeneration is idempotent — re-run the
script and the cassette content is byte-identical (subject to hash
determinism).

---

## 3. Cassette regen

Cassette: `backend/apps/leases/training/cassettes/generate-sectional-title-1-tenant-fixed__day-1-2-stub.jsonl`

```
Drafter request hash:  089a97cf53a3132bb3785fa44305b5ed58c2f1f097274790fe570e5201f40e79
Reviewer request hash: da5275780e1b3227f6b5c1c4615c731d606c6bbe6665ccb32e50b925048f5463
Drafter system blocks: 3 (persona 2824 chars / merge-fields 2744 chars / RAG 65 chars)
```

The Drafter response carries the assembled lease HTML in a single
`text` block (Day 1-2 — when the corpus indexer lands the Drafter will
emit `add_clause` tool calls and we re-record). The Reviewer response
is a single forced `submit_audit_report` `tool_use` block with verdict
`pass`, zero findings.

To regenerate (no API spend):

```bash
cd backend && .venv/bin/python -m scripts.spikes.regenerate_day_1_2_cassette
```

The script is idempotent. It must be re-run whenever:

- The Drafter / Reviewer persona text changes
- The TOOLS arrays change
- The merge-fields YAML changes (alters the cached system block)
- The clauses / statutes corpus is indexed (RAG block becomes non-empty)

---

## 4. Sample SSE event sequence

First 10 SSE frames emitted by `_sse_pipeline` for an S1 generate request:

```
event: status
data: {"phase":"front_door","message":"Routing intent=generate → drafter+reviewer.","request_id":"r1"}

event: agent_started
data: {"agent":"drafter","phase":"drafting","request_id":"r1"}

event: text_chunk
data: {"agent":"drafter","text":"<section>OUT</section>"}

event: agent_finished
data: {"agent":"drafter","llm_calls":1,"duration_ms":1}

event: agent_handoff
data: {"from_agent":"drafter","to_agent":"reviewer","reason":"gate"}

event: agent_started
data: {"agent":"reviewer","phase":"audit","request_id":"r1"}

event: audit_report
data: {"agent":"reviewer","verdict":"pass","summary":"OK.","report":{...}}

event: agent_finished
data: {"agent":"reviewer","llm_calls":1,"duration_ms":2}

event: done
data: {"reply":"<section>OUT</section>","total_calls":2,"total_latency_ms":2,...}
```

The stream finishes with `event: done` carrying `total_calls`,
`total_latency_ms`, `total_cost_usd`, `corpus_version`,
`terminated_reason`. Errors emit `event: error` with `recoverable: bool`
and a Sentry capture.

---

## 5. Day-1-2 deviations from the original plan

1. **V2 view uses `django.views.View`, not DRF `APIView`.** The
   installed DRF (3.17) doesn't yet support `async def` handlers — its
   sync `dispatch` wraps the coroutine in `finalize_response` and
   crashes with `TypeError: object Response can't be used in 'await'
   expression`. The ASGI ADR's note "DRF's APIView supports async def
   post natively as of Django 4.1+" is correct in spirit but not in
   DRF 3.17 specifically. We hand-roll the JWT auth + `IsAgentOrAdmin`
   check inline; the auth surface matches v1 exactly.

2. **AsyncClient header passing.** Django's `AsyncClient.post` requires
   the `headers={"Authorization": ...}` kwarg form (case-insensitive
   ASGI lookup) rather than the legacy `HTTP_AUTHORIZATION=...` form.
   Both work in real production via daphne, but the test setup must use
   the new form.

3. **Test DB transaction mode.** `test_template_views_v2.py` uses
   `@pytest.mark.django_db(transaction=True)` + `TransactionTestCase`
   so the `sync_to_async` thread inside the view sees committed reads
   from the test setup (a fresh DB connection per thread doesn't see
   the test transaction's open writes).

4. **`_apply_add_clause` Day 1-2 placement.** The implementation appends
   the rendered clause at the end of the document rather than honouring
   `after_line_index`. The line-index → HTML-offset mapping is Phase 3
   work (lives in the Formatter's pagination logic); the tool-result
   summary states this honestly so the Drafter doesn't think the
   placement was honoured.

---

## 6. Concerns for Day 3-7

1. **Internal-turn-loop assistant message shape.** `DrafterHandler.run`
   feeds tool results back as a `user` message with a list of
   `tool_result` blocks. The cassette client hashes against the full
   message list including the tool-use ids from the previous response.
   If Anthropic changes its `tool_use.id` generation, cassette replay
   will miss on the second turn. Mitigation: the ids are
   round-tripped from response → message history, so they're
   self-consistent within a session. But cross-session replay relies
   on deterministic id generation in the recording.

2. **DB connection in `_pull_statutes`.** `query_facts_by_topic` opens
   a real DB connection. In the harness's non-DB test context this
   raises a `cursor … does not exist` error inside the catch-all
   `except Exception`. The error is logged at `exception` level —
   noisy but harmless. Day 3+: short-circuit when `settings.DATABASES`
   isn't configured (or move the legal_rag query into the harness's
   stub mode).

3. **Reviewer can't pull tools yet.** The Reviewer's 5 query tools
   (`query_statute`, `query_clauses`, etc.) are declared but the
   handler doesn't process `tool_use` blocks emitted by the model — it
   immediately validates a single forced `submit_audit_report` call.
   For a real Reviewer pass where the model wants to look up case law
   first, Day 3+ must wire the multi-turn tool loop (matching the
   Drafter's shape) AND the truncation guard must run on every
   intermediate response. Today's "single forced call" pattern is
   enough for the regression tests and the S1 cassette; it's not
   enough for adversarial scenarios A1 / A4 / A5.

4. **`tool_choice` in cassette hash.** The Reviewer's request hash
   includes `tool_choice`. If we later add `tool_choice` to a Drafter
   self-check call (e.g. forcing `check_rha_compliance`), the cassette
   must be re-recorded. Worth documenting in the harness module so
   scenario authors don't accidentally invalidate cassettes.

5. **Front Door RAG retrieval is silent-fail.** When the corpus isn't
   indexed (the typical test environment), `_pull_clauses` /
   `_pull_statutes` log an exception and return `[]`. The RAG block
   then says `(no chunks retrieved for this context)` — which is
   deterministic for cassette hashing but means the Drafter never
   actually sees any corpus content in tests. Phase 2 Day 3+ will
   teach `train_lease_agent` to seed a minimal fixtures Chroma index
   so the RAG block has real content for assertion purposes.

6. **No persisted `AILeaseAgentRun` row from the V2 view yet.** The
   runner is constructed but `runner.finalize()` is never called.
   Day 3-7 wires the `finalize()` call at the end of `_sse_pipeline`
   (post-`done` event) — and a try/finally so cap-hit paths also
   persist the row with `terminated_reason`. The model + migration
   are already shipped (Phase 0.5 0031), this is just wiring.

---

## 7. Lines of code

| File | LOC |
|---|---|
| `agents/__init__.py` | 65 |
| `agents/context.py` | 105 |
| `agents/front_door.py` | 376 |
| `agents/drafter.py` | 369 |
| `agents/reviewer.py` | 320 |
| `agents/formatter.py` | 50 |
| `template_views_v2.py` | 478 |
| `tests/test_drafter.py` | 220 |
| `tests/test_reviewer.py` | 235 |
| `tests/test_front_door.py` | 130 |
| `tests/test_template_views_v2.py` | 240 |
| `scripts/spikes/regenerate_day_1_2_cassette.py` | 200 |
| `deploy/Caddyfile.lease_ai_v2_handler.snippet` | 38 |
| `urls.py` (+9 lines) | — |
| `training/harness.py` (replaced _run_pipeline) | ±60 net |

Total new LOC: ~2,900 (incl. tests + cassette generator). Source-only
(no tests, no generator): ~2,000. The over-spec on the brief's
"700-900 LOC" is concentrated in the agent personas (combined ~5,600
chars of prompt text) and tool schemas (6 Drafter + 6 Reviewer tools
with full JSON schema bodies).
