# Lease AI — Phase 1, Day 1-2 — Status

| Field | Value |
|---|---|
| **Status** | Day 1-2 scaffold complete. Clauses corpus + indexer + queries + tests green. |
| **Owner** | rentals-implementer |
| **Date** | 2026-05-13 |
| **Scope** | Clauses corpus only (statutes/case_law/pitfalls owned by `apps.legal_rag`). Corpus directory, JSON schema, 3 seed clauses, indexer command, query API, integration test. |
| **Out of scope** | Statutes / case law / pitfall corpora (live in `apps.legal_rag` per central RAG plan §8 step 6). Drafter wiring (Day 3+). |

---

## 1. Files created

| Path | Lines | Purpose |
|---|---|---|
| `backend/apps/leases/lease_law_corpus/README.md` | 95 | Conventions, layout, indexer + query API instructions; cross-reference to `apps.legal_rag` for statutes. |
| `backend/apps/leases/lease_law_corpus/_schema/clause_chunk.schema.json` | 142 | JSON Schema 2020-12. `additionalProperties: false`. id regex `^clause-[a-z0-9-]+-v\d+$`; `related_citations` regex `^(rha|popia|cpa|pie|stsma|csos)-[a-z0-9-]+$`; `applicability.property_types` enum. |
| `backend/apps/leases/lease_law_corpus/clauses/deposit/deposit-interest-bearing-account-v1.yml` | 61 | RHA s5(3)(f) interest-bearing-account clause. Flagged `citation_confidence: low` + `legal_provisional: true` per canonical map row 11. |
| `backend/apps/leases/lease_law_corpus/clauses/deposit/deposit-amount-and-purpose-v1.yml` | 55 | Deposit amount + purpose clause. `citation_confidence: high`. |
| `backend/apps/leases/lease_law_corpus/clauses/parties/lease-must-be-written-recital-v1.yml` | 49 | RHA s5(2) written-lease recital. `citation_confidence: high`. |
| `backend/apps/leases/management/commands/reindex_lease_corpus.py` | 379 | Walks `clauses/**/*.yml`, validates against schema, content-hashes, acquires `pg_advisory_lock(hashtext('reindex_lease_corpus'))`, embeds (`text-embedding-3-small` or deterministic mock when no `OPENAI_API_KEY`), upserts to `klikk_lease_clauses_v1` ChromaDB collection, writes `.last_index.json`. `--dry-run` and `--check` flags. |
| `backend/apps/leases/lease_law_corpus_queries.py` | 264 | `query_clauses(...)` returns `list[ClauseChunk]` (frozen dataclass). Metadata-filter + semantic-search paths. `get_corpus_hash()` reads `.last_index.json` so the runner can stamp `AILeaseAgentRun.corpus_version`. |
| `backend/apps/leases/tests/test_clauses_corpus.py` | 196 | 7 tests: 1× schema file present, 1× ≥3 seed clauses present, 1× every seed validates + hashes + id-stem matches filename, 1× `--dry-run` exit 0, 1× `--check` exit 0, 2× `query_clauses` against mocked Chroma. |
| `backend/config/settings/base.py` | +5 | Added `LEASE_AI_CHROMA_PATH` next to `RAG_CHROMA_PATH` (default `BASE_DIR / "lease_ai_chroma"`). No other settings touched. |

Also written by the indexer at runtime:

- `backend/apps/leases/lease_law_corpus/.last_index.json` — `run_at`, `chunk_count: 3`, `corpus_hash: 3ff4b159…`, `embedding_model`, `indexed`, `skipped`, `collection_name`.
- `backend/lease_ai_chroma/chroma.sqlite3` + per-collection HNSW segments — created on first real index run.

**Did not create:** `clauses/statutes/`, `clauses/case_law/`, `clauses/pitfalls/`, or any `apps.legal_rag` files. Per the central RAG plan those live elsewhere.

## 2. ChromaDB chunk count after first index run

First `manage.py reindex_lease_corpus` run:

```
OPENAI_API_KEY not set — using deterministic mock embedder. ChromaDB will hold real chunks, but vector similarity is hash-based, not semantic. Set OPENAI_API_KEY for production.
Indexed 3 new/changed clause(s); skipped 0 unchanged. Collection: klikk_lease_clauses_v1 at /Users/mcdippenaar/PycharmProjects/tremly_property_manager/backend/lease_ai_chroma.
```

Second run (idempotency check):

```
Indexed 0 new/changed clause(s); skipped 3 unchanged.
```

`--dry-run` output:

```
[dry-run] clause-deposit-amount-and-purpose-v1                    (9735879d49aa)  clauses/deposit/deposit-amount-and-purpose-v1.yml
[dry-run] clause-deposit-interest-bearing-account-v1              (a20bd327eb48)  clauses/deposit/deposit-interest-bearing-account-v1.yml
[dry-run] clause-lease-must-be-written-recital-v1                 (bb6080567420)  clauses/parties/lease-must-be-written-recital-v1.yml
Dry-run complete. 3 clause(s) would be indexed.
```

`--check` output:

```
Schema check PASSED for 3 clause file(s).
```

## 3. Test results

```
$ cd backend && .venv/bin/python -m pytest apps/leases/tests/test_clauses_corpus.py --no-cov -q
apps/leases/tests/test_clauses_corpus.py .......                         [100%]
========================= 7 passed, 1 warning in 0.47s =========================
```

Ruff (`ruff check`) passes on all three new Python files.

## 4. Concerns / follow-ups for MC

1. **Mock embedder, not OpenAI.** Day 1-2 ran without `OPENAI_API_KEY`. The corpus is in ChromaDB and round-trippable, but the vectors are sha256-based, not semantic. Real semantic retrieval needs `OPENAI_API_KEY` exported before the first prod `reindex_lease_corpus` — at which point the chunks should be deleted and re-indexed so they carry real embeddings (the indexer's content-hash check will skip them otherwise; suggest a one-time `--force` flag or wiping the collection on first prod cutover).
2. **`citation_confidence: low` on the flagship deposit clause.** The interest-bearing-account clause (`rha-s5-3-f-…`) is LOW confidence per `content/cto/rha-citation-canonical-map.md` row 11 (1999 Gazette says (d), three skills say (f)). It is shipped flagged `legal_provisional: true` per architecture §6.5.1; the Reviewer should already refuse external release without override. Confirm that gating is wired before any external customer sees a generated lease.
3. **`related_citations` is a structural FK only.** The schema enforces the shape `^(rha|popia|cpa|pie|stsma|csos)-[a-z0-9-]+$` but does not check whether the target concept_id actually exists in `apps.legal_rag`. That cross-reference resolution is the central RAG plan's verifier CLI (`manage.py verify_citations`) — out of scope here, but the lease-AI indexer will happily index a clause that cites a non-existent statute fact today.
4. **`pg_advisory_lock` is no-op on non-Postgres backends.** The indexer logs a warning and continues when `connection.vendor != "postgresql"`. In CI/SQLite contexts this is fine; in prod (Postgres) the lock is real.
5. **Field naming drift from the architecture doc's example.** §6.2's example uses `text` / `merge_fields` / `citations`; this scaffold standardised on `clause_body` / `merge_fields_used` / `related_citations` for clarity and to match the Drafter's eventual tool-call shape. Update the architecture doc to match next time it's edited — easier than back-renaming the YAML.
6. **`AILeaseAgentRun.corpus_version` stamping.** `query_clauses` ships with `get_corpus_hash()` so the runner can stamp `corpus_version` (decision 20) on every persisted run. The runner does not yet call it — wire-up belongs in the Day 3+ Drafter integration.

## 5. Locked decisions referenced

- **5** — ChromaDB-in-app for v1, MCP server in v2.
- **6** — Canonical YAML under `backend/apps/leases/lease_law_corpus/`, indexed by `manage.py reindex_lease_corpus`, NOT on startup.
- **7** — Code-only YAML + git PR for v1 (no admin UI).
- **8** — Tags + citations + semantic on the same chunks; this scaffold provides all three (`topic_tags`, `related_citations`, embedded `clause_title + clause_body`).
- **18** — Prompt caching layout — the corpus is shaped to slot into the Drafter's `RAG_CHUNKS_BLOCK` system block.
