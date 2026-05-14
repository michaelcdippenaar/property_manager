# Chat Agent Best Practices

A field guide for building production-grade chat agents — distilled from the Klikk Lease AI v2 multi-agent build.

The goal: agents that are **fast, cheap, auditable, and don't lie**. Most chat-agent advice on the internet optimises for demos. This is for systems that have to run unattended, produce artefacts customers rely on, and not get the company sued.

---

## 1. Decide single-agent vs multi-agent up front

A single LLM call is the right answer surprisingly often. Reach for multi-agent only when one of these is true:

- The task has **genuinely distinct phases** with different success criteria (draft vs review, write vs critique)
- You need **separable budgets and observability** per phase
- You want **independent retry / fallback** per phase
- The output of one phase changes the **prompt or tools** of the next

If you only have "step 1, step 2, step 3" but they share context and tools, that's one agent with a longer prompt. Multi-agent is a system-design choice, not a complexity flex.

Klikk lease AI uses 4 agents — Front Door (intent classification), Drafter (writes lease HTML), Reviewer (multi-turn audit with pull-tools), Formatter (pagination + signatures). Each has its own success criteria, its own budget cap, its own tool surface, its own cassette in tests.

## 2. Define the agent contract before the prompt

Every agent should have a one-page spec containing:

- **Role** — one sentence on what it owns
- **Inputs** — exactly what arrives (schema, not English)
- **Outputs** — exactly what leaves (schema, not English) — usually a tool call with a strict argument schema
- **Tools available** — and tools explicitly NOT available
- **Budget** — max tokens, max tool calls, max wall-clock
- **Failure modes** — what "the agent gave up" looks like and how the runner handles it
- **Handoff target** — which agent runs next, and what state passes

Write this first. The system prompt is a derivative of this spec, not the source of truth.

## 3. Force structured output via tool_use, not JSON-mode

For anything the rest of the system has to parse, define a tool with a strict input schema and require the model to call it. Two reasons:

1. **Anthropic's tool-use enforcement is stricter than JSON-mode.** Schema violations are rarer.
2. **The tool name doubles as your intent signal.** `submit_audit_report` vs `request_clarification` tells you exactly which branch fired without parsing.

For the Reviewer agent, `submit_audit_report` is the only terminal tool. If the agent emits text, the runner keeps the loop open. If it emits the wrong tool, the runner errors fast.

## 4. The pull-tool loop > one-shot reasoning

If an agent needs facts to do its job (statutes, prior clauses, case law), do NOT pre-stuff them into the prompt. Give the agent **query tools** and let it pull what it needs:

- `query_statute(name, section)`
- `query_clauses(topic, applicability)`
- `query_case_law(jurisdiction, topic)`
- `list_pitfall_patterns(clause_type)`

Why:
- Smaller context = faster + cheaper + less hallucination
- The audit trail of which tools fired = a record of what evidence was actually consulted
- The agent can adapt: if it finds something unexpected in result A it can pull a follow-up B

The Reviewer agent runs an unbounded `for turn in range(max_turns)` loop. Each turn it can call a query tool OR submit the final report. The loop exits on `submit_audit_report` or budget exhaustion.

## 5. Cite or it didn't happen

Every fact-bearing claim an agent emits should carry a **citation token** back to the source. In Klikk's case, every legal finding has a `citation` field pointing to a `LegalFact` row, which points to a YAML file, which points to a statute section + effective date + last_reviewed_at.

The Reviewer's `query_statute` tool returns facts with their citation pre-attached. The agent's job is to preserve it, not invent it. The runner validates that every finding's citation resolves to a real LegalFact before persisting.

Hallucinated citations are the #1 failure mode of legal AI. The fix is architectural, not promptural: don't let the agent **emit** citation strings — let it **forward** citation strings the tool returned.

## 6. Build a cost ledger from day one

Every model call goes through a `LeaseAgentRunner` (or equivalent coordinator) that tracks:

- Input tokens
- Output tokens
- Cached tokens (separately — the discount is real)
- Tool-call count per agent
- Wall-clock per agent
- Cumulative spend in cents

Budget caps fire at the runner level:
- `max_input_tokens_total` (across whole session)
- `max_output_tokens_per_agent`
- `max_tool_calls_per_agent`
- `max_wall_seconds_total`

When a cap trips, the runner short-circuits with a structured error event, persists what it has, and surfaces a `budget_exhausted` reason. The user sees "ran out of budget on the Reviewer pass — accept partial result or retry with higher cap?"

Without a cost ledger you will discover production cost overruns from the Anthropic invoice. With it you discover them from a Sentry alert at 3% of budget.

## 7. Stream over Server-Sent Events, not WebSockets

For chat agents specifically, SSE wins:

- Unidirectional (agent → client) — matches the actual data flow
- Reconnect-on-close is trivial
- Plays nicely with HTTP/2 multiplexing
- No protocol upgrade dance, no sticky-session requirements

Event types we found useful (one event = one self-contained JSON payload):

| Event | When |
|---|---|
| `status` | Coordinator-level status text |
| `agent_started` / `agent_finished` | Phase transitions |
| `agent_handoff` | One agent passes the baton to another |
| `text_chunk` | Streaming text from the model to the editor |
| `tool_use` | Optional — surfaces "consulting statute X…" |
| `audit_report` | Structured Reviewer output |
| `done` | Successful terminal event |
| `audit_persisted` | DB row ID for the saved run |
| `error` | Structured failure with a code |

**The Caddy gotcha:** by default Caddy buffers responses until they close. For SSE you must set `flush_interval -1` on the reverse_proxy block. We lost half a day to this. Set it once, leave a comment in the Caddyfile pointing at the ADR.

## 8. Cassette-replay tests, not live API tests

In CI, never call the real Anthropic API. Build a cassette client:

1. First run hits the real API, records every request → response pair to a YAML file
2. Subsequent runs replay from the YAML
3. Tests assert on the structured tool calls + final state, not on the exact prose

This gives you:
- Sub-second test runs
- Zero API spend in CI
- Reproducible failures (the cassette is the spec)
- A diff-able artefact when the model upgrades and behaviour changes

Scenarios become a smoke battery: `generate-sectional-title-1-tenant-fixed`, `audit-existing-stellenbosch-lease`, `insert-no-pets-clause`. Each has a cassette + an assertion bundle. Adding scenarios adds coverage linearly without adding cost.

## 9. The Front Door agent is non-optional

The user types "I want a lease for my flat in Sea Point with two tenants on a year contract." That sentence contains:
- Intent: `generate` (not audit, not edit, not Q&A)
- Property type: `apartment`
- Location: `Western Cape` → applicable RHA
- Tenant count: `2`
- Lease type: `fixed_term` (12 months)

A cheap, fast Front Door agent classifies this into a typed `IntentPacket` before any expensive Drafter / Reviewer work fires. Two wins:

1. Wrong intent fails in 200ms with `clarify` instead of 30s into a wrong lease
2. The Drafter receives a structured packet, not a prose dump — its prompt becomes deterministic

The Front Door uses Haiku, not Sonnet. It's a router, not a writer.

## 10. Schema-validate every agent boundary

Between every agent, run the handoff payload through a strict Pydantic / dataclass validator. Two reasons:

- **Defence in depth** against the upstream agent emitting garbage
- **Type safety** for downstream code — the Drafter doesn't have to defensively check `if packet.tenant_count is None`

If validation fails, the runner emits a `handoff_validation_error` event with the field path + the bad value, and either retries the upstream agent with a corrective message or hard-fails. Never silently coerce.

## 11. Truncation detection

Anthropic returns `stop_reason: "max_tokens"` when the model ran out of output budget mid-generation. Most code ignores this. Don't.

Build a helper:
```python
def is_truncated_tool_use(response) -> bool:
    return (
        response.stop_reason == "max_tokens"
        and response.content
        and response.content[-1].type == "tool_use"
    )
```

If true, the tool call's JSON args are almost certainly malformed (closing brace missing). The runner should reject, raise the output budget, and retry — not parse-and-fail downstream.

## 12. Persist the run, always

Every agent session writes a row (`AILeaseAgentRun` in our case) with:

- `run_id` (UUID), `user_id`, `template_id`
- `started_at`, `ended_at`
- Full event stream (JSONB array)
- Final state (`completed` / `errored` / `budget_exhausted` / `user_cancelled`)
- Cost ledger snapshot
- Cassette hash (so you can correlate prod runs back to the test scenario they match)

When a customer complains "your AI broke my lease" you load the run, scroll the events, and see exactly which Reviewer turn flagged what. Without this you're guessing.

## 13. Failure UX matters more than success UX

Success path is easy — content streams in, audit panel appears, accept button enables. Failure path is where products live or die:

- **Budget exhausted mid-generation** — show what was produced + an "extend budget" button, not "Error"
- **Reviewer found high-severity issues** — surface them prominently, don't bury under a chevron
- **Network drop mid-stream** — resume from last `audit_persisted` event, not from scratch
- **Hallucinated citation detected** — flag the specific finding as "unverified" and let the user accept or reject

Build at least three explicit failure states in the UI before you ship. The default browser "fetch failed" toast is not one of them.

## 14. Keep the human in the loop for irreversible actions

The Drafter writes HTML into an editor. The user accepts or rejects. The Reviewer never auto-fixes. Nothing the agent does is persisted to a customer-facing artefact (a signed PDF, an outbound email, a Tribunal filing) without a human accept click.

This is non-negotiable for regulated domains (legal, medical, financial). For lower-stakes domains the same principle still applies to anything with a real-world side effect — sending an email, charging a card, opening a ticket. Agents propose, humans dispose.

## 15. Skill files over mega-prompts

Instead of one 8000-token system prompt, the Reviewer loads a curated set of skill files at runtime — POPIA reference, RHA reference, lease format guide. Each skill is a markdown file rendered offline from YAML facts by a deterministic renderer (`render_legal_skills --write`).

Why:
- Skills are reviewable / diff-able artefacts — your legal team can sign off on a `.md`, not on a Python string
- Different agents load different skill bundles — Front Door gets none, Drafter gets format guide, Reviewer gets the legal canon
- Skills carry a `last_reviewed_at` stamp — if a fact ages past 12 months a CI check flags it

## 16. Observability checklist before "go live"

Don't ship until you have:

- [ ] Per-agent token / cost / latency metric in your APM
- [ ] Per-event-type stream emission rate (catches "events stopped firing" silently)
- [ ] Sentry alert on `error` event with the structured reason
- [ ] Alert on cost-per-session exceeding 3× the p50
- [ ] Alert on `budget_exhausted` rate exceeding 5%
- [ ] DB row count for `AILeaseAgentRun` charted alongside chat sessions started (catches "users start chats but no runs persist")
- [ ] A weekly review of 10 random runs — read the event stream end-to-end like a code review

If any of these are missing you are flying blind. The agent will misbehave in a way no test caught and you will only find out from a support ticket.

---

## Anti-patterns we caught ourselves doing

- **Putting the whole legal corpus in the system prompt.** Replaced with `query_statute` tool.
- **Single mega-agent with 12 tools.** Split into Front Door / Drafter / Reviewer / Formatter — each with 1–6 focused tools.
- **JSON-mode for structured output.** Replaced with tool-use + strict schema.
- **One-shot text response.** Replaced with the pull-tool loop for Reviewer.
- **In-memory cost tracking.** Replaced with persisted ledger so post-hoc analysis is possible.
- **Mocking the API in tests with `unittest.mock`.** Replaced with cassette client so test fixtures match real wire format.
- **Production Caddy buffering SSE events.** Fixed with `flush_interval -1` + an ADR explaining why.
- **Letting the agent invent citations.** Replaced with citation-forwarding-only — agents can only emit citations the tools returned.

---

## Reference

- Klikk lease AI architecture: `docs/system/lease-ai-asgi-decision.md`
- Citation governance: `content/cto/training/autonomous-session-2026-05-13-summary.md`
- Testing harness: `backend/apps/leases/training/`
- Legal RAG layer: `backend/apps/legal_rag/`
- Frontend SSE consumer: `admin/src/composables/useLeaseAIChatV2.ts`
- Backend SSE view: `LeaseTemplateAIChatV2View` at `/api/v1/leases/templates/<id>/ai-chat-v2/`
- Caddy SSE handler: `deploy/Caddyfile` — `flush_interval -1` block on `api.klikk.co.za` and `backend.klikk.co.za`

## Deployed where

- **Staging:** `app.klikk.co.za` (admin SPA) + `backend.klikk.co.za` / `api.klikk.co.za` (Django API). The lease AI v2 multi-agent cluster is live on staging as of 2026-05-13, SHA `66794a1`.
- **Production:** not yet flipped. Cutover gated on staging soak + lawyer attestation (D2).

Last reviewed: 2026-05-13
