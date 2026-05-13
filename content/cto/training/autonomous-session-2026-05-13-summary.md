# Autonomous Session — 2026-05-13

MC went out for ~2 hours. Caffeinate held the laptop awake. 10 new commits landed end-to-end against the lease-AI multi-agent build. Nothing pushed (MC controls remote).

---

## Commits since `5770fc1d` (MC's last)

```
692f22b9  feat(lease-ai): seed 5 more clauses → 8-clause corpus for chained-Drafter scenarios
a0f1df70  feat(lease-ai): Phase 2 Wave 2A — Reviewer multi-turn, Drafter tools, finalize wiring
fbeaf660  feat(lease-ai): Phase 2 Day 1-2 — Drafter + Reviewer + V2 view; A.6 skill renderer
e1465475  feat(lease-ai): Phase 1 Day 3-7 — legal RAG queryable; cleanup; B.3 wired
992a446b  feat(lease-ai): Phase 1 Day 1-2 scaffolds — 4 parallel workstreams
952daba7  docs(lease-ai): testing + training plan with Claude Code feedback loop
95a320d8  docs(lease-ai): finish ASGI reframe + decision 22 max_tokens edge case
4ff8a07c  feat(lease-ai): Phase 0.5 runtime — LeaseAgentRunner, spikes, ASGI ADR
2738e37c  docs(lease-ai): citation governance + central RAG plan + verifier CLI
5770fc1d  ← your last
```

## What now exists end-to-end

The lease-AI multi-agent cluster is **functional in cassette-replay mode**:

| Layer | Status |
|---|---|
| `LeaseAgentRunner` coordinator + cost ledger + 4 budget caps + `is_truncated_tool_use` helper | ✅ 23 tests |
| `apps.legal_rag` Django app + 4 models + 10 seed YAMLs + 7 query functions + ChromaDB indexer + Postgres sync + skill renderer | ✅ 65 tests |
| `apps.leases.lease_law_corpus` clauses corpus + ChromaDB indexer + `query_clauses()` | ✅ 8 seed clauses (was 3) |
| `apps.leases.merge_fields_loader` — 103 legacy tuples → 15 YAML, applicability-filtered, FK to legal facts | ✅ 25 tests |
| `apps.leases.training` harness + cassette client + assertions + S1 smoke scenario | ✅ 6 tests |
| `apps.leases.agents` — Front Door + Drafter (all 6 tools implemented) + Reviewer (multi-turn pull-tool loop) + Formatter (stub) | ✅ 16 tests |
| `LeaseTemplateAIChatV2View` async post + SSE (status/agent_started/agent_finished/agent_handoff/text_chunk/tool_use/audit_report/done/audit_persisted/error) | ✅ 4 tests |
| `runner.finalize()` wired → `AILeaseAgentRun` row persisted post-stream | ✅ |
| Caddy `flush_interval -1` snippet at `deploy/Caddyfile.lease_ai_v2_handler.snippet` | ⏳ apply by hand to staging+prod Caddyfiles |
| Skill renderer for 2 RHA reference files (`06-rha-core-and-s5.md`, `07-rha-s4a-unfair-practices.md`) | ✅ 7 tests |

**Total: 365 tests passing across leases + legal_rag. Zero broken regressions. `manage.py check` clean. ruff clean.**

---

## Concrete proof the cluster runs

```
$ backend/.venv/bin/python manage.py train_lease_agent \
    --scenario=generate-sectional-title-1-tenant-fixed --replay

Pipeline trace (via cassette replay):
  → Front Door classified intent=generate
  → Drafter call → produces lease HTML
  → Reviewer multi-turn loop:
      • Reviewer query_statute("RHA s7") → real LegalFact from apps.legal_rag
      • Reviewer submit_audit_report → strict schema validated
  → runner.finalize → AILeaseAgentRun row persisted
  → SSE: done → audit_persisted

OVERALL: PASS
```

`query_statute("RHA s7")` returns the canonical Tribunal-establishment fact (the s13→s7 citation correction is live code, not just documentation).

---

## Wave 2C — what's next when you're ready

1. **S1 cassette regeneration with chained `add_clause` pattern.** The current S1 cassette uses one Drafter text-only response. The 8-clause corpus now supports realistic chained-tool-call assembly (parties → property → term → rent → deposit → signatures). Subagent task; ~20 min.

2. **Smoke battery expansion to S2–S8** (testing-plan §3.3). 7 more scenarios + their cassettes:
   - S2: generate freehold 2 tenants month-to-month
   - S3: audit existing Stellenbosch lease (needs to feed a real lease HTML in)
   - S4: insert no-pets clause
   - S5: edit deposit clause lines
   - S6: answer RHA s5(3)(f) question
   - S7: audit with case law (needs case_law facts in legal_rag — currently zero)
   - S8: format add TOC + running header (Formatter agent stub → needs implementation)

3. **A.6 extension to 5 more skill files** (POPIA references 01–05 + `sa-rental-law.md`). Requires more POPIA YAML facts in `content/legal/statutes/popia/` — currently only s16 + s24 exist.

4. **A.7 first lawyer-attestation packet.** Blocked on **D2** (lawyer retainer decision).

5. **Phase 3 (Formatter agent + per-page initials + running header) and Phase 4 (frontend SSE consumer in admin SPA).**

---

## Decisions still open from prior plans

| # | Decision | Blocks |
|---|---|---|
| D2 | Lawyer retainer (FICA attorney bundle vs separate rental-housing specialist) | A.7 first attestation |
| D3 | Marketing copy gate — `lawyer_reviewed` only, or accept `mc_reviewed` pre-launch | Marketing site build |
| D4 | Pre-release: judge score drop > 0.5 blocks deploy, or warning only | Phase 2 testing-plan deploy gate |
| D5 | Rubric attestation cadence — who signs off `legal_precision` + `tenant_fairness` dimensions | Judge wiring |
| D6 | Vault33 vs S3+KMS for opinion-letter PDF storage | A.7 first attestation |
| D7 | Trainer subagent autonomous PR vs stage-for-review | Phase 3 lease-ai-trainer subagent |

All have CTO recommendations in the strategic plans; final call is yours.

---

## Concerns surfaced across the session (none blocking)

1. **DRF 3.17 doesn't support `async def` APIView** — V2 uses plain Django View + hand-rolled JWT/role decoder. Matches v1 auth surface. Worth tracking if DRF upgrades.
2. **`_apply_add_clause` ignores `after_line_index`** — appends at end. Phase 3 pagination work.
3. **Reviewer `query_clauses` and `query_case_law` are wired but the case_law corpus is empty** — `list_pitfall_patterns` likewise. Phase A Day 6-7 work (more YAML seeds).
4. **Skill renderer's footer carries `generated <iso>Z` timestamp** — drifts every render. CI `--check` mode currently treats this as expected drift; consider deterministic stamping in A.6 v2.
5. **Phase 0.5 ASGI ADR's Caddy snippet** sits at `deploy/Caddyfile.lease_ai_v2_handler.snippet` waiting for manual paste into staging + prod Caddyfiles before the SSE pipeline can actually stream in production. Half a day of ops work.
6. **`manage.py reindex_lease_corpus` ran with mock embedder** (no `OPENAI_API_KEY` in env). Before real-OpenAI cutover: wipe `klikk_lease_clauses_v1` ChromaDB collection — content-hash idempotency would otherwise preserve mock vectors.
7. **Background subagent stalls happened twice mid-session** when your internet dropped. Re-dispatched cleanly both times. The stalls were connectivity, not the agents.

---

## Caffeinate

`caffeinate -dimsu -t 9000` started at session start (PID 19532, 2.5-hour window). Will release on its own.

---

## Push status

Nothing pushed to remote. Ten commits sit local. Push when you're ready.
