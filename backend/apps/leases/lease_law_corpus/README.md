# Lease-AI clauses corpus

Canonical, version-controlled YAML clauses used by the lease-AI Drafter
(`apps.leases.agent_runner.LeaseAgentRunner`). This corpus is **clauses
only** — statutes, case law, and pitfall patterns live in
`apps.legal_rag` under `content/legal/`. See
`content/cto/centralised-legal-rag-store-plan.md` §8 step 6 for the
boundary.

## Layout

```
backend/apps/leases/lease_law_corpus/
├── README.md                                    # this file
├── _schema/
│   └── clause_chunk.schema.json                 # JSON Schema 2020-12
├── .last_index.json                             # written by reindex_lease_corpus
└── clauses/
    ├── deposit/*.yml
    ├── parties/*.yml
    └── …
```

Every YAML file is one clause. The id (`clause-<slug>-v<n>`) is canonical
and must match the filename stem (without `.yml`).

## Schema

`_schema/clause_chunk.schema.json` is the authoritative shape. Required
fields:

- `id` — `^clause-[a-z0-9-]+-v\d+$`
- `type` — always `clause`
- `version` — integer; bump on substantive edit; `id` suffix must match
- `clause_title`
- `clause_body` — may contain `{{ merge_field }}` placeholders
- `topic_tags` — at least one
- `applicability.property_types`, `applicability.tenant_counts`, `applicability.lease_types`
- `merge_fields_used` — must list every placeholder used inside `clause_body`

Optional:

- `related_citations` — list of `apps.legal_rag` concept_ids (e.g.
  `rha-s5-3-f-deposit-interest-bearing-account`). FK to legal_rag; this
  corpus does not validate the target exists, only the id shape.
- `disclaimers`, `citation_confidence`, `legal_provisional`,
  `effective_from`, `last_reviewed_at`, `curator`, `confidence_level`,
  `notes`.

`additionalProperties: false` — typos in field names fail the indexer.

## Indexing

```sh
cd backend
.venv/bin/python manage.py reindex_lease_corpus           # idempotent full index
.venv/bin/python manage.py reindex_lease_corpus --dry-run # parse + validate only, no Chroma writes
.venv/bin/python manage.py reindex_lease_corpus --check   # schema-only; exits non-zero on first failure (CI gate)
```

The indexer:

1. Walks `clauses/**/*.yml`.
2. Validates each against `_schema/clause_chunk.schema.json`.
3. Computes `content_hash = sha256(canonical_yaml_str)` of the
   normalised YAML (sorted keys, no aliases).
4. Acquires `pg_advisory_lock(hashtext('reindex_lease_corpus'))` to
   prevent concurrent reindex runs across workers.
5. Embeds `clause_title + " " + clause_body` via
   `text-embedding-3-small` (or a deterministic mock embedder if
   `OPENAI_API_KEY` is missing — logs a clear warning).
6. Upserts into the ChromaDB collection `klikk_lease_clauses_v1` at
   `settings.LEASE_AI_CHROMA_PATH`.
7. Skips chunks whose `content_hash` already matches the live index
   (idempotent).
8. Writes `.last_index.json` with `corpus_hash`, chunk count, and
   embedding model.

**Not run on app startup.** See architecture doc §6.3.

## Query API

```python
from apps.leases.lease_law_corpus_queries import query_clauses

clauses = query_clauses(topic_tags=["deposit"])
```

Returns `list[ClauseChunk]` — see `apps.leases.lease_law_corpus_queries`
for the dataclass shape. Used by the Drafter's Front Door push pattern
(decision 9).

## Statutes / case law / pitfalls

Out of scope for this directory. Authored under `content/legal/` and
served by `apps.legal_rag.queries`. Do **not** add `statutes/`,
`case_law/`, or `pitfalls/` subdirectories here — the central RAG plan
migrates them to `apps.legal_rag` (parallel workstream).

## Citation references

`related_citations` are FK strings into `apps.legal_rag`. The shape is
enforced (`^(rha|popia|cpa|pie|stsma|csos)-[a-z0-9-]+$`); cross-reference
resolution (i.e. "this concept_id actually exists") is done by the
`apps.legal_rag` verifier CLI, not here.

For canonical statute citations, defer to
`content/cto/rha-citation-canonical-map.md` until the lawyer-attestation
cycle produces signed YAML facts. Until then, LOW-confidence rows must
set `citation_confidence: low` and `legal_provisional: true`.
