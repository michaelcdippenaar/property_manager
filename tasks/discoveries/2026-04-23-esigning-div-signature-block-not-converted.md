---
discovered_by: rentals-tester
discovered_during: QA-018
discovered_at: 2026-04-23
priority_hint: P1
suggested_prefix: QA
---

## What I found
`_convert_legacy_signing_span` (services.py ~line 482) uses a regex that only matches `<span data-type="signature-block" ...>` elements. Template 57 ("The One Stellenbosch - Student Lease") uses `<div data-type="signature-block" ...>` elements, which the regex does not match. As a result, the signature-block divs are never converted to `<signature-field>` tags, and `extract_signer_fields` returns 0 fields for any submission generated from template 57 (or any template using `<div>` for signature blocks).

## Why it matters
The Step 5 acceptance criterion for QA-018 ("confirm fields are returned") **fails** for template 57 in E2E testing. All tenants and landlords using template 57 will see no signing fields and be unable to complete native e-signing. The alias fix in QA-018 is correct but never exercises this code path because the `<div>` elements bypass `_convert_legacy_signing_span` entirely.

## Where I saw it
- `backend/apps/esigning/services.py:482` — regex `r'<span([^>]+data-type="signature-block"[^>]*)>'` does not match `<div>`
- Template 57 content_html (stored in `leases_leasetemplates`, id=57): uses `<div data-type="signature-block" data-field-type="signature" data-signer-role="tenant" ...>`
- Submission 99 (generated from template 57 during QA-018 test): `document_html` contains `data-signer-role="tenant"` as `<div>` attrs but zero `<signature-field>` tags

## Suggested acceptance criteria (rough)
- [ ] `_convert_legacy_signing_span` (or a new companion) also handles `<div data-type="signature-block">` elements
- [ ] E2E Step 5 (`esigning_native_signing_test`) returns > 0 fields when using template 57
- [ ] Regression test added asserting the div-based signature block is correctly converted

## Why I didn't fix it in the current task
Out of scope for QA-018 which targeted only the role-alias mismatch. The `<div>` vs `<span>` discrepancy is a separate rendering bug in the template editor output path that requires its own implementer pass.
