---
name: klikk-leases-test-battery
description: >
  Run the full lease and e-signing integration test battery via the tremly-e2e MCP server.
  Trigger for: "run tests", "run test battery", "run lease tests", "test the lease system",
  "check if signing works", "run integration tests", "leases-test-battery", "test everything",
  "run full tests", "test e-signing", "test templates", "test PDF", "test clauses", or any
  request to verify that the lease signing pipeline, templates, merge fields, clauses, PDF
  generation, or builder flows are working correctly. Even partial requests like "test the
  PDF pipeline" or "check merge fields" should trigger this skill — run the relevant subset.
---

# Lease Test Battery

11 tests across 4 groups covering the full lease + e-signing stack via the tremly-e2e MCP server.

## Pre-flight

```
auth_status → if not authenticated → auth_login
```

## Test Groups

| Group | Tests | Dependencies |
|-------|-------|--------------|
| A: Foundation | 1. Health Check, 2. Merge Field Audit, 3. TipTap Roundtrip | None |
| B: CRUD | 4. Clause CRUD, 5. Lease CRUD | None |
| C: E-Signing | 6. Native Signing E2E, 7. Form Submit E2E, 8. PDF Generation, 9. PDF Layout Compare | Active lease from Group B or create temp |
| D: Builder | 10. Builder Session, 11. Clause AI Generation | None |

Group C depends on an active lease. Run Group A first. Groups A, B, D can run in parallel.

If user asks for a specific area only (e.g., "test PDFs"), run only that group + Pre-flight.

Read `references/test-cases.md` for all test parameters, pass/fail criteria, and MCP tools.

---

## Output Format

```
Group | Test                          | Result  | Notes
------|-------------------------------|---------|------------------
A     | Health Check                  | PASS    |
A     | Template Merge Field Audit    | PASS    |
A     | TipTap Roundtrip              | PASS    |
B     | Clause CRUD                   | PASS    |
B     | Lease CRUD                    | PASS    |
C     | Native Signing E2E            | PASS    |
C     | Form Submit E2E               | PASS    |
C     | PDF Generation                | PASS    | 20 pages, 143KB
C     | PDF Layout Compare            | PASS    | 0 warnings
D     | Builder Session               | PASS    |
D     | Clause AI Generation          | PASS    |
------|-------------------------------|---------|------------------
      | OVERALL                       | PASS    | 11/11
```

Include page count + size for PDF tests. Include warning count for layout compare.
After the table, add a **Failures** section with full detail for each failing test.

## Cleanup Protocol

All created resources (leases, clauses, submissions) must be deleted after tests.
If a test fails mid-way, still attempt cleanup. Battery must leave the DB in the same state it found it.
Exception: `esigning_native_signing_test` and `esigning_form_submit_test` handle their own cleanup.

## Reference Index

| Topic | File |
|-------|------|
| Full test specs: parameters, MCP tools, pass/fail criteria for all 11 tests | [test-cases.md](references/test-cases.md) |
