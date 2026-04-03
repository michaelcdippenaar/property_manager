---
name: lease-test-battery
description: >
  Run the full lease and e-signing integration test battery via the tremly-e2e MCP server.
  Trigger for: "run tests", "run test battery", "run lease tests", "test the lease system",
  "check if signing works", "run integration tests", "leases-test-battery", or any request to
  verify that the lease signing pipeline, templates, and merge fields are working correctly.
---

# Lease Test Battery

You are running the Tremly lease and e-signing integration test battery. This covers template
integrity, e-signing flows, PDF generation, and merge field correctness.

## Pre-flight

Check authentication status first. If not logged in, call `mcp__tremly-e2e__auth_login` with
the default credentials before running any tests.

```
auth_status → if not authenticated → auth_login
```

## Test Suite

Run each test below in sequence. Collect all results, then print a single summary table.

### 1. Health Check
Tool: `health_check`
- Pings all backend API endpoints
- Runs the template merge field audit (checks for row/label mismatches in all active templates)
- **Pass criteria**: `ok: true`, all endpoints status `OK`, `template_merge_field_audit.status === "OK"`
- **On failure**: List failing endpoints and any templates with merge field issues

### 2. TipTap Roundtrip
Tool: `template_tiptap_roundtrip`
- Creates a template with v2 TipTap JSON envelope, re-fetches, verifies integrity, then deletes
- **Pass criteria**: all steps pass (`ok: true`)
- **On failure**: Show which step failed and the actual vs expected values

### 3. Template Merge Field Audit
Tool: `template_merge_field_audit`
- Scans every active template for merge field mismatches:
  - Email rows must not use phone field names
  - Phone/Contact rows must not use email field names
  - `data-label` must agree with `data-field-name` (name label → name field, id label → id field, etc.)
- **Pass criteria**: `ok: true`, zero issues across all templates
- **On failure**: List each template and its specific mismatches with the offending `fieldName` and context

### 4. Native Signing End-to-End
Tool: `esigning_native_signing_test`
- Creates a real lease + native signing submission
- Fetches public document as tenant, verifies HTML + signing fields present
- Simulates signing (POST signature data)
- Checks submission reaches `in_progress` or `completed` status
- Cleans up (deletes lease)
- **Pass criteria**: `ok: true`
- **On failure**: Show which step failed

### 5. PDF Generation
Tool: `esigning_test_pdf`
- Generates a signed PDF for a test submission and validates it is a real PDF (starts with `%PDF`)
- **Pass criteria**: `ok: true`, valid PDF returned
- **On failure**: Show the error and PDF size if available

### 6. PDF Layout Compare
Tool: `esigning_pdf_layout_compare`
- Generates PDFs at multiple page sizes and checks character count consistency
- Validates that all signers are found in the submission
- **Pass criteria**: `ok: true`, consistent layout across page sizes
- **On failure**: Show layout diff and signer count discrepancy

## Output Format

After all tests complete, print a summary table:

```
Test                          | Result  | Notes
------------------------------|---------|-------
Health Check                  | ✅ PASS |
TipTap Roundtrip              | ✅ PASS |
Template Merge Field Audit    | ✅ PASS |
Native Signing E2E            | ✅ PASS |
PDF Generation                | ✅ PASS |
PDF Layout Compare            | ✅ PASS |
------------------------------|---------|-------
OVERALL                       | ✅ PASS |
```

If any test fails, replace ✅ PASS with ❌ FAIL and add a note. After the table, print a
"Failures" section with the full detail for each failing test so the developer can act on it.

## Merge Field Audit Detail

When the merge field audit finds issues, explain each one clearly:

- **row_field_mismatch**: A label like "Email:" in the document uses a field like `tenant_1_phone`.
  The field name must contain the same semantic as the row label.
- **label_field_mismatch**: A merge field span has `data-label="Email"` but `data-field-name` contains
  something other than "email". These must agree.

Always name the affected template and the specific field so the developer can fix it in the
TipTap editor or via a DB shell patch.
