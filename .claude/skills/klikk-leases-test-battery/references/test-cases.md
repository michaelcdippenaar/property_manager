# Test Cases — Groups A–D

---

## Group A: Foundation

### Test 1: Health Check
**Tool:** `health_check`
- Pings all backend API endpoints; includes template merge field audit
- **Pass:** `ok: true`, all endpoints `OK`, `template_merge_field_audit.status === "OK"`
- **Fail:** List failing endpoints and templates with merge field issues

### Test 2: Template Merge Field Audit
**Tool:** `template_merge_field_audit`
- Scans every active template for merge field mismatches:
  - Email rows must not use phone field names
  - Phone/Contact rows must not use email field names
  - `data-label` must agree with `data-field-name`
- **Pass:** `ok: true`, zero issues across all templates
- **Fail:** List each template and its specific mismatches with offending `fieldName`

### Test 3: TipTap Roundtrip
**Tool:** `template_tiptap_roundtrip`
- Creates template with v2 TipTap JSON envelope, re-fetches, verifies integrity, deletes
- **Pass:** All steps pass
- **Fail:** Which step failed, actual vs expected values

---

## Group B: CRUD Operations

### Test 4: Clause CRUD
**Tools:** `clause_create` → `clause_list` → `clause_use` → `clause_delete`
- Create: title "Test Clause — Battery", category "general", html `<p>This is a test clause for the integration test battery.</p>`
- List → verify new clause appears; Mark as used; Delete → verify gone
- **Pass:** All 4 operations succeed
- **Fail:** Which operation failed and error returned

### Test 5: Lease CRUD
**Tools:** `lease_list` → `lease_create` → `lease_get` → `lease_update` → `lease_delete`
- List leases to find existing `unit_id` and `primary_tenant_id` (use first active lease)
- Create: status "draft", start_date tomorrow, end_date +12 months, monthly_rent "8500", notes "Test Battery — safe to delete"
- Get → verify fields match; Update notes to "Updated by test battery"; Delete
- **Pass:** All operations succeed; get returns correct data
- **CRITICAL:** Always clean up — delete the test lease even if later steps fail

---

## Group C: E-Signing Pipeline

> Use first active lease from `lease_list`. If none exists, create temporary lease, run group, then delete.

### Test 6: Native Signing E2E
**Tool:** `esigning_native_signing_test`
- Signers: `[{name: "Test Landlord", email: "test-landlord@test.com", role: "landlord"}, {name: "Test Tenant", email: "test-tenant@test.com", role: "tenant_1"}]`
- Creates native signing submission, fetches public document, validates signing fields
- **Pass:** `ok: true`, all steps pass

### Test 7: Form Submit E2E
**Tool:** `esigning_form_submit_test`
- Same `lease_id` and signers as test 6
- Full round-trip: create submission → get public link → fetch document fields → submit with fake signature images → verify DB updated
- **Pass:** `ok: true`, captured data persisted, signer status updated

### Test 8: PDF Generation
**Tool:** `esigning_test_pdf`
- Use submission ID from test 7 (or find a completed submission via `esigning_list`)
- Validates PDF header (`%PDF`), counts pages, reports size
- **Pass:** Valid PDF, pages > 0, size > 10KB
- Include page count + file size in notes

### Test 9: PDF Layout Compare
**Tool:** `esigning_pdf_layout_compare`
- Same submission ID as test 8
- Checks: blank page detection, content density (no page < 15% avg chars), image positions (initials at consistent Y), text positions (no signing field text in top 20%), page count ≤ 30, footer consistency, audit trail (last page has ≥2 of: "Audit Trail", "Signer", "SHA-256", "Document Hash", "Electronic")
- **Pass:** All steps pass, zero warnings
- **Fail:** List each failing step; for image position failures show page + Y% coordinates

---

## Group D: Builder & AI

### Test 10: Builder Session
**Tools:** `builder_session_create` → `builder_session_message` → `builder_draft_list`
- Message: "Create a month-to-month lease for a studio apartment at R6500 per month"
- Wait for AI response (10–30s); list drafts to check draft was created
- **Pass:** Session created, AI responds with lease content, no errors
- **NOTE:** Do NOT finalize the session — avoids creating a real lease

### Test 11: Clause AI Generation
**Tool:** `clause_generate`
- Prompt: "Standard pet policy clause allowing one small dog under 10kg with a pet deposit of R2000"
- **Pass:** Response contains non-empty HTML mentioning pet + deposit
- **Cleanup:** Do not save the generated clause
