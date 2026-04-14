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

You are running the Tremly lease and e-signing integration test battery. This covers the full
stack: health checks, template integrity, clause management, lease CRUD, e-signing flows, PDF
generation, PDF layout validation, and builder sessions.

## Pre-flight

Check authentication status first. If not logged in, call `auth_login` with default credentials.

```
auth_status → if not authenticated → auth_login
```

## Test Suite

There are 11 tests organised in 4 groups. Run each test in sequence within its group.
Tests in different groups can run in parallel where possible, but the E-Signing group
depends on a lease existing, so run Foundation first.

If the user asks to test a specific area (e.g. "test PDFs"), run only the relevant group
plus Pre-flight. Otherwise run everything.

---

### Group A: Foundation

#### 1. Health Check
**Tool:** `health_check`
- Pings all backend API endpoints
- Includes template merge field audit
- **Pass:** `ok: true`, all endpoints `OK`, `template_merge_field_audit.status === "OK"`
- **Fail detail:** List failing endpoints and any templates with merge field issues

#### 2. Template Merge Field Audit
**Tool:** `template_merge_field_audit`
- Scans every active template for merge field mismatches:
  - Email rows must not use phone field names
  - Phone/Contact rows must not use email field names
  - `data-label` must agree with `data-field-name`
- **Pass:** `ok: true`, zero issues across all templates
- **Fail detail:** List each template and its specific mismatches with offending `fieldName`

#### 3. TipTap Roundtrip
**Tool:** `template_tiptap_roundtrip`
- Creates a template with v2 TipTap JSON envelope, re-fetches, verifies integrity, deletes
- **Pass:** all steps pass
- **Fail detail:** Which step failed, actual vs expected values

---

### Group B: CRUD Operations

#### 4. Clause CRUD
**Tools:** `clause_create` → `clause_list` → `clause_use` → `clause_delete`
- Create a test clause with title "Test Clause — Battery", category "general",
  html `<p>This is a test clause for the integration test battery.</p>`
- List clauses and verify the new clause appears
- Mark it as used (increment usage count)
- Delete it and verify it's gone from the list
- **Pass:** All four operations succeed, clause appears in list after create, gone after delete
- **Fail detail:** Which operation failed and the error returned

#### 5. Lease CRUD
**Tools:** `lease_list` → `lease_create` → `lease_get` → `lease_update` → `lease_delete`
- List leases to find an existing unit_id and primary_tenant_id (use the first active lease)
- Create a test lease with status "draft", start_date tomorrow, end_date +12 months,
  monthly_rent "8500", notes "Test Battery — safe to delete"
- Get the created lease by ID, verify fields match
- Update the lease: change notes to "Updated by test battery"
- Delete the lease
- **Pass:** All operations succeed, get returns correct data, delete succeeds
- **Fail detail:** Which operation failed
- **Important:** Always clean up — delete the test lease even if later steps fail

---

### Group C: E-Signing Pipeline

These tests need a lease. Use the first active lease from `lease_list` (status "active").
If no active lease exists, create a temporary one as in test 5, run the group, then delete it.

#### 6. Native Signing E2E
**Tool:** `esigning_native_signing_test`
- Pass `lease_id` from the active lease
- Pass signers: `[{name: "Test Landlord", email: "test-landlord@test.com", role: "landlord"},
  {name: "Test Tenant", email: "test-tenant@test.com", role: "tenant_1"}]`
- Creates a native signing submission, fetches public document, validates signing fields
- **Pass:** `ok: true`, all steps pass
- **Fail detail:** Which step failed

#### 7. Form Submit E2E
**Tool:** `esigning_form_submit_test`
- Same `lease_id` and signers as test 6
- Full round-trip: creates submission → gets public link → fetches document fields →
  submits form with fake signature images and captured merge field data →
  verifies DB was correctly updated via authenticated API
- **Pass:** `ok: true`, captured data persisted, signer status updated
- **Fail detail:** Which step failed, DB state vs expected

#### 8. PDF Generation
**Tool:** `esigning_test_pdf`
- Use a submission ID from test 7 (or find a completed submission via `esigning_list`)
- Generates a signed PDF, validates PDF header (`%PDF`), counts pages, reports size
- **Pass:** valid PDF returned, pages > 0, size > 10KB
- **Fail detail:** Error message, PDF size if available

#### 9. PDF Layout Compare
**Tool:** `esigning_pdf_layout_compare`
- Same submission ID as test 8
- Comprehensive layout analysis:
  - **Blank page detection** — no empty pages allowed
  - **Content density** — no page with <15% of average character count (excluding audit trail)
  - **Image position analysis** — initials images must be at consistent Y-positions (>90% of
    page height = footer). Flags images in top half of page or with >15% position spread.
  - **Text position analysis** — signing field placeholders must not appear in top 20% of page
  - **Page count check** — must be ≤30 pages for a standard SA lease
  - **Footer consistency** — footer content should appear across sampled pages
  - **Audit trail** — last page must contain ≥2 of: "Audit Trail", "Signer", "SHA-256",
    "Document Hash", "Electronic"
- **Pass:** all steps pass, zero warnings
- **Fail detail:** List each failing step with its issues. For image position failures,
  show the affected pages and Y-coordinate percentages.

---

### Group D: Builder & AI

#### 10. Builder Session
**Tools:** `builder_session_create` → `builder_session_message` → `builder_draft_list`
- Create a new builder session (no template_id — tests default flow)
- Send a message: "Create a month-to-month lease for a studio apartment at R6500 per month"
- Wait for AI response (may take 10-30s)
- List drafts to see if a draft was created
- **Pass:** Session created, AI responds with lease content, no errors
- **Fail detail:** Error from session creation or message send
- **Note:** Do NOT finalize the session — this avoids creating a real lease.
  The test only verifies the builder pipeline responds.

#### 11. Clause AI Generation
**Tool:** `clause_generate`
- Generate a clause with prompt: "Standard pet policy clause allowing one small dog under 10kg
  with a pet deposit of R2000"
- Verify the response contains HTML clause content
- **Pass:** Response contains non-empty HTML with relevant content (mentions pet, deposit)
- **Fail detail:** Error or empty response
- **Cleanup:** Do not save the generated clause — this just tests the AI pipeline responds

---

## Output Format

After all tests complete, print a summary table:

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

If any test fails, mark it FAIL and add a note. After the table, print a **Failures** section
with full detail for each failing test so the developer can act on it.

For PDF tests, always include page count and file size in the notes column.
For layout compare, include warning count and any specific issues.

## Merge Field Audit Detail

When the merge field audit finds issues, explain each one clearly:

- **row_field_mismatch**: A label like "Email:" in the document uses a field like `tenant_1_phone`.
  The field name must contain the same semantic as the row label.
- **label_field_mismatch**: A merge field span has `data-label="Email"` but `data-field-name`
  contains something other than "email". These must agree.

Always name the affected template and the specific field so the developer can fix it in the
TipTap editor or via a DB shell patch.

## Cleanup Protocol

Tests that create resources (leases, clauses, submissions) must clean up after themselves.
If a test fails mid-way, still attempt cleanup. The test battery should leave the database
in the same state it found it.

Exception: `esigning_native_signing_test` and `esigning_form_submit_test` handle their own
cleanup internally. Only manually clean up resources you created directly via `_create` tools.
