# test_hub Context Directory

These files are the **single source of truth for test intelligence**.
They are vectorised into the ChromaDB `test_context` collection and queried by AI agents
before writing any test.

---

## RAG-First Workflow (Entry Point)

Before writing or modifying any test, an AI agent MUST query the RAG store:

```python
from core.contract_rag import query_test_context

# What should I test in this module?
results = query_test_context("what should I test in the leases module?", module="leases")

# Is this scenario already covered?
results = query_test_context("date validation end before start lease", module="leases")

# What are the business rules I must not break?
results = query_test_context("RHA compliance invariants leases")
```

This ensures no duplicate tests, coverage aligns with known business rules, and bug history is respected.

## Re-indexing the RAG Store

Run whenever context files change:

```bash
python manage.py ingest_test_context --reset       # Full re-index
python manage.py ingest_test_context --module leases  # Single module
python manage.py ingest_test_context --dry-run     # Preview
```

**Re-index when:** a feature ships, a bug is documented, a module is added, conventions change.

---

## How to use this as an AI agent

1. Query the RAG store (see above) — check existing coverage
2. Read `tdd_workflow.md` — understand the Red-Green-Refactor rules
3. Read `bug_workflow.md` — if fixing a manual issue
4. Read `conventions.md` — naming and factory patterns
5. Read `modules/<module>.md` — domain context before writing tests
6. Write a `@pytest.mark.red` test first, confirm it xfails
7. Implement the feature / fix
8. Change marker to `@pytest.mark.green`, confirm it passes

## Files

| File | Purpose |
|------|---------|
| architecture.md | System-wide technical architecture |
| tdd_workflow.md | Red-Green-Refactor rules and examples |
| conventions.md | Test naming, factory usage, mock patterns |
| modules/accounts.md | Auth, roles, permissions domain context |
| modules/properties.md | Properties, units, landlords domain context |
| modules/leases.md | Leases, templates, builder domain context |
| modules/maintenance.md | Maintenance, suppliers, AI agent domain context |
| modules/esigning.md | E-signing, DocuSeal, PDF domain context |
| modules/ai.md | AI parsing, tenant intelligence domain context |
| modules/tenant_portal.md | Tenant chat, heuristics domain context |
| modules/notifications.md | Push + email notifications context |
