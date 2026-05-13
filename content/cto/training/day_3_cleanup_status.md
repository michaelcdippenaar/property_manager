# Day 3 cleanup status — G.1 / G.2 / G.3

| Field | Value |
|---|---|
| **Status** | All three follow-ups landed, tests green, ruff clean |
| **Owner** | CTO (Day 3 cleanup workstream G) |
| **Date** | 2026-05-13 |
| **Scope** | Three follow-ups deferred from Day 1-2 workstreams B / C / D, blocking Phase 2 |
| **Source notes** | `content/cto/training/lease_ai_test_harness_day_1_2_status.md` §3.4 items 1 & 3 (C's concerns), `content/cto/training/merge_fields_yaml_upgrade_status.md` §6.6 (D's concern) |
| **Commits / push** | None — staged in dirty state per the cleanup brief |
| **Locked files touched** | None |

---

## 1. TL;DR

- **G.1 — Cassette path canonicalisation.** Stub cassette relocated to the canonical `cassettes/<scenario_id>__<corpus_hash>.jsonl` layout. Harness now resolves the canonical path first; falls back (with a deprecation warning) to the Day-1-2 fixture-adjacent cassette only when exactly one match exists. New `--corpus-hash` CLI override on `train_lease_agent`.
- **G.2 — YAML assertion-key lint.** Misspelled assertion keys under real categories (`structural`, `citation_correctness`) now raise `ScenarioConfigError` at scenario-load time with the sorted list of valid names. Keys under stub categories (`reviewer_pipeline`, `cost_and_latency`, `semantic`) accept any key with a `logger.warning`.
- **G.3 — Render-budget fix.** `render_for_drafter_system_block()` worst case dropped from 4086 chars → 3485 chars (3-tenant townhouse / holiday_let). The 1-tenant freehold case dropped from 3384 → 2796 chars. All supported `(tenant_count, property_type, lease_type)` combos now render under 3900 chars with ≥415 chars of headroom in the worst case.

---

## 2. Files modified

| Path | Change |
|---|---|
| `backend/apps/leases/training/harness.py` | (G.1) Canonical cassette path with legacy fallback. (G.2) `ScenarioConfigError` + `_known_assertion_names()` catalogue + `Scenario._validate_assertion_keys()` lint at load time. |
| `backend/apps/leases/training/__init__.py` | Re-export `ScenarioConfigError`. |
| `backend/apps/leases/management/commands/train_lease_agent.py` | (G.1) New `--corpus-hash` CLI argument threaded through to the harness. |
| `backend/apps/leases/merge_fields_loader.py` | (G.3) `render_for_drafter_system_block()` drops `e.g. <example>` from required-field lines and omits `(string)` annotation for non-required default-typed fields. New `_DEFAULT_FIELD_TYPE` constant + docstring note locking the 3900-char invariant. |
| `backend/apps/leases/training/fixtures/happy/generate-sectional-title-1-tenant-fixed.yaml` | Cassette comment updated to point at the canonical path. |
| `backend/apps/leases/tests/test_training_smoke.py` | New `CassettePathCanonicalisationTests` (2 cases) + `AssertionKeyLintTests` (3 cases). |
| `backend/apps/leases/tests/test_merge_fields_loader.py` | Tightened `test_render_for_drafter_system_block_is_compact`; added `test_render_for_drafter_system_block_worst_case_under_budget`, `test_render_for_drafter_system_block_one_tenant_freehold_under_budget`, `test_render_for_drafter_system_block_all_combos_under_budget` (13 sub-combos), `test_render_omits_example_for_required_fields`, `test_render_omits_default_type_for_non_required_fields`. |

## Files moved (git mv, staged not committed)

| From | To |
|---|---|
| `backend/apps/leases/training/fixtures/happy/generate-sectional-title-1-tenant-fixed__day-1-2-stub.jsonl` | `backend/apps/leases/training/cassettes/generate-sectional-title-1-tenant-fixed__day-1-2-stub.jsonl` |

No code editing of the cassette content itself — just the location.

---

## 3. Test results

```
$ cd backend && .venv/bin/python -m pytest \
    apps/leases/tests/test_training_smoke.py \
    apps/leases/tests/test_merge_fields_loader.py -q --no-cov

apps/leases/tests/test_merge_fields_loader.py .........................  [ 80%]
apps/leases/tests/test_training_smoke.py ......                          [100%]

======================== 31 passed, 1 warning in 1.19s =========================
```

| Suite | Before | After |
|---|---|---|
| `test_training_smoke.py` | 1 | 6 (+5: 2 cassette-path + 3 assertion-lint) |
| `test_merge_fields_loader.py` | 20 | 25 (+5: 1 worst-case budget + 1 one-tenant guard + 1 all-combos sub-battery + 2 rendering shape) |
| Wider `test_regression_battery.py` | 64 | 64 (no regression) |

Ruff: `ruff check apps/leases/training apps/leases/merge_fields_loader.py apps/leases/management/commands/train_lease_agent.py apps/leases/tests/test_training_smoke.py apps/leases/tests/test_merge_fields_loader.py` → "All checks passed!"

---

## 4. Render-budget headroom (G.3)

Worst-case scan across every supported `(tenant_count, property_type, lease_type)`:

| Combo | Chars | Headroom under 3900 |
|---|---|---|
| 1-tenant freehold fixed_term | 2796 | 1104 |
| 1-tenant sectional_title fixed_term | 2744 | 1156 |
| 1-tenant freehold month_to_month | 2722 | 1178 |
| 2-tenant freehold fixed_term | 3151 | 749 |
| 2-tenant sectional_title fixed_term | 3099 | 801 |
| 3-tenant freehold fixed_term | 3469 | 431 |
| 3-tenant sectional_title fixed_term | 3417 | 483 |
| 3-tenant townhouse fixed_term | 3485 | **415 ← worst case** |
| 3-tenant holiday_let fixed_term | 3485 | 415 |
| 3-tenant student fixed_term | 3417 | 483 |
| 3-tenant apartment fixed_term | 3417 | 483 |
| 3-tenant freehold month_to_month | 3395 | 505 |
| 3-tenant sectional_title month_to_month | 3343 | 557 |

The previously-busted 3-tenant + sectional-title + fixed-term render is now 3417 chars (was 4086) — 669 chars saved on the failing path and 415 chars of headroom under the tightened 3900-char invariant on the new worst case.

Strategy used:
1. Drop `, e.g. <example>` from required-field lines. Per the rendering docstring, the example value flows through the structured Context Object — the catalogue's job is to advertise the field, not duplicate the value.
2. Drop the redundant `(string)` annotation for non-required default-typed fields. The field name already implies the shape and the structured Context Object carries the typed value.
3. Tighten the required-field gloss cap from 60 → 50 chars (cosmetic; helps consistency).

Non-required fields with non-default types (`phone`, `email`, `date`, `address`, `sa_id_number`, `enum`, `currency`, `text`) still carry the type annotation — the AI needs that signal for SA-specific shapes like 13-digit IDs and ZAR currency formatting.

---

## 5. Architectural notes

### 5.1 Legacy cassette fallback is time-bound

`LeaseTrainingHarness._find_legacy_cassette()` is a Phase-1 transitional shim. Phase 2 should drop it — the cassettes/ canonical layout is the only supported location going forward. The fallback emits a `logger.warning` so any scenario still relying on it surfaces in CI logs.

### 5.2 Stub-category lint deliberately permissive

Per the cleanup brief, scenario authors are free to declare future `reviewer_pipeline`, `cost_and_latency`, `semantic` assertion keys before Phase 2 implements them. The lint emits a `logger.warning` ("stub category; key not validated") rather than raising, so the S1 fixture's Phase-2-shaped assertions don't trip the lint today.

This is the right trade-off: the lint catches typos in real assertions (which currently silently pass through the stub branch — C's concern #2) without forcing scenario authors to wait for Phase 2 before sketching coverage.

### 5.3 Drafter system-block budget locked at 3900

The 4000-char `cache_control: ephemeral` ceiling is the hard limit; the loader holds itself to 3900 to leave ≥100 chars of headroom for future field additions. The 3-tenant townhouse / holiday_let worst case currently sits at 3485 — i.e. 415 chars of room for the next 8-10 fields before the budget bites. The new `test_render_for_drafter_system_block_all_combos_under_budget` sub-battery guards every supported combo in lockstep.

### 5.4 No changes to locked artefacts

- `backend/apps/leases/agent_runner.py` — not touched.
- `backend/apps/legal_rag/` — not touched (E's territory).
- `backend/apps/leases/lease_law_corpus/` — not touched (B's territory).
- `content/legal/` — not touched (other than the migrated cassette which lives under `backend/apps/leases/training/cassettes/`, not `content/legal/`).
- `docs/system/lease-ai-agent-architecture.md` — not touched.
- `content/cto/lease-ai-testing-and-training-plan.md` — not touched.

### 5.5 Pre-existing E-workstream noise

`manage.py` system checks currently raise `admin.E108` on `apps.legal_rag.admin.LegalFactAdmin.list_display[6]` (`last_changed_at` field reference). This is from the E workstream and pre-dates Day 3 (verified by `git stash` toggle). The pytest path doesn't run the admin check and is unaffected. Flagged here so E can clean it up — not in scope for Day 3.

---

## 6. Phase-2 readiness checklist

| Item | Status |
|---|---|
| Canonical cassette layout adopted | Done (G.1) |
| Legacy fixture-adjacent fallback documented for retirement | Done (G.1) |
| Misspelled assertion keys raise loudly | Done (G.2) |
| Stub-category keys accept any name with warning | Done (G.2) |
| Drafter system block ≤3900 chars on all combos | Done (G.3) |
| 8-scenario smoke battery | NOT YET — Day 3+ scope, outside G workstream |
| `--battery=smoke` flag | NOT YET — Day 3+ scope |
| Live-API recording exercise | NOT YET — Day 3+ scope |
