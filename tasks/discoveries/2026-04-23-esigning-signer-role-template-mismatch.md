---
discovered_by: rentals-tester
discovered_during: QA-017
discovered_at: 2026-04-23
priority_hint: P1
suggested_prefix: QA
---

## What I found
The `create_native_submission` service maps signer input role `"tenant"` → `"tenant_1"` in the signer record, but `generate_lease_html` preserves the original `data-signer-role="tenant"` attribute from the template HTML when converting legacy signature-block spans. This means `extract_signer_fields` finds no fields for `signer_role="tenant_1"` even when the template has a tenant signature block.

## Why it matters
Any end-to-end native signing test (and any real tenant signing) where the input role is `"tenant"` or `"tenant 1"` will produce 0 signing fields in the public document endpoint, making it impossible to complete signing. The `esigning_native_signing_test` MCP tool Step 5 fails with "No fields found" for all available templates.

## Where I saw it
- `backend/apps/esigning/services.py` — `_role_to_tiptap` mapping (line ~554) maps `'tenant'` → `'tenant_1'` for signer records
- `backend/apps/esigning/services.py` — `_convert_legacy_signing_span` (line ~437) preserves original `data-signer-role` from template HTML unchanged (e.g. `"tenant"`)
- `backend/apps/esigning/services.py:597` — `extract_signer_fields` does a case-insensitive match on `signer_role` from the signer record

## Suggested acceptance criteria (rough)
- [ ] Either normalise template HTML roles to `tenant_1`/`tenant_2` during conversion, or extend `extract_signer_fields` to accept aliases (e.g. `"tenant"` matches `"tenant_1"`)
- [ ] `esigning_native_signing_test` Step 5 returns > 0 fields for a lease with a template that has tenant signature blocks
- [ ] Existing templates (e.g. template 57) produce signing fields when a `tenant_1` signer creates a native submission

## Why I didn't fix it in the current task
Out of scope — QA-017 is testing the `signer_role` parameter fix (QA-017 Step 3), not the field extraction logic.
