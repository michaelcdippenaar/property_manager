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

## When to load this skill

- Writing or extending any test in `backend/apps/test_hub/`
- Fixing a bug (red-before-fix is mandatory)
- Auditing coverage for a module
- Re-indexing the ChromaDB test context RAG store
- Skills registry housekeeping (seed_skills, vectorize_issues)

---

## 1. RAG-First Protocol — Always Do This Before Writing Any Test

Query the test context RAG store before touching any test file:

```python
# Run this inside a Django shell or inline in a management command
from core.contract_rag import query_test_context

results = query_test_context("what should I test in <module>?", module="<module>")
for r in results:
    print(r["text"], "\n---")
```

`query_test_context(query, module=None, n_results=5)` returns a list of dicts:
`{ text, module, doc_type, source, distance }`

**Why:** The RAG store holds conventions, coverage gaps, known edge cases, and past bug history. Skipping this step risks duplicating existing tests or missing critical invariants.

---

## 2. Deduplication Checklist

Before creating any new test, verify it does not exist:

1. **RAG query** — `query_test_context("<scenario>", module="<module>")`
2. **Collection check** — `cd backend && pytest --co -q | grep -i <keyword>`
3. **Source scan** — `grep -r "def test_" apps/test_hub/<module>/`
4. **Decision:**
   - Similar test exists → **extend** it (add a method or parametrize)
   - No match found → create a new test
   - Never replace an existing test — always add to it

---

## 3. TDD Red-Green-Refactor Cycle

### Markers

| Marker | Meaning | conftest enforcement |
|--------|---------|----------------------|
| `@pytest.mark.red` | Written before implementation | `xfail(strict=True)` — must fail |
| `@pytest.mark.green` | Implementation complete | Must pass |
| `@pytest.mark.refactor` | Code under refactor | Must stay green |
| `@pytest.mark.unit` | No DB, fast, isolated | — |
| `@pytest.mark.integration` | DB + API client | — |
| `@pytest.mark.e2e` | Hits DocuSeal/Gotenberg/Firebase | — |

### 6-Step Cycle

```
1. Query RAG           → confirm scenario not covered
2. Write red test      → @pytest.mark.red (xfail strict=True)
3. Confirm xfail       → cd backend && pytest -m red apps/test_hub/<module>/
4. Implement fix       → minimum code change to make it pass
5. Flip to green       → @pytest.mark.green
6. Confirm pass        → cd backend && pytest -m green apps/test_hub/<module>/
```

The conftest.py root hook automatically injects `xfail(strict=True)` on all `red` tests — if a red test unexpectedly passes, the suite fails. This enforces real test-first discipline.

---

## 4. Manual Bug Workflow

When a manual test session (or production observation) finds an issue:

```
1. Audit     → pytest --co -q | grep -i <keyword>  (confirm no existing test)
2. Document  → create apps/test_hub/issues/<module>/YYYY-MM-DD_<slug>.md
3. Red test  → write failing test, confirm xfail
4. Fix       → minimum code change
5. User confirms → manual verification before marking green
6. Green     → change marker, run tests
7. Re-index  → python manage.py ingest_test_context --module <module>
```

### Issue file template

```markdown
# Issue: <title>
**Module:** <module>
**Status:** RED | FIXED
**Discovered:** <date> (manual testing)
**Test file:** apps/test_hub/<module>/<tier>/test_<file>.py::<Class>::<method>

## Description
## Reproduction Steps
## Root Cause
## Fix Applied
## Test Coverage
- New test: `<path>`
- Duplicate check: confirmed NOT covered — checked: <list>
## Status History
```

Save to: `backend/apps/test_hub/issues/<module>/YYYY-MM-DD_<slug>.md`

---

## 5. Test Structure

```
backend/apps/test_hub/
├── base/
│   └── test_case.py          ← TremlyAPITestCase — all factory methods live here
├── context/                  ← AI-readable markdown (vectorised into ChromaDB)
│   ├── README.md
│   ├── architecture.md
│   ├── tdd_workflow.md
│   ├── bug_workflow.md
│   ├── conventions.md
│   └── modules/<module>.md   ← per-module domain context + coverage gaps
├── issues/<module>/          ← Bug history (also vectorised)
└── <module>/
    ├── conftest.py            ← module-specific fixtures
    ├── unit/                  ← no DB, fast, isolated
    └── integration/           ← full Django stack + API client
```

**Two tiers per module:**
- `unit/` — models, serializers, permissions, utils, signals in isolation
- `integration/` — API endpoints via DRF test client with real DB

All test classes inherit from `TremlyAPITestCase` or use the `tremly` pytest fixture.

---

## 6. Factory Methods

```python
from apps.test_hub.base.test_case import TremlyAPITestCase

class TestFoo(TremlyAPITestCase):
    # User factories
    user   = self.create_user(email=..., role=...)
    admin  = self.create_admin()
    agent  = self.create_agent()
    tenant = self.create_tenant()
    sup    = self.create_supplier_user()
    owner  = self.create_owner_user()

    # Data factories
    person   = self.create_person(full_name="Jane Doe", linked_user=user)
    prop     = self.create_property(agent=agent)
    unit     = self.create_unit(property_obj=prop)
    lease    = self.create_lease(unit=unit, primary_tenant=tenant)
    request  = self.create_maintenance_request(unit=unit, tenant=tenant)
    supplier = self.create_supplier()

    # Auth helpers
    self.authenticate(user)          # force-auth the test client
    tokens = self.get_tokens(user)   # returns {access, refresh}
```

**Pytest fixture equivalent** (`conftest.py` provides `tremly`):

```python
def test_something(tremly):
    agent  = tremly.create_agent()
    tenant = tremly.create_tenant()
    tremly.authenticate(agent)
    ...
```

---

## 7. Pytest Commands

```bash
cd backend

# By TDD phase
pytest -m red                                # All pending (must xfail)
pytest -m green                              # All passing
pytest -m unit                               # Fast unit tests only
pytest -m integration                        # API-level tests

# By module
pytest apps/test_hub/accounts/
pytest apps/test_hub/leases/
pytest apps/test_hub/maintenance/
pytest apps/test_hub/esigning/
pytest apps/test_hub/properties/
pytest apps/test_hub/ai/
pytest apps/test_hub/tenant_portal/

# TDD cycle report
python manage.py run_tdd --cycle
python manage.py run_tdd --module leases

# Coverage
pytest --cov=apps --cov-report=term-missing

# Deduplication check
pytest --co -q | grep -i <keyword>
```

---

## 8. RAG Housekeeping

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

## 9. Skills Registry Housekeeping

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

---

## 10. Modules

| Module | Domain |
|--------|--------|
| `accounts` | Auth, JWT, OTP, OAuth, roles, POPIA |
| `properties` | Properties, units, landlords, banking, ownership |
| `leases` | Lease agreements, TipTap templates, AI builder, clauses, RHA |
| `maintenance` | Requests, suppliers, dispatch, quotes, AI agent, matching algo |
| `esigning` | DocuSeal integration, Gotenberg PDF, audit trail, public links |
| `ai` | Claude integration, lease parsing, tenant intelligence, skills registry |
| `tenant_portal` | Tenant AI chat, maintenance ticket creation, heuristics, throttles |
| `notifications` | Firebase push, email — **priority coverage gap** |

---

## 11. SA Context

- **POPIA** — personal data must not leak across tenant/owner/agent boundaries; test this explicitly
- **RHA** — Rental Housing Act; lease tests must cover mandatory clause validation and 20-business-day notice
- **ZAR** — all monetary amounts in South African Rand
- **Email domains** — use `@tremly.co.za` or `@test.com` in test accounts
- **SA ID numbers** — use valid 13-digit SA ID format in identity tests
