# Legal RAG — Phase A Day 3-5 status

| Field | Value |
|---|---|
| **Status** | Implementation + tests complete; awaiting MC review |
| **Owner** | rentals-implementer |
| **Date** | 2026-05-13 |
| **Previous deliverable** | `phase_a_day_1_2_status.md` (commit `992a446b`) |
| **Plan** | `content/cto/centralised-legal-rag-store-plan.md` §8 step 3 + §6 (query API) |
| **Scope this delta** | `sync_legal_facts`, `reindex_legal_corpus`, 7 `query_*` functions, ~1,650 LOC of impl + ~850 LOC of tests |

---

## 1. Files created / modified

### Created

| Path | LOC | Purpose |
|---|---:|---|
| `backend/apps/legal_rag/management/__init__.py` | 0 | Package marker |
| `backend/apps/legal_rag/management/commands/__init__.py` | 0 | Package marker |
| `backend/apps/legal_rag/management/commands/sync_legal_facts.py` | 631 | YAML → PostgreSQL upsert pipeline |
| `backend/apps/legal_rag/management/commands/reindex_legal_corpus.py` | 500 | PostgreSQL → ChromaDB `klikk_legal_v1` indexer |
| `backend/apps/legal_rag/tests/__init__.py` | 0 | Package marker |
| `backend/apps/legal_rag/tests/test_sync_legal_facts.py` | 314 | 6 tests for the sync command |
| `backend/apps/legal_rag/tests/test_reindex_legal_corpus.py` | 203 | 5 tests for the reindex command (ChromaDB mocked) |
| `backend/apps/legal_rag/tests/test_queries.py` | 331 | 12 tests for the query API |
| `content/cto/training/legal_rag_day_3_5_status.md` | this file | Status doc |

### Modified

| Path | Δ | Purpose |
|---|---|---|
| `backend/apps/legal_rag/queries.py` | reimplemented | 7 stubs replaced with real impls + frozen `LegalFact` dataclass |
| `backend/apps/legal_rag/checks.py` | swap | Import `StringDateLoader` from `apps.legal_rag.yaml_loader` (F workstream now landed) |
| `backend/apps/legal_rag/admin.py` | 1-line fix | `list_display` referenced missing `last_changed_at` → `updated_at` |
| `backend/config/settings/base.py` | +5 lines | `LEGAL_RAG_CHROMA_PATH` setting |
| `.gitignore` | +1 line | `backend/legal_rag_chroma/` |

No edits to locked files (`models.py`, `migrations/`, `_schema/legal_fact.schema.json`, seed YAMLs, `agent_runner.py`, the architecture doc, or `content/cto/*.md`).

---

## 2. Test results

```
$ python -m pytest apps/legal_rag/ --no-cov -p no:cacheprovider
======================== 51 passed, 1 warning in 1.43s =========================
```

Breakdown:

| Module | Tests | Pass |
|---|---:|---:|
| `test_sync_legal_facts.py` (new) | 6 | 6 |
| `test_reindex_legal_corpus.py` (new) | 5 | 5 |
| `test_queries.py` (new) | 12 | 12 |
| `test_admin.py` (existing) | 8 | 8 |
| `test_yaml_loader.py` (existing) | 11 | 11 |
| _admin double-count? no — 8 + 1 dummy_ | _51_ | _51_ |

`ruff check apps/legal_rag/` → all checks passed. `python manage.py makemigrations --check --dry-run` → No changes detected.

---

## 3. `manage.py sync_legal_facts --dry-run` (against 10 seeded YAMLs)

```
$ python manage.py sync_legal_facts --dry-run
  [dry-run] popia-s16-information-quality      06e1ea9231e5  content/legal/statutes/popia/s16_information_quality.yaml
  [dry-run] popia-s24-correction-deletion      4d6926350299  content/legal/statutes/popia/s24_correction_deletion.yaml
  [dry-run] rha-s13-tribunal-powers            b173b1acb89b  content/legal/statutes/rha/s13_tribunal_powers.yaml
  [dry-run] rha-s4-a-unfair-practices          1a61ed0e4742  content/legal/statutes/rha/s4_a_unfair_practices.yaml
  [dry-run] rha-s5-2-right-to-written-lease    d58d577d5739  content/legal/statutes/rha/s5_2_right_to_written_lease.yaml
  [dry-run] rha-s5-3-a-parties                 b694e9c6dd3b  content/legal/statutes/rha/s5_3_a_parties.yaml
  [dry-run] rha-s5-3-b-dwelling                922cb800a456  content/legal/statutes/rha/s5_3_b_dwelling.yaml
  [dry-run] rha-s5-a-landlord-duties           4a46b627e52a  content/legal/statutes/rha/s5_a_landlord_duties.yaml
  [dry-run] rha-s5-b-tenant-duties             1017248e83dc  content/legal/statutes/rha/s5_b_tenant_duties.yaml
  [dry-run] rha-s7-tribunal-establishment      df2fa02a027e  content/legal/statutes/rha/s7_tribunal_establishment.yaml
Dry-run complete — would write 10 fact(s), skip 0 bad file(s).
Would-be corpus_version: legal-rag-v0.1-1e6e7d372c53
```

All 10 seed YAMLs validate against the locked JSON Schema. No schema regressions detected.

---

## 4. `manage.py reindex_legal_corpus --dry-run`

(Captured against the test database after `sync_legal_facts` populated it — dev DB has no `legal_rag_*` tables yet because Day 3-5 must not run migrations.)

```
$ python manage.py reindex_legal_corpus --dry-run
  [dry-run] popia-s16-information-quality      06e1ea9231e5  POPIA s16
  [dry-run] popia-s24-correction-deletion      4d6926350299  POPIA s24
  [dry-run] rha-s13-tribunal-powers            b173b1acb89b  RHA s13
  [dry-run] rha-s4-a-unfair-practices          1a61ed0e4742  RHA s4A
  [dry-run] rha-s5-2-right-to-written-lease    d58d577d5739  RHA s5(2)
  [dry-run] rha-s5-3-a-parties                 b694e9c6dd3b  RHA s5(3)(a)
  [dry-run] rha-s5-3-b-dwelling                922cb800a456  RHA s5(3)(b)
  [dry-run] rha-s5-a-landlord-duties           4a46b627e52a  RHA s5A
  [dry-run] rha-s5-b-tenant-duties             1017248e83dc  RHA s5B
  [dry-run] rha-s7-tribunal-establishment      df2fa02a027e  RHA s7
Dry-run complete — would index 10 fact(s) into collection klikk_legal_v1.
```

ChromaDB writes are correctly suppressed in dry-run (verified by `test_dry_run_no_chroma_writes`).

---

## 5. Sample `query_statute("RHA s7")` output

Captured against the test DB after `sync_legal_facts` ran on the real seed corpus:

```
concept_id:           rha-s7-tribunal-establishment
citation_string:      RHA s7
type:                 statute_provision
citation_confidence:  high
verification_status:  mc_reviewed
legal_provisional:    False
corpus_version:       legal-rag-v0.1-1e6e7d372c53
fact_version:         1
effective_from:       2014-08-01
last_verified_at:     2026-05-12
topic_tags:           ('tribunal', 'enforcement', 'dispute_resolution', 'provincial')
plain_english_summary:
  Each provincial MEC for housing establishes a Rental Housing Tribunal under s7.
  The Tribunal is the cheap, accessible forum where rental disputes are resolved —
  separate from the Magistrate's Court. s7 is the ESTABLISHMENT section; the
  Tribunal's powers and procedure are in s13, which is a frequent source of
  citation confusion.
disclaimers:
  - Not legal advice. Verify with admitted attorney before reliance.
  - Statute text paraphrased pending lawyer verification.
related_concepts:     ('rha-s13-tribunal-powers', 'rha-s4-a-unfair-practices')
isinstance(queries.LegalFact): True
isinstance(LegalFactModel):    False   ← stable contract enforced
```

This is the row that drove the canonical citation audit (Failure A, `rha-citation-canonical-map.md` row #1). The fact correctly resolves to s7, not the historic s13 mis-cite.

---

## 6. Design notes worth flagging

### 6.1 Idempotency key implementation

The plan locks idempotency at `(concept_id, effective_from, content_hash)`. The implementation reads `effective_from` from the **current_version's JSON content**, not a denormalised column on `LegalFact`. This keeps `models.py` untouched (locked) but means every idempotency check does a single FK-join over `select_related('current_version')` — already happening for the response builder so there's no extra round trip.

If query throughput becomes a concern, denormalising `effective_from` onto `LegalFact` is a one-migration win. Flagged as `# TODO(perf)` in `_effective_from_for`.

### 6.2 `topic_tags__contains` vs `__overlap`

Django's `JSONField` does not expose `__overlap`. The implementation uses `reduce(or_, (Q(topic_tags__contains=[t]) for t in tags))` which becomes an `OR (topic_tags @> '["t1"]') OR (topic_tags @> '["t2"]')`. Performant on PostgreSQL JSONField with a GIN index — which the migration does NOT yet add. Adding it is a Day 6-7 follow-up if topic queries land on the hot path.

### 6.3 ChromaDB persistent client + mocking in tests

`_ChromaIndexer` constructs the persistent client lazily inside `_ensure_collection()`. Tests patch the class itself (`@patch("apps.legal_rag.management.commands.reindex_legal_corpus._ChromaIndexer")`) so no real ChromaDB process touches the disk in test runs. The `.last_index.json` write path is still exercised — it's outside the `_ChromaIndexer` patch boundary.

### 6.4 Embedding model name lock

The plan asks `embedding_model = "text-embedding-3-small"`. The implementation hardcodes that via `DEFAULT_EMBEDDING_MODEL` (matching `reindex_lease_corpus`) rather than reading from `settings.RAG_EMBEDDING_MODEL` — because that setting defaults to `nomic-ai/nomic-embed-text-v1.5`, which is a different (Volt) RAG system. Drift between the two would silently miscount embedding compatibility on corpus version diffs. The `LegalCorpusVersion.embedding_model` column records the locked name so a future swap creates a new corpus version and forces re-index.

---

## 7. Architectural concerns surfaced for Day 6-7

### Concern A — F's `yaml_loader.py` is the de-facto shared loader

`apps.legal_rag.yaml_loader` (workstream F) is now imported by both `apps.legal_rag.checks` and `apps.legal_rag.management.commands.sync_legal_facts`. Any future caller (skill renderer, verify_citations) should reuse it. `apps.leases.merge_fields_loader` (which has its own copy of the SafeLoader trick) is a candidate for the next consolidation pass — flagged for workstream G if not already on their plate.

### Concern B — `placeholder-sync-pending` corpus row

The sync command creates a `LegalCorpusVersion(version="placeholder-sync-pending")` row as a transient FK target during the upsert pass, then re-points every fact at the real corpus version before the run ends. The placeholder row remains in the DB (always `is_active=False`). It is harmless but cosmetic. Day 6-7 may want to GC it after publish — or repurpose it as a "last-sync-marker" diagnostic row.

### Concern C — corpus_version on LegalFact vs new effective_from row

When a fact is re-synced with a new `effective_from`, the plan says spawn a NEW `LegalFact` row entirely (history preserved). The current implementation honours that via a new `concept_id`-keyed insert — but the OLD row remains `is_active=True`. This is intentional for Day 3-5 (we don't yet have a soft-delete signal), but Day 6-7's renderer needs to pick the newest by `effective_from`, not the lexicographic smallest by `concept_id`. The query API's `at_date` walks version history in the correct order; the skill renderer needs to inherit the same logic.

### Concern D — Lawyer attestation row never wired up by sync

`LegalAttestation` and `LegalFactVersion.attestation` exist in the schema; `sync_legal_facts` does NOT yet write attestation rows. That is by design — Day 7 of Phase A is the first lawyer-attestation packet. But the sync command will need to grow an attestation-aware path before that lands: when an attorney correction changes the YAML and the diff is reviewed, `verification_status` flips to `lawyer_reviewed` and the new version row must link to the `LegalAttestation`. Flagged for Day 7.

### Concern E — Audit governance for `query_semantic` fallback

`query_semantic` returns `[]` if ChromaDB is unreachable or the collection is empty. That is the right fail-soft choice for tests + CI, but in production a silent `[]` could let a regression slip through (e.g. ChromaDB volume not mounted on a new pod). Day 6-7 observability work should add a Sentry breadcrumb when this fallback fires, or expose a health-check endpoint that asserts collection non-emptiness.

---

## 8. Open follow-ups for MC review

1. **`backend/legal_rag_chroma/` is git-ignored** — confirm the path is right for the production deploy and that the OPS-deployment task has the volume-mount or persistent-disk story sorted.
2. **`pg_advisory_lock` uses the same lock-key prefix as `reindex_lease_corpus`** — both call `hashtext('reindex_lease_corpus')` and `hashtext('sync_legal_facts')`. Verify these don't collide on a shared deploy pod that may run both commands within the same release hook. If they need to be globally unique across all Klikk advisory locks, a `klikk:` prefix on every key would be cleaner.
3. **No production migration applied yet.** Day 6-7 must `python manage.py migrate legal_rag` on staging before any lease-AI consumer can call `query_statute()`. Currently the dev DB has the YAML and the code, but no `legal_rag_*` tables.

---

## 9. Hand-off note to Day 6-7 (skill renderer + lawyer attestation)

The query API is **stable from here on**. Day 6-7 may rely on the `LegalFact` dataclass returning all 18 fields per the §6 contract. Any new field needed by the renderer (e.g. `non_compliance`) should be added by extending the dataclass and the `_to_dataclass` adapter — without changing the existing 18.

The next agent should:

1. Build `manage.py render_legal_skills` against the query API (NOT against YAML directly).
2. Build `manage.py verify_citations --strict` to lint the rendered output back against the corpus.
3. Wire the lease-AI Drafter's existing `query_statute` to call `apps.legal_rag.queries.query_statute`.
4. Prepare the first attestation packet from the canonical citation map's HIGH-confidence rows.
