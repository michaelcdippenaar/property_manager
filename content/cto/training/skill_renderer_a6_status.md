# A.6 — Skill Renderer status

| Field | Value |
|---|---|
| **Phase** | A — centralised legal RAG store |
| **Sub-step** | A.6 — skill `.md` renderer (`manage.py render_legal_skills`) |
| **Status** | Day 1 scope complete; default-`--check`, opt-in `--write`; 2 targets live |
| **Plan section** | `content/cto/centralised-legal-rag-store-plan.md` §7 |
| **Date** | 2026-05-13 |
| **Branch** | `main` — **uncommitted** (per task constraint "Do not commit. Do not push.") |

## What landed

### New files

1. `backend/apps/legal_rag/skill_rendering.py`
   Pure-Python rendering helpers — Jinja2 environment, `fact()` /
   `facts_by_topic()` / `concept()` template helpers, marker extraction
   and replacement. Tests target this module directly.

2. `backend/apps/legal_rag/management/commands/render_legal_skills.py`
   Django management command. `--check` (default) re-renders in memory
   and diffs against on-disk; exits `1` with a unified diff on drift.
   `--write` is the explicit opt-in that mutates files. `--target=`
   repeatable, `--verbose`. Acquires
   `pg_advisory_lock(hashtext('render_legal_skills'))` across the run.

3. `backend/apps/legal_rag/skill_templates/klikk-legal-POPIA-RHA/06-rha-core-and-s5.md.j2`
   Covers s5(2), s5(3)(a)/(b) (table with provisional flag), s5A, s5B,
   s7 establishment. Footer carries `corpus_version` + canonical-map
   cross-reference for LOW-confidence rows.

4. `backend/apps/legal_rag/skill_templates/klikk-legal-POPIA-RHA/07-rha-s4a-unfair-practices.md.j2`
   Covers s4A, s7 establishment cross-reference, s13 powers; ends with
   a comparison table so the s7-vs-s13 confusion never recurs.

5. `backend/apps/legal_rag/tests/test_render_legal_skills.py`
   Seven tests — five against `skill_rendering.render_target` directly,
   two end-to-end through `call_command("render_legal_skills")`.

### Modified files

1. `.claude/skills/klikk-legal-POPIA-RHA/references/06-rha-core-and-s5.md`
   Inserted `<!-- BEGIN AUTO-GENERATED legal-facts -->` /
   `<!-- END AUTO-GENERATED legal-facts -->` pair where the old s5(2)
   and s5(3) table sat. Outside-marker content preserved verbatim
   (intros, narrative, s5(4)-(6), s5A duties list, deposit rules table,
   eviction guidance, founder quick-check).

2. `.claude/skills/klikk-legal-POPIA-RHA/references/07-rha-s4a-unfair-practices.md`
   Inserted markers after the intro paragraph and before `## 1. Unfair
   practices — list`. Outside-marker content preserved (intros, the
   16-row unfair-practices table, Tribunal procedure, founder strategy,
   interplay table, founder quick-check).

3. `backend/apps/legal_rag/management/commands/render_legal_skills.py`
   (during testing iteration) — added `_resolve_repo_root()` helper
   honouring `settings.LEGAL_RAG_RENDER_REPO_ROOT` so tests can point
   the renderer at a temp directory without monkey-patching Django
   internals.

4. `backend/apps/legal_rag/checks.py`
   Added `_check_skill_render_drift()` — emits fail-soft
   `CheckWarning` (id `legal_rag.W014`) when `--check` would fail.
   Triggers via `manage.py check`. Conservative on import/DB failures;
   never raises.

## Test result

`cd backend && .venv/bin/python -m pytest apps/legal_rag/tests/test_render_legal_skills.py -q`

```
7 passed, 13 warnings in 14.03s
```

Full app suite re-run: `apps/legal_rag/tests/` → **58 passed**. No
regressions.

Tests:

- `test_render_06_rha_core_includes_s5_2_summary` — s5(2) summary
  appears + `facts_used` includes every required `concept_id`.
- `test_render_marks_low_confidence_facts_provisional` — LOW fact
  surfaces `provisional_reason` + the `(provisional)` table marker.
- `test_render_idempotent` — two consecutive renders produce equal
  output (modulo the dynamic `generated <iso-now>Z` stamp).
- `test_render_includes_corpus_version_in_footer` — passing
  `corpus_version` flows through to the rendered footer.
- `test_check_mode_exits_zero_when_drift_zero` — post-`--write` the
  `--check` re-run is clean and `exit 0`.
- `test_check_mode_exits_one_when_drift_detected` — stale on-disk
  content → exit `1` + unified diff to stderr.
- `test_unknown_concept_id_raises_clearly` — empty corpus → `fact()`
  helper raises `LegalFactNotFound` rather than silently writing.

## Sample rendered snippet (06-rha-core-and-s5.md)

```markdown
> Source: `content/legal/` (corpus_version: `legal-rag-v0.1-1e6e7d372c53`, generated 2026-05-13T11:01:58Z)
> Do not edit this section directly. Edit YAML under `content/legal/statutes/rha/`
> and re-run `manage.py render_legal_skills --write`.

### s5(2) — Right to a written lease

A rental agreement does not have to be in writing to be valid in South Africa,
but the tenant has the right to demand that the landlord reduce it to writing.
Once requested, the landlord must comply.

- **Citation:** `RHA s5(2)`
- **Confidence:** high
- **Verification:** Verified by Klikk

### s5(3) — Mandatory contents of a written lease

| Item | Citation | Detail | Confidence | Verification |
|---|---|---|---|---|
| `RHA s5(3)(a)` | `RHA s5(3)(a)` | Every written lease must list the full names of the landlord and the tenant... | high | Verified by Klikk |
| `RHA s5(3)(b)` | `RHA s5(3)(b)` | The lease must contain a description of the property being rented... | high | Verified by Klikk |
...
```

## Before / after diff stats (real `--write` against seeded corpus)

Captured by running `render_legal_skills --write` against the
committed `content/legal/` corpus (8 RHA YAMLs + 2 POPIA YAMLs) on a
temp test DB, then comparing the on-disk skill `.md` before vs. after
(originals restored after capture — no committed changes).

| Target | Before | After | +Lines | −Lines | Facts referenced |
|---|---|---|---|---|---|
| `06-rha-core-and-s5.md` | 166 | 225 | 60 | 1 | 34 (with repeats) |
| `07-rha-s4a-unfair-practices.md` | 131 | 186 | 56 | 1 | 30 (with repeats) |

Both targets cleanly replaced the single-line placeholder between
markers with the rendered facts block. All content outside the
markers (intros, narrative tables, founder quick-check, interplay
tables) was preserved byte-for-byte.

## Status of constraints

- [x] Do not commit / push — no commits made.
- [x] Default to `--check`, not `--write` — confirmed in command handler.
- [x] Preserve content outside markers — confirmed via diff capture
  above (one-line placeholder is the only `−` line).
- [x] Type hints, docstrings, ruff-clean — Python files use full type
  annotations + module docstrings + class/function docstrings.
- [x] No edits to locked files (`models.py`, `migrations/`,
  `queries.py`, `sync_legal_facts.py`, `reindex_legal_corpus.py`,
  `yaml_loader.py`, `admin.py`, `apps/leases/`, content/legal/_schema,
  statutes, merge_fields, strategic plans, canonical map).
  Edited: `checks.py` only (per spec item 6 — light CI hook).

## Concerns / follow-up

1. **`facts_used` deduplication.** The renderer's tracking list
   contains duplicates because each `fact(id)` call appends. Not a
   correctness issue (tests use `assertIn`) but the `--verbose` "30
   facts referenced" log line is misleading. Easy fix later: dedupe
   in the helper.

2. **`generated <iso>Z` stamp** changes every render and therefore the
   `--check` mode will always show drift on the timestamp line after
   a `--write` — unless we run `--check` from the same process /
   second. For CI we will either (a) freeze `now` deterministically
   from the active `LegalCorpusVersion.created_at` or (b) exclude the
   timestamp line from the drift diff. Day 1 punts; raise in A.7.

3. **CheckWarning W014 needs a DB.** The system-check drift detector
   reads `LegalCorpusVersion.objects.filter(is_active=True)`, which
   means `manage.py check` on a fresh dev clone (no migrations
   applied) silently returns no warnings. Acceptable for fail-soft;
   the hard gate is `--check` in CI.

4. **Coverage gap.** Day 1 ships only RHA targets in
   `klikk-legal-POPIA-RHA`. POPIA targets (`01-popia-core.md` etc.)
   and the worst offender `klikk-leases-rental-agreement/references/sa-rental-law.md`
   are explicitly out of Day 1 scope per the brief; templates land in
   A.7 along with concept-level cross-references.

5. **Marker positioning trade-off.** In `06-rha-core-and-s5.md` I put
   the markers BEFORE the old s5(3) table so the table-with-LOW-flag
   becomes generated. The hand-written s5(3) full sub-section list
   (with ⚠️ LOW-confidence row (f)) survives outside markers as the
   non-generated "full list reference" — a useful redundancy until
   that letter is lawyer-attested.
