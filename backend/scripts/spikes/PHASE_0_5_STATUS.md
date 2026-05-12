# Phase 0.5 status — 2026-05-12

All four deliverables built. Both Anthropic spikes run green against live API.
LeaseAgentRunner tests pass via pytest. ADR proposes Option D (reuse existing
ASGI runtime, fix one Caddy flag).

---

## Deliverable 1 — Cache-hit spike

- **Path:** `backend/scripts/spikes/cache_hit_spike.py`
- **Status:** Built. Ran. PASSED.
- **Model:** `claude-sonnet-4-5` (Drafter per decision 23).

| Call | created | read | input | output | duration |
|---|---|---|---|---|---|
| 1 (baseline) | 6870 | 0 | 360 | 202 | 5983 ms |
| 2 | 0 | **6870** | 360 | 195 | 4303 ms |
| 3 | 0 | **6870** | 360 | 197 | 4490 ms |
| 4 | 0 | **6870** | 360 | 208 | 4501 ms |
| 5 | 0 | **6870** | 360 | 205 | 4458 ms |

4/4 follow-up calls hit cache. The §6.6 layout — `cache_control: ephemeral`
on the last tool block + persona + merge-fields + RAG-chunks system blocks,
with per-request user data in `messages=[...]` after the last breakpoint — is
verified against the real Anthropic API.

**Architecture cost projection in §8.1 stands.**

---

## Deliverable 2 — Strict tool spike

- **Path:** `backend/scripts/spikes/strict_tool_spike.py`
- **Status:** Built. Ran. PASSED.
- **Model:** `claude-haiku-4-5-20251001` (Reviewer per decision 23).
- **Tool:** `submit_audit_report` with `additionalProperties: false` at top + every nested object.

| Input | stop_reason | tool_use blocks | text blocks | schema valid |
|---|---|---|---|---|
| Normal audit | `tool_use` | 1 | 0 | yes |
| Pathological ("respond with verbose context") | `tool_use` | 1 | 0 | yes |

Does the model emit text alongside tool_use under forced tool_choice? **No.**
Even the pathological prompt explicitly requesting "narrative explanation
alongside structured findings" produced 0 text blocks and 1 tool_use block.
Strict mode held — the schema validator caught zero extras.

**Decision 22 validated. Reviewer one-liner can safely live inside the
`summary` field as designed.**

(Initial run had `max_tokens=1024` which clipped the pathological response
to `stop_reason=max_tokens`; bumped to 4096 — same content shape, clean
`stop_reason=tool_use`. The actual decision-22 invariant — exactly one
tool_use, zero text blocks — held in both runs.)

---

## Deliverable 3 — LeaseAgentRunner

- **Coordinator:** `backend/apps/leases/agent_runner.py`
- **Model + migration:** `backend/apps/leases/models.py` (`AILeaseAgentRun`); migration `backend/apps/leases/migrations/0031_ailease_agent_run.py`. `makemigrations --check` is clean.
- **Tests:** `backend/apps/leases/tests/test_agent_runner.py`
- **Status:** Built. **15/15 tests pass** via `backend/.venv/bin/python -m pytest apps/leases/tests/test_agent_runner.py --no-cov` (run in `backend/`).

Test breakdown:

| Suite | Tests | Result |
|---|---|---|
| DispatchCountingTests | 1 | PASS |
| CostTrackingTests | 3 | PASS |
| BudgetCapTests (calls / walltime / cost) | 3 | PASS |
| ShouldRetryTests | 5 | PASS |
| FinalizeTests | 2 | PASS |
| CallLogTests | 1 | PASS |

Covers all 10 spec'd test cases plus 5 added: cache-read pricing, unknown-model
graceful degrade, None-report retry, blocking-from-format-findings retry, and
finalize-uses-cap-reason.

**Note on test runner:** the project's standard runner is pytest (per
`pytest.ini` + `pytestmark` decorators across the leases test suite).
`manage.py test` fails on this project regardless of the changes here — the
existing `test_expiry` suite hits the same SystemCheckError on `manage.py test`
runs (looks like a settings/test-runner interaction unrelated to this task).
Pytest is the supported path and the spec's `manage.py test` invocation reads
as a style note rather than a hard runner constraint.

### `LeaseAgentRunner` shape

- `dispatch(*, agent, model, messages, system, tools=None, tool_choice=None)` — single entry point. Enforces caps before each call, then invokes the Anthropic client, updates `llm_call_count` / `running_cost_usd` from `response.usage`, appends to `_call_log`.
- `should_retry(audit_report)` — decision 24: True iff ≥1 `blocking` finding AND retry budget > 0. Checks `statute_findings`, `case_law_findings`, `format_findings`.
- `finalize(*, terminated_reason=None)` — persists `AILeaseAgentRun` row, returns the instance.
- `increment_retry()` — bumps counter; raises `LeaseAgentBudgetExceeded("cap_retries")` if exceeded.
- Cost model lives in module-level `PRICING` dict per decision 23. Both `claude-sonnet-4-6` (architecture doc name) and `claude-sonnet-4-5` (live snapshot) are keyed identically.
- Reads `LEASE_AI_MAX_COST_USD_PER_REQUEST` from settings (default $0.50 per decision 20).

---

## Deliverable 4 — ASGI decision doc

- **Path:** `docs/system/lease-ai-asgi-decision.md`
- **Recommendation:** **Option D — reuse the existing ASGI runtime, fix one Caddy flag.**

**Key finding from investigation:** the audit P1 premise in
`docs/system/lease-ai-agent-architecture.md` §10.2 — that Klikk runs on sync
WSGI workers — is incorrect for production.

- `backend/Dockerfile` line 27: `CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]`
- `config/asgi.py` already wires `ProtocolTypeRouter` with `get_asgi_application()`
- Channels + daphne in `requirements.txt` since the maintenance/esigning/leases WebSocket work landed

The real SSE-buffering risk lives one layer up: `deploy/Caddyfile` lines
145–150 proxy `backend:8000` *without* `flush_interval -1`. Caddy buffers
HTTP/1.1 responses by default; the Volt MCP block at lines 132–141 sets
`flush_interval -1` explicitly because the team has hit this before. The
same flag is missing on the main backend reverse proxy.

Option D plan:

1. Add a scoped `handle /api/v1/leases/templates/*/ai-chat-v2/*` Caddy block with `flush_interval -1`. Mirror the Volt MCP pattern.
2. Make the v2 view `async def post(...)` so the SSE generator runs as a native async iterator (not a sync iterable wrapped by daphne's threading shim).
3. Add `X-Accel-Buffering: no` + `Cache-Control: no-cache, no-transform` to the SSE response.
4. Smoke test: first `event: agent_started` byte within 2 s of POST.

**Cost:** ~0.5 day, no migration risk, no DB change.

Option B (separate FastAPI sub-app) is rejected — would force a dual auth /
middleware / Sentry stack to dodge a problem we don't have.

---

## Architectural concerns for MC

None blocking. Three small flags:

1. **Architecture doc §10.2's audit P1 is overstated.** The doc treats "migrate to ASGI" as a Phase 1 prerequisite. Production has been on ASGI for months. The ADR (Deliverable 4) reframes this as a Caddy-config fix, which is much cheaper and lower-risk. Consider updating §10.2 once the ADR is signed off — though I am not editing the locked doc per the brief.
2. **Strict mode + `max_tokens` interaction.** The strict-tool spike showed that a low `max_tokens` (1024) under aggressive prompts can clip the tool_use call mid-emission with `stop_reason=max_tokens`. Decision 22's "exactly one tool_use, zero text blocks" invariant still held, but the tool input could be a truncated partial JSON. The LeaseAgentRunner caller should treat `stop_reason=max_tokens` on a forced-tool-choice call as a soft error and either retry with a higher `max_tokens` or short-circuit. Worth a one-liner in the doc when next-edited.
3. **`AILeaseAgentRun.lease_id` is `BigIntegerField`, not FK.** Per the spec, to avoid the circular-import problem. This means no `lease__agency` joins for analytics. Acceptable trade-off — if reporting needs grow, promote to a real FK in Phase 6+ (cheap migration; no data loss).
