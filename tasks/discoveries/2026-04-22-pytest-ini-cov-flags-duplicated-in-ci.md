---
discovered_by: rentals-reviewer
discovered_during: QA-001
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: QA
---

## What I found
`backend/pytest.ini` `addopts` already includes `--cov=apps --cov-report=term-missing --cov-report=html:htmlcov`. The CI `pytest` step in `.github/workflows/ci.yml` also passes `--cov=apps --cov-report=term-missing --cov-report=html:htmlcov --cov-report=xml:coverage.xml` on the command line. pytest-cov merges duplicate flags silently, so CI still works, but the configuration is split across two files making it harder to reason about what options are active in each environment.

## Why it matters
If someone removes the CI flags expecting `pytest.ini` to cover them, the XML report (only in CI) disappears. Conversely if someone removes the `pytest.ini` flags expecting CI to cover them, local runs lose HTML output. The split is a maintenance trap.

## Where I saw it
- `backend/pytest.ini:7` — addopts contains `--cov=apps --cov-report=term-missing --cov-report=html:htmlcov`
- `.github/workflows/ci.yml:84-89` — pytest step repeats the same flags and adds `--cov-report=xml:coverage.xml`

## Suggested acceptance criteria (rough)
- [ ] Move all coverage flags into `pytest.ini` `addopts` (including `--cov-report=xml:coverage.xml`) so a single source of truth governs all environments
- [ ] CI step becomes plain `pytest --tb=short -q` with no `--cov` flags

## Why I didn't fix it in the current task
Out of scope — QA-001 is about test coverage, not CI config housekeeping. Also requires confirming whether XML should always be generated locally or CI-only.
