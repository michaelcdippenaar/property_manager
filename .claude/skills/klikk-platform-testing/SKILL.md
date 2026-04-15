---
name: klikk-platform-testing
description: >
  AI agent protocol for all testing work on the Tremly Property Manager platform.
  Load this skill whenever you are: writing new tests, adding test coverage, fixing a
  bug found during manual or automated testing, running a test audit, re-indexing the
  test RAG store, or doing skills registry housekeeping. Trigger on any mention of
  pytest, test_hub, TDD, red/green markers, ChromaDB test context, or test coverage
  for any Tremly module (accounts, leases, maintenance, esigning, properties, ai,
  tenant_portal, notifications). Also trigger when the user says "write a test",
  "cover this", "add coverage", "this is broken", "bug fix", or "update the test
  context". When in doubt, load this skill — it is the single source of truth for
  everything testing-related on this platform.
---

# Tremly Testing Protocol

**Test location:** `backend/apps/test_hub/`
**Base class:** `TremlyAPITestCase` (all factories) or `tremly` pytest fixture
**RAG store:** ChromaDB test context — always query before writing any test

---

## TDD Red-Green-Refactor Cycle

### Markers

| Marker | Meaning | Enforcement |
|--------|---------|-------------|
| `@pytest.mark.red` | Written before implementation | `xfail(strict=True)` — must fail |
| `@pytest.mark.green` | Implementation complete | Must pass |
| `@pytest.mark.refactor` | Code under refactor | Must stay green |
| `@pytest.mark.unit` | No DB, fast, isolated | — |
| `@pytest.mark.integration` | DB + API client | — |
| `@pytest.mark.e2e` | Hits Gotenberg/Firebase | — |

### 6-Step Cycle

```
1. Query RAG           → confirm scenario not covered
2. Write red test      → @pytest.mark.red (xfail strict=True)
3. Confirm xfail       → cd backend && pytest -m red apps/test_hub/<module>/
4. Implement fix       → minimum code change to make it pass
5. Flip to green       → @pytest.mark.green
6. Confirm pass        → cd backend && pytest -m green apps/test_hub/<module>/
```

### Bug Workflow

```
1. Audit     → pytest --co -q | grep -i <keyword>
2. Document  → create apps/test_hub/issues/<module>/YYYY-MM-DD_<slug>.md
3. Red test  → write failing test, confirm xfail
4. Fix       → minimum code change
5. User confirms → manual verification before marking green
6. Green     → change marker, run tests
7. Re-index  → python manage.py ingest_test_context --module <module>
```

---

## Reference Index

| Topic | File |
|-------|------|
| RAG query API, deduplication checklist, RAG housekeeping, skills registry | [rag-protocol.md](references/rag-protocol.md) |
| Directory layout, factory methods, pytest commands | [test-structure.md](references/test-structure.md) |
| Module registry, SA context rules, issue file template | [modules.md](references/modules.md) |
