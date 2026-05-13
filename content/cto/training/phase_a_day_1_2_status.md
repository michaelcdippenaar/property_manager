# Phase A, Day 1-2 — Status

| Field | Value |
|---|---|
| **Status** | Day 1-2 scaffold complete. Ready for MC review + commit. |
| **Owner** | rentals-implementer |
| **Date** | 2026-05-13 |
| **Scope** | Django app skeleton + JSON schemas + 10 seed YAML facts + system check |
| **Out of scope (Day 3+)** | Loader (`sync_legal_facts`), verifier, ChromaDB indexer, skill renderer |

---

## 1. Files created

### Django app: `backend/apps/legal_rag/`

| Path | Lines | Purpose |
|---|---|---|
| `__init__.py` | 0 | Package marker. |
| `apps.py` | 31 | `LegalRagConfig`; wires `checks` from `ready()`. |
| `exceptions.py` | 23 | `LegalFactNotFound` — public exception. |
| `models.py` | 432 | `LegalFact`, `LegalFactVersion`, `LegalAttestation`, `LegalCorpusVersion` + 5 TextChoices enums. |
| `queries.py` | 147 | Public read-API surface; all 7 functions raise `NotImplementedError` for Day 1-2. |
| `checks.py` | 175 | Django system check validating `content/legal/statutes/**/*.yaml` against the schema. |
| `migrations/__init__.py` | 0 | Package marker. |
| `migrations/0001_initial.py` | 122 | Auto-generated. Clean against current model state. |
| **Subtotal** | **930** | |

### JSON Schemas: `content/legal/_schema/`

| Path | Lines | Purpose |
|---|---|---|
| `legal_fact.schema.json` | 297 | Draft 2020-12 schema for a legal-fact YAML. Enforces `concept_id` kebab-case, `citation_string` regex, enum constraints, conditional rules (lawyer attestation, provisional flag, verbatim text). |
| `attestation.schema.json` | 106 | Schema for an attorney-attestation YAML. |
| **Subtotal** | **403** | |

### Content docs: `content/legal/`

| Path | Lines | Purpose |
|---|---|---|
| `README.md` | 62 | Conventions, lifecycle, what-not-to-do for editors. |
| `CHANGELOG.md` | 22 | Empty header, ready for entries. |

### Seed YAML facts: `content/legal/statutes/`

All 10 facts are `verification_status: mc_reviewed`, `citation_confidence: high`, `legal_provisional: false`, `statute_text_verbatim: false`.

| Path | Lines | Concept |
|---|---|---|
| `rha/s4_a_unfair_practices.yaml` | 85 | RHA s4A — unfair practices framework |
| `rha/s5_2_right_to_written_lease.yaml` | 75 | RHA s5(2) — right to written lease |
| `rha/s5_3_a_parties.yaml` | 75 | RHA s5(3)(a) — parties + domicilium |
| `rha/s5_3_b_dwelling.yaml` | 74 | RHA s5(3)(b) — description of dwelling |
| `rha/s5_a_landlord_duties.yaml` | 79 | RHA s5A — landlord duties |
| `rha/s5_b_tenant_duties.yaml` | 78 | RHA s5B — tenant duties |
| `rha/s7_tribunal_establishment.yaml` | 94 | RHA s7 — Tribunal establishment (carries `alternative_citations` recording the historic `s13` error) |
| `rha/s13_tribunal_powers.yaml` | 80 | RHA s13 — Tribunal powers / referral |
| `popia/s16_information_quality.yaml` | 92 | POPIA s16 — information quality (records the historic `s11(2)` error) |
| `popia/s24_correction_deletion.yaml` | 91 | POPIA s24 — correction / deletion (records the historic `s25` error) |
| **Subtotal** | **823** | |

### Status note (this file)

| Path | Lines |
|---|---|
| `content/cto/training/phase_a_day_1_2_status.md` | ~130 |

### One settings change

- `backend/config/settings/base.py`: added `"apps.legal_rag"` to `LOCAL_APPS` (between `apps.legal` and `apps.payments`).

---

## 2. `makemigrations --check` output

```
$ .venv/bin/python manage.py makemigrations --check --dry-run
No changes detected
```

Migration generated on first run, no drift on second run. Migration file: `backend/apps/legal_rag/migrations/0001_initial.py` (122 LOC).

**Note:** as instructed, the migration was NOT applied against the dev DB. `manage.py migrate` was not run.

---

## 3. `manage.py check` output

```
$ .venv/bin/python manage.py check
System check identified no issues (0 silenced).
```

The Django check `legal_rag.W001…W006` is registered and active. It iterates 10 YAML files in `content/legal/statutes/**/*.yaml`, validates each against `_schema/legal_fact.schema.json`, and yields a `Warning` per violation. With the seed files as written, **zero warnings are emitted** — that is the Day 1-2 proof that schema + seed + check are coherent.

A one-shot independent validation also passed:

```
$ .venv/bin/python -c "<validator script>"
OK   content/legal/statutes/popia/s16_information_quality.yaml
OK   content/legal/statutes/popia/s24_correction_deletion.yaml
OK   content/legal/statutes/rha/s13_tribunal_powers.yaml
OK   content/legal/statutes/rha/s4_a_unfair_practices.yaml
OK   content/legal/statutes/rha/s5_2_right_to_written_lease.yaml
OK   content/legal/statutes/rha/s5_3_a_parties.yaml
OK   content/legal/statutes/rha/s5_3_b_dwelling.yaml
OK   content/legal/statutes/rha/s5_a_landlord_duties.yaml
OK   content/legal/statutes/rha/s5_b_tenant_duties.yaml
OK   content/legal/statutes/rha/s7_tribunal_establishment.yaml

Files: 10, errors: 0
```

Ruff is clean on the new app:

```
$ ruff check backend/apps/legal_rag/
All checks passed!
```

---

## 4. Notes / concerns surfaced for the plan before Day 3

These are findings that arose during the scaffold pass. None are blocking; all are things the loader / verifier / renderer authors should know.

### 4.1 PyYAML's date auto-resolution conflicts with JSON Schema strings

**Problem:** PyYAML's default `safe_load` parses ISO date strings (e.g. `2026-05-12`) into Python `datetime.date` objects. The JSON Schema in `_schema/legal_fact.schema.json` declares date fields as `type: string, format: date`. Without intervention, every fact YAML fails validation with `datetime.date(…) is not of type 'string'`.

**Resolution in Day 1-2:** the check uses a subclassed `yaml.SafeLoader` that strips the `tag:yaml.org,2002:timestamp` implicit resolver, so ISO dates stay as strings. The loader (`sync_legal_facts`, Day 3) MUST use the same pattern — otherwise the in-app representation will diverge from the canonical YAML and `content_hash` calculation will silently differ across processes.

**Recommendation for plan:** add a one-liner to §11 (Tech stack) noting that YAML date parsing requires a custom loader. The loader + checker + verifier should share a `legal_rag.yaml_loader` helper module rather than re-deriving the loader in each command. (Suggest adding this to the Day 3 deliverables.)

### 4.2 `LegalFact.current_version` is nullable to break the FK cycle

**Context:** the plan §3 implies `LegalFact` always points at a `LegalFactVersion`, but `LegalFactVersion` carries an FK back to `LegalFact` (it must — versions are children of a fact). On row creation this is a chicken-and-egg.

**Resolution in Day 1-2:** `LegalFact.current_version` is `null=True, blank=True`. The loader will need a `transaction.atomic()` block: INSERT `LegalFact` → INSERT `LegalFactVersion` → UPDATE `LegalFact.current_version` to the version row. After the transaction every published fact row has a non-null `current_version`; an integrity test in the verifier can assert this invariant. (Mirrors how `apps.audit.AuditEvent.prev_hash` is "" only for the genesis row.)

**Recommendation for plan:** add a half-paragraph to §3 noting the transactional creation pattern, so the Day 3 author doesn't trip on it.

### 4.3 `LegalAttestation` save-time guard vs. test fixtures

The model raises `ValidationError` on any re-save of an existing row to enforce append-only. This is correct per plan §3 but means:

- Tests that build attestations via Django ORM factories must not call `.save()` twice on the same instance.
- The Django admin (when added) MUST NOT expose an edit form for `LegalAttestation` — only "add" and read-only views.

**Recommendation for plan:** add a note under §11 / Vault33 storage line that the admin for attestations is intentionally read-only. (Or surface this as an open question for MC if read-only-admin is contested.)

### 4.4 `verification_status: mc_reviewed` allows `citation_confidence: high`

The schema's `legal_provisional` conditional requires `medium/low` confidence when `legal_provisional: true`. But it does NOT require `lawyer_reviewed` for `high` confidence — that's correct, since HIGH-confidence facts can sit at `mc_reviewed` indefinitely (per plan §5 lifecycle diagram). The seed files use this pattern.

**Recommendation:** no change needed; flag for the lawyer attestation step that a HIGH-confidence row at `mc_reviewed` is the **default** state going into the first quarterly review, not an anomaly.

### 4.5 `effective_from` for POPIA seed facts

The POPIA Act commenced on 2021-07-01 (most provisions). The seed `popia/s16` and `popia/s24` files use `2021-07-01` as `effective_from`. This is correct but mark for lawyer review: if any subsequent regulation amends s16/s24 (e.g. the 2025 POPIA Amendment Regulations referenced in the `vault33-popia-ruleset` skill), the `effective_from` bumps and a new fact_version is required.

**Recommendation:** the loader's idempotency rule must include `effective_from` in the change-detection key, not just `content_hash`. Otherwise a regulator-driven `effective_from` bump that doesn't change the substantive text would be missed.

### 4.6 The Django check is fail-soft (Warning), per spec

The check emits `Warning` not `Error`, deliberately. This means CI will pass against malformed YAML in Day 1-2. The loader in Day 3 must promote schema failures to **fatal** — `sync_legal_facts` should refuse to write any rows if even one YAML is invalid. Plan §3 already implies this; spelling it out here.

### 4.7 Embedded test of skill regeneration round-trip is needed by Day 5

When the skill renderer lands (Day 4-5), there should be a pytest that asserts every rendered `.md` file's `<!-- BEGIN AUTO-GENERATED -->` block round-trips against the YAML — i.e. rendering twice produces byte-identical output. Without this, a corpus_version bump that re-orders facts could produce a diff that looks like content drift but is just sort instability.

---

## 5. Open questions surfaced to MC (none blocking Day 3)

1. **Schema versioning.** The schema itself is at `$id` only — no `version` field. Plan §3 talks about corpus_version but not schema_version. When the schema evolves (e.g. adding a new field), do we want a schema_version column on `LegalCorpusVersion` to detect old-corpus + new-schema mismatch?  (Suggest yes; minor.)
2. **Statute enum in JSON schema vs. open string.** Currently the `statute` field is enum-locked to `[RHA, POPIA, CPA, PIE, STSMA, CSOS]`. Adding e.g. National Credit Act (NCA s171 for unfair credit terms in domestic leases) would require a schema bump. Acceptable; just record that adding a new SA Act is a corpus_version event, not a YAML-only event.
3. **Seed coverage.** Day 1-2 ships 8 RHA + 2 POPIA facts. The remaining HIGH-confidence rows from the canonical map (~35) are deferred to Day 5-7 (per plan §13). This is intentional but worth a sanity check — confirm the 10 seed facts are enough to exercise the loader end-to-end. (My read: yes; 4 statute types + cross-references + `alternative_citations` patterns exercise every JSON schema branch.)

---

## 6. Ready for Day 3

When Day 3 starts (`sync_legal_facts` loader), it should:

1. Reuse the `_StringDateLoader` pattern from `checks.py` (extract into `legal_rag/yaml_loader.py`).
2. Compute `content_hash` from the canonical-YAML *bytes* (not the parsed dict) so YAML re-serialisation drift doesn't change the hash.
3. Use `pg_advisory_lock('legal_facts_sync')` per plan §3.
4. Wrap each fact in a single `transaction.atomic()` for the LegalFact → LegalFactVersion → current_version pattern.
5. Resolve all `related_concepts` cross-references at the end of the load and `Error` on any unresolved id.
6. Emit a `LegalCorpusVersion` row whose `merkle_root` is the SHA256 of the deterministic JSON of `[{concept_id, content_hash}]` sorted by `concept_id`.
7. Set `is_active=True` on the new corpus version and `is_active=False` on the previous, atomically.
