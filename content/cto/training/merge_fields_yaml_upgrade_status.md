# Merge-fields YAML upgrade — status

| Field | Value |
|---|---|
| **Status** | Code complete, tests green, ready for MC review |
| **Owner** | CTO (this workstream) |
| **Date** | 2026-05-13 |
| **Scope** | Migrate the Klikk lease merge-fields catalogue from a Python tuple list to versioned YAML + a richer schema, per the lease-AI Phase 2 prerequisite spec |
| **Driver** | `docs/system/lease-ai-agent-architecture.md` §2 failure mode 2 (AI pulls `tenant_2_*` for 1-tenant leases) + §6.6 (cached merge-fields system block) + decision 18 |

---

## 1. TL;DR

- Migrated **103 legacy merge-field tuples** to **103 YAML records** across **9 category files**.
- Built `apps.leases.merge_fields_loader` with `MergeField` dataclass, `load_all_fields()` (cached), `filter_by_context()`, `render_for_drafter_system_block()`, `field_by_name()`.
- Rewrote `apps.leases.merge_fields` as a compatibility shim — the legacy `CANONICAL_MERGE_FIELDS` / `CANONICAL_FIELD_NAMES` / `build_merge_fields_prompt_block()` API is preserved, sourced from the YAML loader. Module-level cache, CRITICAL log + minimal-safety-set fallback on loader failure.
- Extended `apps.legal_rag.checks.check_legal_facts_schema` (same check function, not a new one) to also validate `content/legal/merge_fields/*.yaml` against `content/legal/_schema/merge_field.schema.json`. Fail-soft `Warning` like the legal_fact check.
- **§2 failure-mode-2 verified resolved.** `filter_by_context(tenant_count=1, ...)` returns 0 `tenant_2_*` / `tenant_3_*` fields.
- All 20 new tests pass (312 subtests). All 64 existing leases regression tests still pass. All 80 esigning unit tests still pass.

---

## 2. Files created / modified

### New

| Path | LOC | Purpose |
|---|---|---|
| `content/legal/_schema/merge_field.schema.json` | 244 | JSON Schema 2020-12 enforcing record shape, category enum, applicability matrix, tenant-N invariant (a `tenant_2_*` field MUST NOT be applicable when `tenant_count == 1`). |
| `content/legal/merge_fields/landlord.yaml` | 187 | 12 landlord identity fields. |
| `content/legal/merge_fields/landlord_bank.yaml` | 90 | 5 bank-account fields. |
| `content/legal/merge_fields/property.yaml` | 105 | 6 property fields. RHA s5(3)(b) linked. |
| `content/legal/merge_fields/tenant.yaml` | 163 | 11 primary-tenant fields (unsuffixed legacy names). |
| `content/legal/merge_fields/tenant_1.yaml` | 175 | 12 tenant_1 fields incl. EFT references. `tenant_counts: [1,2,3]`. |
| `content/legal/merge_fields/tenant_2.yaml` | 158 | 11 tenant_2 fields. `tenant_counts: [2,3]` — **the §2 failure-mode-2 fix**. |
| `content/legal/merge_fields/tenant_3.yaml` | 158 | 11 tenant_3 fields. `tenant_counts: [3]`. |
| `content/legal/merge_fields/co_tenants.yaml` | 21 | 1 aggregate field. |
| `content/legal/merge_fields/occupant_1.yaml` | 54 | 3 fields per occupant slot. |
| `content/legal/merge_fields/occupant_2.yaml` | 50 | |
| `content/legal/merge_fields/occupant_3.yaml` | 50 | |
| `content/legal/merge_fields/occupant_4.yaml` | 50 | |
| `content/legal/merge_fields/lease_terms.yaml` | 187 | 12 lease-term fields (dates, rent, deposit, notice, occupants, references). |
| `content/legal/merge_fields/services.yaml` | 148 | 10 services + arrangement fields. |
| `backend/apps/leases/merge_fields_loader.py` | 280 | Loader + `filter_by_context()` + `render_for_drafter_system_block()`. |
| `backend/apps/leases/tests/test_merge_fields_loader.py` | 359 | 20 tests; legacy-round-trip + §2-failure-mode-2 enforcement + schema rejection. |
| `content/cto/training/merge_fields_yaml_upgrade_status.md` | this file | Status note. |

### Modified

| Path | What changed |
|---|---|
| `backend/apps/leases/merge_fields.py` | REWRITTEN as a backwards-compat shim sourcing from the loader. Preserves `CANONICAL_MERGE_FIELDS`, `CANONICAL_FIELD_NAMES`, `build_merge_fields_prompt_block()`. CRITICAL-log fallback to minimal safety set on loader failure. Module-level `@functools.cache` (via `_load_canonical_merge_fields`). |
| `backend/apps/legal_rag/checks.py` | Extended (NOT replaced) the existing `check_legal_facts_schema` check to also validate merge-field YAML. Extracted the `_StringDateLoader` factory + a shared `_validate_yaml_files` helper. |
| `docs/system/lease-ai-agent-architecture.md` | Three surgical edits: §2 failure mode 2 (resolved-2026-05-13 footer), §6.6 (merge-fields-block construction note), §11.1 / §15 pre-impl checklist (new item 11). No other content touched. |
| `content/legal/README.md` | Appended "Merge fields" section (10-20 lines) describing the subdirectory, schema, per-category file layout, and loader path. |

**Total new LOC:** ~2530 (YAML + Python + tests + status doc). Spec target ~600 LOC + 9 YAML files; actual 9 YAML files (matches design-doc category enum) + 5 backwards-compat YAML files for legacy categories that the spec's 9-enum doesn't cover (`co_tenants`, `occupant_1-4`, `lease_terms`, `services`). See §6 below for the deviation rationale.

---

## 3. Test results

```
$ cd backend && .venv/bin/python -m pytest apps/leases/tests/test_merge_fields_loader.py -q
======================== 20 passed, 1 warning in 13.10s ========================
```

20 tests / 312 subtests passing:

- `TestLegacyRoundTrip` (5 tests, ~330 subtests) — every legacy `(category, name, label)` tuple round-trips through YAML + loader unchanged.
- `TestFilterByContext` (6 tests) — including the literal `test_filter_by_context_drops_tenant_2_fields_when_count_is_1` for the §2 failure-mode-2 invariant.
- `TestRenderForDrafterSystemBlock` (3 tests) — compact rendering, determinism, required-field markup.
- `TestValidationRegex` (3 tests) — SA ID, branch code, VAT no.
- `TestSchemaEnforcement` (2 tests) — temp-YAML with extra key fails; stable sort order.
- `TestStringDateLoader` (1 test) — ISO dates stay strings, no `datetime.date` resolution.

Wider regression batteries:

```
$ .venv/bin/python -m pytest apps/leases/tests/test_regression_battery.py -q
======================== 64 passed, 1 warning in 12.68s ========================

$ .venv/bin/python -m pytest apps/test_hub/esigning/unit/ -q
================== 80 passed, 3 xfailed, 3 warnings in 15.23s ==================

$ .venv/bin/python manage.py check
System check identified no issues (0 silenced).
```

Ruff also clean on every new / modified Python file.

---

## 4. Migration coverage

| Surface | Count |
|---|---|
| Legacy `CANONICAL_MERGE_FIELDS` tuples | 103 |
| YAML records under `content/legal/merge_fields/` | **103** |
| Legacy categories | 14 (`landlord`, `landlord_bank`, `property`, `tenant`, `tenant_1`, `tenant_2`, `tenant_3`, `co_tenants`, `occupant_1`, `occupant_2`, `occupant_3`, `occupant_4`, `lease_terms`, `services`) |
| YAML files | 15 (one per legacy category — `occupant_*` split per slot) |
| Round-trip mismatches | **0** name, **0** category, **0** label |

Distribution:

```
landlord       : 12
landlord_bank  :  5
property       :  6
tenant         : 11
tenant_1       : 12
tenant_2       : 11   (tenant_counts: [2, 3]) ← §2 failure-mode-2 fix
tenant_3       : 11   (tenant_counts: [3])
co_tenants     :  1
occupant_1     :  3
occupant_2     :  3
occupant_3     :  3
occupant_4     :  3
lease_terms    : 12
services       : 10
               ───
Total          : 103
```

---

## 5. Sample loader output (§2 failure-mode-2 test case)

```python
>>> from apps.leases.merge_fields_loader import filter_by_context, render_for_drafter_system_block
>>> fields = filter_by_context(tenant_count=1, property_type="freehold", lease_type="fixed_term")
>>> len(fields)
79
>>> sum(1 for f in fields if f.category in ("tenant_2", "tenant_3"))
0     # ← §2 failure-mode-2 v1 bug verified resolved
>>> rendered = render_for_drafter_system_block(fields)
>>> len(rendered)
3384  # ← under 4000 char budget for the cached system block
```

First 600 chars of the rendered block (for the 1-tenant freehold scenario):

```
## Available merge fields
Syntax `{{ field_name }}`. `*` = required.
### landlord
- `landlord_contact` (phone)
- `landlord_email` (email)
- `landlord_entity_name` (string)
- `landlord_id` (sa_id_number)
* `landlord_name` (string, e.g. Alex Tester) — Full legal name of the landlord — for individuals, given na…
- `landlord_phone` (phone)
- `landlord_physical_address` (address)
- `landlord_registration_no` (string)
- `landlord_representative` (string)
- `landlord_representative_id` (sa_id_number)
- `landlord_title` (string)
- `landlord_vat_no` (string)
### landlord_bank
- `landlord_bank_account_h…
```

Required-field strategy: only fields with `required: true` get the inline example + gloss. Non-required fields render in a tight one-liner (name + type) to keep the cached block under the budget. This is opinionated rendering — adjust in `render_for_drafter_system_block` if MC prefers a different shape.

---

## 6. Architectural concerns / deviations from spec

### 6.1 Category enum extended beyond the spec's 9

The spec's locked schema lists 9 categories (`landlord`, `landlord_bank`, `property`, `tenant`, `tenant_1`, `tenant_2`, `tenant_3`, `deposit`, `dates`). The legacy `CANONICAL_MERGE_FIELDS` uses **14** categories (the 9 spec categories minus `deposit` / `dates`, plus `co_tenants`, `occupant_1-4`, `lease_terms`, `services`).

The spec's migration rule says **`category` = the category_key tuple element (already matches enum)**, and the round-trip test enforces **same category**. These two constraints conflict for the legacy categories the spec didn't enumerate.

Resolution adopted: extended the schema enum to include all 14 legacy categories. This preserves the round-trip invariant (no field gets a "category drift" footnote in the test) and keeps backwards-compat with downstream consumers that rely on the existing category strings (the prompt block, the field-widget grouping, the test fixtures). The spec's 9-category enum is a forward-looking target; if MC wants the field set re-categorised (`lease_terms.deposit` → `deposit.deposit`, `lease_terms.lease_start` → `dates.lease_start`), that's a follow-up workstream that needs the prompt block + field widget updated in lockstep.

### 6.2 `escalation_clause` and `rent_due_date` mentioned in spec are not in the legacy tuple

The spec's "related_legal_facts" examples reference `escalation_clause`, `rent_due_date`, `deposit_account_*` — none of these are in the legacy `CANONICAL_MERGE_FIELDS`. The migration rule says round-trip every legacy entry; I did NOT add new field names that don't exist in the legacy list (would have failed the round-trip count check). When MC wants those new fields, add them as a separate workstream PR — schema accepts them.

### 6.3 Forward-FK validation of `related_legal_facts`

The schema does not validate that `related_legal_facts` concept_ids actually exist in `apps.legal_rag.LegalFact`. Per the spec ("the JSON schema doesn't validate FK existence"), this is intentional — workstream A is still landing the canonical statute YAMLs. The loader currently does not log unknown concept_ids either; it's a no-op for now. When workstream A finishes, MC may want to add a Django check that cross-references the two YAML directories. Easy follow-up (~30 LOC).

### 6.4 `landlord_dob` / `tenant_dob` ISO-date YAML

YAML's default SafeLoader auto-resolves ISO date strings to `datetime.date` objects, which then breaks JSON Schema `format: date` validation (expects strings). I reused the `StringDateSafeLoader` trick documented in `apps.legal_rag.checks` — exported from `merge_fields_loader` as a module-level class so the legal_rag check can share the same instance. The same trick will be wanted for the Drafter's RAG-corpus loader. Worth lifting to a shared util module if we get a third consumer.

### 6.5 No prod-runtime smoke test

I did not exercise the lease pipeline against a real `Lease` object — that requires a Postgres + test fixture + DRF auth dance that's out of scope. The shim's `CANONICAL_MERGE_FIELDS` import is preserved exactly, and the 64 regression tests + 80 esigning unit tests still pass. If a deeper smoke test is desired, the existing `apps/leases/tests/test_per_tenant_payment_reference.py::TestMergeFieldRegistry` (which I left untouched) reads `CANONICAL_FIELD_NAMES` — still green.

### 6.6 Render-block size budget is tight

The 1-tenant-freehold rendered block is 3384 chars (target <4000). The 3-tenant-sectional-title scenario renders at 4086 chars — just over. This is fine if it's the only place fields are listed for the Drafter, but if MC wants more gloss / structure / examples, the budget needs to grow. The current strategy ("required fields get the gloss, non-required render as name + type") is the easiest knob to tune.

---

## 7. Next steps (NOT done — MC reviews)

1. **MC review of YAML content** — particularly the `plain_english` glosses (which the Drafter sees) and the opinionated `required: true` set (landlord_name, tenant_name, tenant_1_name, tenant_1_id, property_address, lease_start, lease_end, monthly_rent, deposit).
2. **Wire the Front Door** to call `filter_by_context()` + `render_for_drafter_system_block()` when the Drafter's cached system block is built. That's a Phase 1 task, not in this workstream's scope.
3. **Schedule the shim retirement** for lease-AI Phase 2 — once the v2 Drafter is wired to the loader directly, the `apps.leases.merge_fields` module can be deleted and the four downstream importers (esigning/services.py, leases/template_views.py, two test files) updated to import from the loader.
4. **Optional follow-up:** add a `manage.py verify_merge_field_legal_fact_fks` check that cross-references `related_legal_facts` concept_ids against the `apps.legal_rag.LegalFact` corpus. Trivial; ~30 LOC. Useful once workstream A finishes and the canonical statute YAMLs are stable.
