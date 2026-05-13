# content/legal — canonical SA legal-fact corpus

This directory is the **single source of truth** for South African legal facts that Klikk consumes — statute provisions (RHA, POPIA, CPA, PIE, STSMA, CSOS), case law, cross-statute concepts, and pitfall patterns. Marketing copy, the lease-AI agent, the three legal skills, and any future MCP server all read from here.

The full architectural rationale lives in `content/cto/centralised-legal-rag-store-plan.md`. This README is the **operating manual** — what to edit, what NOT to edit, and how the lawyer-review workflow runs.

## What lives here

| Path | Contains | Lifecycle |
|---|---|---|
| `_schema/legal_fact.schema.json` | JSON Schema 2020-12 for a single fact YAML. | Edited only when the canonical fact shape changes; bump the corpus version. |
| `_schema/attestation.schema.json` | JSON Schema for an attorney-attestation YAML. | Same as above. |
| `statutes/<act>/*.yaml` | One fact per file, named after `concept_id`. | Edit via PR; CI validates against schema; lawyer reviews diff per quarter. |
| `concepts/*.yaml` | Cross-statute concepts (e.g. "deposit refund timing" spans RHA s5(3) + CPA). | Same. |
| `case_law/<jurisdiction>/*.yaml` | Reported judgments cited by the lease AI or audit. | Same. |
| `pitfalls/*.yaml` | Known landlord/agent error patterns the lease AI flags. | Same. |
| `attestations/*.yaml` | Append-only attorney opinion records. | NEVER edit an existing attestation file; only add new ones. |
| `CHANGELOG.md` | Human-readable per-release notes. | Append at corpus-version bump. |

## How to edit (humans + Claude)

1. **Edit YAML in this directory.** Do NOT edit `.claude/skills/` reference files post-Phase A — those are regenerated from this corpus by `manage.py render_legal_skills`. CI fails if skill files have drifted from the YAML.
2. **Validate locally before opening a PR.** Run `python -m jsonschema -i <yaml-as-json> _schema/legal_fact.schema.json`, or simpler, let CI catch it.
3. **One PR per logically grouped change.** A lawyer reviews the diff; granular PRs are 30-second reviews, monster PRs are an hour. Be kind.
4. **Bump `version` + `last_changed_at`** on any content edit. The loader uses `content_hash` to detect physical change; the explicit version field is the contract with downstream consumers.
5. **Never set `verification_status: lawyer_reviewed`** directly — that field is flipped only by `manage.py sync_legal_facts` after an attestation YAML lands referencing the fact.

## What gates each verification status

| Status | Who sets it | What it means for consumers |
|---|---|---|
| `ai_curated` | Claude / agent on draft | Internal-only. Lease-AI Drafter may use with disclaimers. Marketing copy MUST NOT depend on this. |
| `mc_reviewed` | MC merges the PR | Lease-AI Drafter usable. Marketing copy gated on a separate disclaimer-prominent flag (see plan §10). |
| `lawyer_reviewed` | Attestation YAML lands and `sync_legal_facts` flips it | Usable everywhere, including externally-facing legal claims. |

## Lawyer-review workflow (quarterly batched)

1. Engineering ships PRs that land facts at `verification_status: mc_reviewed`.
2. Once a quarter, MC packages all `mc_reviewed` facts with `last_changed_at` since the previous attestation → sends to retained attorney.
3. Attorney returns an opinion letter (PDF, signed) covering each `(concept_id, fact_version)` with a finding (`confirmed | corrected | rejected`).
4. MC writes an attestation YAML in `attestations/<year>-<quarter>-<id>.yaml` and stores the opinion letter PDF in Vault33.
5. `manage.py sync_legal_facts` reads the attestation, links it to the matching `LegalFactVersion`, and flips `verification_status` to `lawyer_reviewed` on confirmed facts.
6. Corrected facts get a new fact version with the lawyer's text; the old version stays queryable for historical leases.

Expected cadence: ~30 min/quarter lawyer time, ~R3000-R6000 fixed fee per cycle. See plan §5 for the cost model.

## What you must NOT do

- **Do NOT edit `.claude/skills/.../references/*.md` files for legal facts.** They are generated. CI will reject your PR.
- **Do NOT edit an attestation YAML after it has been committed.** Attestations are append-only. Add a new attestation instead.
- **Do NOT mark a fact `verification_status: lawyer_reviewed` by hand.** Only the sync command does that, and only when an attestation YAML references the exact `(concept_id, fact_version)` pair.
- **Do NOT add a `statute_text_verbatim: true` field unless a lawyer has read the current consolidated Act and confirmed the text.** The schema rejects this combination at `verification_status != lawyer_reviewed`.
- **Do NOT delete YAML files.** Set `is_active: false` on the corresponding row in the loader; the file moves to `_deprecated/` for historical traceability.

## Phase A status (as of 2026-05-12)

- Day 1-2 scaffold: Django app + models + schemas + 10 seed facts. **<-- you are here**
- Day 3: `manage.py sync_legal_facts` (YAML → Postgres, idempotent).
- Day 4-5: `manage.py verify_citations` + skill renderer.
- Week 2-3: first lawyer attestation, flip 10 HIGH-confidence facts to `lawyer_reviewed`.

See `content/cto/centralised-legal-rag-store-plan.md` §13 for the full phased delivery plan.

## Merge fields

`merge_fields/<category>.yaml` is the canonical catalogue of every Klikk lease merge field — name, label, category, type, applicability (tenant_counts / property_types / lease_types), validation regex, example, plain-English gloss for the AI Drafter, and forward-FK `related_legal_facts` linking to `apps.legal_rag.LegalFact.concept_id`.

| Path | What it contains |
|---|---|
| `_schema/merge_field.schema.json` | JSON Schema 2020-12 enforcing the record shape, the category enum, the applicability matrix, and the tenant-N applicability invariant (a `tenant_2_*` field MUST NOT be applicable when `tenant_count == 1`). |
| `merge_fields/landlord.yaml` etc. | One YAML file per category; each is a list of records. Edit via PR. |
| `backend/apps/leases/merge_fields_loader.py` | Runtime reader + `filter_by_context()` for the lease-AI Front Door. |
| `backend/apps/leases/merge_fields.py` | Backwards-compat shim. Reads from the loader; will be retired in lease-AI Phase 2. |

The Django system check `apps.legal_rag.checks.check_legal_facts_schema` validates this directory against the schema at startup and on `manage.py check`. Fail-soft (`Warning`) like the legal_fact check.

See `docs/system/lease-ai-agent-architecture.md` §2 failure mode 2 + §6.6 for the design driver: the Drafter's cached merge-fields system block is built per-request from `filter_by_context()` so it never sees `tenant_2_*` fields for a 1-tenant lease.
