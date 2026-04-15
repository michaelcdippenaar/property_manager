# RAG Protocol & Housekeeping

---

## RAG-First — Always Before Writing Any Test

Query the test context RAG store before touching any test file:

```python
# Run inside Django shell or management command
from core.contract_rag import query_test_context

results = query_test_context("what should I test in <module>?", module="<module>")
for r in results:
    print(r["text"], "\n---")
```

`query_test_context(query, module=None, n_results=5)` returns:
`{ text, module, doc_type, source, distance }`

**Why:** The RAG store holds conventions, coverage gaps, known edge cases, and past bug history. Skipping this risks duplicating tests or missing critical invariants.

---

## Deduplication Checklist

Before creating any new test:

1. **RAG query** — `query_test_context("<scenario>", module="<module>")`
2. **Collection check** — `cd backend && pytest --co -q | grep -i <keyword>`
3. **Source scan** — `grep -r "def test_" apps/test_hub/<module>/`
4. **Decision:**
   - Similar test exists → **extend** it (add a method or parametrize)
   - No match found → create a new test
   - Never replace an existing test — always add to it

---

## RAG Housekeeping

Re-index the ChromaDB test context after any of these events:

| Trigger | Command |
|---------|---------|
| New feature shipped | `python manage.py ingest_test_context --module <module>` |
| Bug fixed | Update issue .md to FIXED, then re-index module |
| New module added | Create `context/modules/<module>.md` + full ingest |
| Conventions changed | Update `context/conventions.md` + `--reset` |
| Full rebuild | `python manage.py ingest_test_context --reset` |

### Module context file structure

Each `context/modules/<module>.md` must have:

```markdown
# Module: <Name>
## Domain Responsibilities
## Key Models
## External Dependencies (and how to mock them)
## Business Invariants (things tests must enforce)
## Current Coverage
## Coverage Gaps (things not yet tested)
## Known Edge Cases
```

Keep **Current Coverage** and **Coverage Gaps** up to date — this is what the RAG returns when asked "what should I test?".

---

## Skills Registry Housekeeping

When maintenance skills are added, removed, or renamed:

```bash
# 1. Update the registry file
#    → backend/apps/ai/skills_registry.py

# 2. Sync to DB
python manage.py seed_skills

# 3. Re-vectorize maintenance issues (if symptom phrases changed)
python manage.py vectorize_issues --reset

# 4. Update the AI module context
#    → backend/apps/test_hub/context/modules/ai.md  (skills list section)

# 5. Re-index RAG
python manage.py ingest_test_context --module ai
```
