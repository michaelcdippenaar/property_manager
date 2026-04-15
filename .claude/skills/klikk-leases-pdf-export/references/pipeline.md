# PDF Pipeline — Stages 1–3

---

## Full Pipeline Flow

```
TipTap Editor (Vue)
  ↓  save: getHTML() + getJSON() → v2 JSON envelope
  ↓  stored in LeaseTemplate.content_html

generate_lease_html(lease)          ← fills merge fields, maps signing roles
  ↓
create_native_submission()          ← stores HTML snapshot, assigns signers
  ↓
Signers sign via custom Vue UI      ← captures signatures, initials, dates
  ↓
generate_signed_pdf(submission)     ← embeds signatures, cleans HTML
  ↓
gotenberg.html_to_pdf(html)         ← Chromium renders pixel-perfect PDF
  ↓
Final PDF bytes (with audit trail)
```

---

## Stage 1: generate_lease_html()

**Location:** `backend/apps/esigning/services.py:422`

### Steps:
1. Load template → find specified or most recent active `LeaseTemplate`
2. Extract HTML → parse v2 JSON envelope via `_extract_html()`
3. Fill merge fields → regex-replaces all 4 formats:
   - v1: `<span data-merge-field="X">...</span>`
   - v2: `<span data-type="merge-field" data-field-name="X">...</span>`
   - Reverse: `data-field-name` before `data-type`
   - Mustache: `{{field_name}}`
4. Convert legacy signing spans → `<signature-field>`, `<initials-field>`, `<date-field>`
5. Map signer roles → TipTap roles to signer identifiers
6. Deduplicate field names
7. Wrap with print CSS → returns full HTML5 document

### build_lease_context() — merge field values

**Location:** `backend/apps/esigning/services.py:202`

| Category | Fields |
|----------|--------|
| **Landlord** | `landlord_name`, `landlord_contact`, `landlord_phone`, `landlord_email`, `landlord_id` |
| **Property** | `property_address`, `property_name`, `unit_number`, `city`, `province` |
| **Tenant (legacy)** | `tenant_name`, `tenant_id`, `tenant_phone`, `tenant_email`, `tenant_address`, `tenant_employer`, `tenant_occupation`, `tenant_dob`, `tenant_emergency_contact`, `tenant_emergency_phone` |
| **Tenant (numbered)** | `tenant_1_name`, `tenant_1_id`, etc. |
| **Co-tenants** | `tenant_2_*`, `tenant_3_*` (up to 3 from `lease.co_tenants`) |
| **Lease terms** | `lease_start`, `lease_end`, `monthly_rent` (formatted `R X,XXX.XX`), `deposit`, `notice_period_days`, `water_included`, `electricity_prepaid`, `max_occupants`, `payment_reference` |

Missing values fall back to `—` (em-dash).

### Print CSS

```css
@page { size: A4; margin: 2cm; }
body { font-family: Arial, sans-serif; font-size: 10.5pt; line-height: 1.55; color: #111; }
h1 { font-size: 14pt; font-weight: bold; text-align: center; margin-bottom: 12pt; }
h2 { font-size: 11pt; font-weight: bold; margin: 8pt 0 3pt; }
p, li { margin: 3pt 0; }
table { border-collapse: collapse; width: 100%; margin: 4pt 0; }
td, th { border: 1px solid #d1d5db; padding: 5pt 7pt; font-size: 10pt; }
```

---

## Stage 2: Native Signing Submission

**Location:** `backend/apps/esigning/services.py:655`

`create_native_submission()` creates an `ESigningSubmission` with:
- `signing_backend = 'NATIVE'`
- `document_html` — HTML snapshot (frozen at signing time)
- `document_hash` — SHA-256 for integrity verification
- `signers` — list with locally-assigned IDs and field metadata

Signers sign via custom Vue UI (`/sign/<uuid>/`): captures signature/initials as base64 data URLs and date fields as text.

---

## Stage 3: generate_signed_pdf()

**Location:** `backend/apps/esigning/services.py:978`

### Processing steps:
1. Convert PaginationPlus wrappers → `page-break-after:always` divs
2. Remove empty `<p></p>` spacers
3. Apply captured data from signers
4. Embed signatures:
   - `signature` fields → `<img>` height 50px
   - `initials` fields → `<img>` height 14px (inline)
   - `date` fields → bold text span
5. Clean up unsigned fields → placeholder underlines
6. Clean up unfilled merge fields → underline placeholder; filled → bold
7. Append audit trail page (SHA-256 hash, signer table, legal notice)
8. Render with Gotenberg → `gotenberg.html_to_pdf(html)` → pixel-perfect PDF
9. Fallback to xhtml2pdf if Gotenberg unavailable (degraded CSS)

### Gotenberg defaults:
- A4 (8.27 × 11.7 inches), 2cm margins
- `preferCssPageSize: true` — CSS `@page` rules take precedence
- `printBackground: true` — include background colors
- 60-second timeout

### Document Integrity
- On creation: `document_hash = sha256(document_html)`
- Before each signer completes: verifies hash (with `select_for_update`)
- Hash printed on audit trail page
