# Lease-AI Test Harness — Day 1-2 status

| Field | Value |
|---|---|
| **Status** | Day 1-2 scaffold complete; ONE smoke scenario passes end-to-end in replay mode |
| **Owner** | CTO |
| **Date** | 2026-05-13 |
| **Plan reference** | `content/cto/lease-ai-testing-and-training-plan.md` §16 (Phase 1 Day 1-2) |
| **Locked plan** | Not edited |
| **Architecture doc** | Not edited |
| **`agent_runner.py`** | Not edited |
| **Commits / push** | None — scaffolding only, awaiting MC review |

---

## 1. What landed

### 1.1 Files created

| Path | LOC | Purpose |
|---|---|---|
| `backend/apps/leases/training/__init__.py` | 34 | Public surface re-exports |
| `backend/apps/leases/training/result.py` | 121 | `ScenarioResult` + `ScenarioTotals` dataclasses + JSON (de)serialise |
| `backend/apps/leases/training/assertions.py` | 319 | Day-1-2 assertion implementations + Phase-2 stubs |
| `backend/apps/leases/training/cassette.py` | 392 | `CassetteAnthropicClient` record / replay / live |
| `backend/apps/leases/training/harness.py` | 434 | `LeaseTrainingHarness` orchestrator |
| `backend/apps/leases/management/commands/train_lease_agent.py` | 207 | `manage.py train_lease_agent` CLI |
| `backend/apps/leases/tests/test_training_smoke.py` | 65 | pytest entry — one S1 smoke check |
| `backend/apps/leases/training/fixtures/happy/generate-sectional-title-1-tenant-fixed.yaml` | 84 | S1 scenario YAML |
| `backend/apps/leases/training/fixtures/happy/generate-sectional-title-1-tenant-fixed__day-1-2-stub.jsonl` | 1 line | Hand-crafted cassette for replay (no live API) |
| `backend/apps/leases/training/cassettes/.gitkeep` | 0 | Placeholder for the canonical cassettes/ dir |
| `content/cto/training/runs/.gitkeep` | 0 | Result-file output directory |

**Code totals:** 1572 lines across 7 Python files (counting docstrings; runnable logic is ~600 LOC as scoped).

**Ruff:** clean (`ruff check apps/leases/training apps/leases/management/commands/train_lease_agent.py apps/leases/tests/test_training_smoke.py` → "All checks passed").

### 1.2 What is implemented for real on Day 1-2

**Structural assertions (plan §4.1):**

- `no_placeholder_text` — `[needs completion]` literal + `TBD`/`TODO`/`XXX` whole-word.
- `merge_field_present(fields)` — every `{{ field }}` token must be present.
- `merge_field_absent(fields)` — every `{{ field }}` token must NOT be present.
- `has_section(sections)` — every section name must appear as a case-insensitive substring.

**Citation-correctness assertions (plan §4.2):**

- `all_citations_resolve_in_canonical_map` — uses the same `CITATION_RE` + `normalise()` as `verify_caselaw_citations.py` so the harness assertion stays in lockstep with the static-markdown gate.
- `known_wrong_citations_zero` — scans for canonical-looking patterns from `KNOWN_WRONG_CITATIONS` (e.g. "Tribunal established under RHA s13").

**Cassette client (plan §6):**

- SHA-256 hash of normalised `messages.create` kwargs (`max_tokens` stripped per §6.3).
- `replay` (default) → raise `CassetteMissError` on miss.
- `record` → forward to live client, append JSONL line, return rehydrated response.
- `live` → forward without recording.
- Response rehydration matches the shape `LeaseAgentRunner._record_call` reads (`.usage.input_tokens` / `output_tokens` / `cache_read_input_tokens` / `cache_creation_input_tokens`, `.stop_reason`, `.content`).
- Cassette path is content-addressed by `<scenario_id>__<corpus_hash>.jsonl`; `DAY_1_2_CORPUS_HASH = "day-1-2-stub"` is the placeholder until the legal_rag indexer lands.

**Result file (plan §5.3):**

- JSON, schema_version 1.0, written to `content/cto/training/runs/<iso8601>__<scenario_id>.json`.
- Fields: `scenario_id`, `run_id`, `mode`, `corpus_version`, `started_at`, `duration_seconds`, `verdict`, `totals` (`llm_call_count`, `input_tokens`, `output_tokens`, `cache_read`, `cost_usd`, `retry_count`, `terminated_reason`), `call_log`, `assertion_results`.
- `to_jsonable()` + `from_jsonable()` round-trip so future trainer code can rehydrate prior runs without ad-hoc parsing.

### 1.3 What is stubbed (intentionally per Day-1-2 scope)

| Category | Stub behaviour |
|---|---|
| `reviewer_pipeline` | Every check returns `passed=True, detail="skipped — Phase 1 Day 1-2 stub"` |
| `cost_and_latency` | Same — Phase 2 wires the real 3-4 call pipeline + budget caps comparison |
| `semantic` (judge) | Same — judge.py is a Phase 2 deliverable |

The scenario YAML keeps the full §3.2 shape for these categories so Phase 2 just lights them up; nothing in the schema needs to change.

### 1.4 What is NOT in this PR

Per the locked scope: no LLM-as-judge, no `rank_artefact_categories` diagnostic, no `lease-ai-trainer` subagent, no `--battery` flag, no live-API calls. Phase 2 + 3 deliverables.

---

## 2. Test result

### 2.1 pytest

```
$ cd backend && .venv/bin/python -m pytest \
    apps/leases/tests/test_training_smoke.py -v --no-cov

apps/leases/tests/test_training_smoke.py::SmokeBatteryTests::
  test_generate_sectional_title_1_tenant_fixed PASSED [100%]

========================= 1 passed, 1 warning in 0.02s =========================
```

The test inherits from `unittest.TestCase`, not `django.test.TestCase`, because the Day-1-2 harness only calls `LeaseAgentRunner.dispatch` — never `finalize()`. No DB row is created, no migrations are required. This makes the smoke battery decoupled from migration state and ~instantaneous on cold start. Phase 2 (when the Reviewer + persistence lands) will switch back to `django.test.TestCase`.

### 2.2 management command

```
$ cd backend && .venv/bin/python manage.py train_lease_agent \
    --scenario=generate-sectional-title-1-tenant-fixed --replay

Scenario: generate-sectional-title-1-tenant-fixed
  Mode:           replay
  Corpus version: day-1-2-stub
  Started:        2026-05-13T07:39:25.095185+00:00

Pipeline trace:
  drafter call  claude-sonnet-4-5  input=312  output=480  cache_read=0  0ms  $0.0120

  Totals: 1 calls, 0.00s, $0.0120, retry=0

Assertions:
  STRUCTURAL                      4/4  PASS
  CITATION_CORRECTNESS            2/2  PASS
  REVIEWER_PIPELINE               4/4  PASS
  COST_AND_LATENCY                4/4  PASS
  SEMANTIC                        3/3  PASS

OVERALL: PASS  duration=0.00s  cost=$0.0120

Result file: /Users/mcdippenaar/.../content/cto/training/runs/
             2026-05-13T07-39-25__generate-sectional-title-1-tenant-fixed.json
```

Cost is $0.0120 because the harness uses Sonnet pricing (input $3/Mtok, output $15/Mtok) against the cassette's recorded `usage` (312 in / 480 out / 1024 cache create). The number is a synthetic from the hand-crafted recording, not a real API call.

### 2.3 Negative validation

The seven Day-1-2 assertions were sanity-checked against deliberately-broken input — each returns `passed=False` with an actionable `detail` string. The cassette miss path (`CassetteMissError`) also raises correctly when no matching hash is found.

### 2.4 JSON output mode

```
$ cd backend && .venv/bin/python manage.py train_lease_agent \
    --scenario=generate-sectional-title-1-tenant-fixed --replay \
    --format=json | head -20

{
  "schema_version": "1.0",
  "scenario_id": "generate-sectional-title-1-tenant-fixed",
  "run_id": "20260513T073844Z__generate-sectional-title-1-tenant-fixed__6df28932",
  "mode": "replay",
  "corpus_version": "day-1-2-stub",
  "started_at": "2026-05-13T07:38:44.571623+00:00",
  "duration_seconds": 0.0002,
  "verdict": "pass",
  ...
}
```

The result file on disk matches the stdout JSON exactly (`to_jsonable` is shared between renderer + writer).

---

## 3. Architectural notes / concerns for Day 3+

### 3.1 Day-1-2 harness pipeline is intentionally minimal

The harness today dispatches **one** Drafter call. Per the scope: "the harness's PURPOSE on Day 1-2 is to prove the cassette + assertion + result-file round-trip works." Phase 2 will reshape `_run_pipeline` to do Front Door → Drafter → Reviewer → Formatter; the assertion + result + cassette layers are designed to absorb that change without API churn.

When Phase 2 lands:

- `_run_pipeline` becomes ~80-150 LOC of agent orchestration (currently 14 LOC for the single dispatch).
- `_build_system_block` reads `PERSONA_DRAFTER` / `MERGE_FIELDS_BLOCK` / `RAG_CHUNKS_BLOCK` from a settings-driven source (today: hard-coded one-liner adjacent to the cassette hash).
- `cassette` re-records will land in `cassettes/<id>__<corpus_hash>.jsonl` per plan §6.2 (today: alongside the YAML fixture under `fixtures/happy/<id>__<corpus_hash>.jsonl` for easier hand-crafting).

These three relocations are documented inline in each module's docstring as "Phase 2 will" comments so the future implementer doesn't need to re-derive intent.

### 3.2 Cassette adjacency to fixtures

For Day 1-2 I co-located the cassette next to its scenario YAML (`fixtures/happy/<id>__day-1-2-stub.jsonl`) instead of the plan's `cassettes/<id>__<hash>.jsonl`. Reason: a hand-crafted cassette is easier to review when it's next to the YAML that produces it. Day 3+ should migrate to the canonical layout once the real corpus hash is available. Two-line change in `LeaseTrainingHarness._build_cassette_client`.

### 3.3 Pytest framework choice

The Day-1-2 test is `unittest.TestCase`, not `django.test.TestCase`. This avoids a 60-second migration on every test run and decouples the smoke battery from the test database state — which mattered during scaffold development because another running test session had left `test_klikk_db` in a half-migrated state. Phase 2 (Reviewer + persistence) will need DB; at that point we add `pytest.mark.django_db` selectively to the tests that finalize, leaving the dispatch-only smoke checks as plain unittest.

### 3.4 Plan nits worth flagging before Day 3

1. **Cassette path canonicalisation.** Plan §6.2 says cassettes live in `backend/apps/leases/training/cassettes/<scenario_id>__<corpus_hash>.jsonl`. The fixture-adjacent layout I used on Day 1-2 should not become the convention. Day 3 should explicitly migrate.
2. **The `priority` field.** Plan §3.2 defines `priority: smoke | full | nightly_only`. Day 1-2 reads it into `Scenario.priority` but does not branch on it; once `--battery=smoke` lands on Day 3 we will need a "load every YAML with priority=smoke" loader.
3. **`stub_reviewer_pipeline` etc. always return PASS.** This is correct for scaffold purposes but a deliberately-broken scenario YAML that mis-spells a structural assertion key currently lands in the stub path and silently passes. Day 3 should add a "did the scenario assert anything we didn't recognise?" lint pass at YAML-load time so typos surface during scenario authoring, not at first failure.
4. **`KNOWN_WRONG_CITATIONS` Day-1-2 detector.** The detector does a naive substring scan for the canonical-form half of each key — it will fail on `RHA:s11(2)|accuracy` because canonical form `s11(2)` would also appear in legitimate POPIA citations. A second pass on Day 3 should add the context-tag check (e.g. "s11(2) within 5 words of 'accuracy'"). Day-1-2 deliberately ships the simple version; my smoke scenario doesn't currently trip any known-wrong citation, so this is latent.
5. **Live mode is wired but untested.** `CassetteAnthropicClient.mode="live"` and `mode="record"` paths compile and have explicit construction guards but no live API call has been made from the harness (Day 1-2 constraint). Day 3 should exercise `--record` for at least one scenario before scaling to 8.

### 3.5 No changes to locked artefacts

- `backend/apps/leases/agent_runner.py` — not touched.
- `docs/system/lease-ai-agent-architecture.md` — not touched.
- `content/cto/lease-ai-testing-and-training-plan.md` — not touched.
- `content/cto/centralised-legal-rag-store-plan.md` — not touched.
- `content/cto/rha-citation-canonical-map.md` — not touched.
- `backend/apps/leases/management/commands/verify_caselaw_citations.py` — not touched (assertions import its `CANONICAL_CITATIONS` / `KNOWN_WRONG_CITATIONS` / `CITATION_RE` / `normalise`).

---

## 4. Day 3+ readiness

| Item | Status |
|---|---|
| Harness skeleton | Done |
| Cassette client (replay / record / live) | Done — replay exercised end-to-end |
| 5-category assertion taxonomy | Structural + citation_correctness real; rest stubbed |
| Result file format + writer | Done — round-trip via `from_jsonable` works |
| `manage.py train_lease_agent` CLI | Done — `--scenario`, `--replay/record/live`, `--format`, `--output` |
| Pytest entry point | Done — passes in 0.02s, no DB required |
| One smoke scenario passing | Done — S1 generate-sectional-title-1-tenant-fixed |
| Hand-crafted cassette | Done — 1 JSONL line, hash-matched |
| 8-scenario smoke battery | NOT YET — Day 3+ scope |
| `--battery=smoke` flag | NOT YET — Day 3+ scope |
| Live-API recording exercise | NOT YET — Day 3+ scope |
| Judge / Reviewer / Front Door / Formatter integration | NOT YET — Phase 2 scope |
| `lease-ai-trainer` subagent | NOT YET — Phase 3 scope |
