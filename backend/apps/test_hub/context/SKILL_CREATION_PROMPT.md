# Skill Creation Prompt

Use this file with `anthropic-skills:skill-creator` to create the `tremly-testing` skill.
Copy the prompt below into the skill creator agent.

---

## Prompt to give the skill-creator agent:

---

Create a skill called `tremly-testing` for the Tremly Property Manager project.

This skill is the AI agent entry point for all testing work on the Tremly platform —
a 99% AI-created and AI-managed Django 5 + DRF + PostgreSQL application.

## Skill Purpose

Load this skill whenever you are:
- Writing new tests
- Fixing a bug found during manual testing
- Running a test audit
- Re-indexing the test RAG store
- Housekeeping test context or skills registry

---

## What the skill must encode

### 1. RAG-First Protocol
Before writing any test, ALWAYS query the ChromaDB test_context store:
```python
from core.contract_rag import query_test_context
results = query_test_context("what should I test in <module>?", module="<module>")
```
This is the entry point. Never write a test without first checking if it's covered.

### 2. TDD Red-Green-Refactor Workflow

**Markers:**
- `@pytest.mark.red` — test written BEFORE implementation (xfail strict=True enforced by conftest)
- `@pytest.mark.green` — implementation complete, test passes
- `@pytest.mark.refactor` — code under refactor, test must stay green
- `@pytest.mark.unit` — fast, no DB, isolated
- `@pytest.mark.integration` — uses DB + API client
- `@pytest.mark.e2e` — hits external services (DocuSeal, Gotenberg, Firebase)

**Cycle:**
1. Query RAG → confirm not covered
2. Write `@pytest.mark.red` test
3. Run `pytest -m red apps/test_hub/<module>/` → confirm xfail
4. Implement the fix/feature
5. Change to `@pytest.mark.green`
6. Run `pytest -m green apps/test_hub/<module>/` → confirm pass

### 3. Manual Bug Workflow (Red Before Fix)

When a manual test session finds an issue:
1. **Audit** — `pytest --co -q | grep -i <keyword>` + check existing test files
2. **Document** — create `apps/test_hub/issues/<module>/<YYYY-MM-DD>_<slug>.md`
3. **Red test** — write failing test, confirm it xfails
4. **Fix** — minimum code change
5. **User confirms** — manual verification
6. **Green** — change marker, run tests, update issue .md to FIXED
7. **Re-index RAG** — `python manage.py ingest_test_context --module <module>`

Issue file template:
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

### 4. Test Structure

```
backend/apps/test_hub/
├── base/test_case.py          # TremlyAPITestCase — all factory methods
├── context/                   # AI-readable docs (vectorised into RAG)
│   ├── README.md              # RAG entry point instructions
│   ├── architecture.md
│   ├── tdd_workflow.md
│   ├── bug_workflow.md
│   ├── conventions.md
│   └── modules/<module>.md    # Per-module domain context
├── issues/<module>/           # Bug history (also vectorised)
├── <module>/
│   ├── conftest.py            # Module-specific fixtures
│   ├── unit/                  # Fast isolated tests (no DB)
│   └── integration/           # API-level tests (DB + client)
```

Two tiers per module:
- `unit/` — test models, serializers, permissions, utils, signals in isolation
- `integration/` — test API endpoints with the full Django stack

### 5. Factory Methods (TremlyAPITestCase)

All test classes inherit from `TremlyAPITestCase` or use the `tremly` pytest fixture.

```python
from apps.test_hub.base.test_case import TremlyAPITestCase

# User factories
create_admin()
create_agent()
create_tenant()
create_supplier_user()
create_owner_user()

# Data factories
create_person(user=None, **kwargs)
create_property(agent=None, **kwargs)
create_unit(property_obj=None, **kwargs)
create_lease(unit=None, tenant=None, **kwargs)
create_maintenance_request(unit=None, tenant=None, **kwargs)

# Auth helpers
authenticate(user)         # force-authenticate the test client
get_tokens(user)           # return {access, refresh} JWT tokens
```

### 6. Pytest Commands

```bash
cd backend

# By TDD phase
pytest -m red                          # All pending (xfail)
pytest -m green                        # All passing
pytest -m unit                         # Fast unit tests only
pytest -m integration                  # API-level tests

# By module
pytest apps/test_hub/accounts/
pytest apps/test_hub/leases/
pytest apps/test_hub/maintenance/

# TDD cycle report
python manage.py run_tdd --cycle
python manage.py run_tdd --module leases

# Coverage
pytest --cov=apps --cov-report=term-missing

# Deduplication check
pytest --co -q | grep -i <keyword>
```

### 7. Deduplication Rules

Before creating any test:
1. Query RAG: `query_test_context("<scenario>", module="<module>")`
2. Run: `pytest --co -q | grep -i <keyword>`
3. Scan: `grep -r "def test_" apps/test_hub/<module>/`
4. If similar test exists: **extend it** with a new method or parametrize case
5. Never replace an existing test — add to it

### 8. RAG Housekeeping

After any of these events, re-index:
```bash
python manage.py ingest_test_context --reset       # Full rebuild
python manage.py ingest_test_context --module <m>  # Single module update
```

**Re-index triggers:**
- New feature shipped → update `context/modules/<module>.md` Coverage Gaps section
- Bug fixed → update issue .md Status to FIXED
- New module added → create context file + run ingest
- TDD conventions change → update `context/conventions.md` + re-ingest

### 9. Module Context File Structure

Each `context/modules/<module>.md` must have these sections:
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

Keep the **Current Coverage** and **Coverage Gaps** sections up to date.
This is what the RAG returns when an agent asks "what should I test?".

### 10. Skills Registry Housekeeping

The `apps/ai/utils/skills_registry.py` (or similar) defines available AI tools.
When new maintenance skills are added or removed:
1. Update the skills registry file
2. Run: `python manage.py seed_skills` to sync DB
3. Re-vectorize: `python manage.py vectorize_issues --reset` if needed
4. Update `context/modules/ai.md` with the new skills list
5. Re-index RAG: `python manage.py ingest_test_context --module ai`

---

## Modules covered by test_hub

| Module | Domain |
|--------|--------|
| accounts | Auth, JWT, OTP, OAuth, roles (admin/agent/tenant/supplier/owner), POPIA |
| properties | Properties, units, landlords, banking, ownership |
| leases | Lease agreements, TipTap templates, AI builder, reusable clauses, RHA |
| maintenance | Requests, suppliers, dispatch, quotes, AI agent assist, matching algo |
| esigning | DocuSeal integration, Gotenberg PDF, audit trail, public links |
| ai | Claude integration, lease parsing, tenant intelligence, skills registry |
| tenant_portal | Tenant AI chat, maintenance ticket creation, heuristics, throttles |
| notifications | Firebase push, email (no coverage yet — priority gap) |

---

## SA Context Reminders

- POPIA: South African data privacy — test that personal data is not leaked across tenant/owner/agent boundaries
- RHA: Rental Housing Act — lease tests must cover mandatory clause validation
- ZAR: All monetary amounts in South African Rand
- Test accounts use @tremly.co.za or @test.com email domains
