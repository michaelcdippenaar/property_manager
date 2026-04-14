---
name: klikk-leases-pdf-export
description: >
  Convert TipTap lease template HTML to PDF in the Tremly property management platform. Use this
  skill when the user asks about PDF generation from lease templates, HTML-to-PDF rendering,
  the merge field replacement pipeline, signature embedding in PDFs, audit trail generation,
  Gotenberg configuration, Chromium PDF rendering, print CSS for leases, or troubleshooting
  the lease PDF output. Also trigger for: "generate PDF", "lease PDF", "PDF export",
  "PDF not rendering", "signed PDF", "audit trail", "gotenberg", "chromium", "merge fields
  not filling", "PDF layout", "page breaks in PDF", "signature in PDF", "download lease",
  "PDF styling", or any question about how TipTap content becomes a downloadable/signable PDF.
  Even if the user just says "the PDF looks wrong" or "merge fields aren't being replaced" —
  use this skill.
---

# TipTap-to-PDF Pipeline — Tremly Lease Module

This skill covers the full pipeline from TipTap editor content to final signed PDF. The flow has
three main stages: template rendering, native signing, and Gotenberg PDF generation.

## Pipeline Overview

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

## Key Files

| File | Purpose |
|------|---------|
| `backend/apps/esigning/services.py` | All PDF pipeline functions |
| `backend/apps/esigning/gotenberg.py` | Gotenberg Python client (`html_to_pdf`, `health_check`) |
| `backend/apps/leases/models.py` | `LeaseTemplate` model (stores v2 JSON envelope) |
| `backend/apps/leases/template_views.py` | `_extract_html()` — parses JSON envelope to raw HTML |
| `backend/apps/esigning/models.py` | `ESigningSubmission` model (stores HTML snapshot) |

> For deep Gotenberg API details (parameters, headers/footers, wait strategies, PDF security),
> see the **gotenberg** skill at `.claude/skills/gotenberg/SKILL.md`.

## Stage 1: generate_lease_html()

**Location:** `backend/apps/esigning/services.py:422`

Takes a `Lease` ORM object and produces a complete HTML5 document ready for signing.

### What it does:
1. **Load template** — finds the specified or most recent active `LeaseTemplate`
2. **Extract HTML** — parses the v2 JSON envelope via `_extract_html()` to get raw HTML
3. **Fill merge fields** — calls `build_lease_context(lease)` for values, then regex-replaces:
   - v1 format: `<span data-merge-field="X">...</span>`
   - v2 format: `<span data-type="merge-field" data-field-name="X">...</span>`
   - Reverse attribute order: `data-field-name` before `data-type`
   - Mustache markers: `{{field_name}}`
4. **Convert legacy signing spans** — old templates used `<span data-type="signature-block">`;
   converts to native signing tags: `<signature-field>`, `<initials-field>`, `<date-field>`
5. **Map signer roles** — converts TipTap roles (landlord, tenant_1) to signer identifiers
6. **Deduplicate field names** — ensures each signing field has a unique name
7. **Wrap with CSS** — embeds print-ready CSS and returns full HTML5 document

### Native mode (`native=True`)
When generating HTML for native signing, unfilled merge fields are preserved
as TipTap `<span data-type="merge-field">` nodes so the signing UI can render them as
editable inputs for the signer to fill in.

### build_lease_context()

**Location:** `backend/apps/esigning/services.py:202`

Maps a `Lease` ORM object to a dict of merge field key/value pairs:

| Category | Fields |
|----------|--------|
| **Landlord** | `landlord_name`, `landlord_contact`, `landlord_phone`, `landlord_email`, `landlord_id` |
| **Property** | `property_address`, `property_name`, `unit_number`, `city`, `province` |
| **Tenant (legacy)** | `tenant_name`, `tenant_id`, `tenant_phone`, `tenant_email`, `tenant_contact`, `tenant_address`, `tenant_employer`, `tenant_occupation`, `tenant_dob`, `tenant_emergency_contact`, `tenant_emergency_phone` |
| **Tenant (numbered)** | `tenant_1_name`, `tenant_1_id`, etc. (same fields with `tenant_1_` prefix) |
| **Co-tenants** | `tenant_2_*`, `tenant_3_*` (up to 3 co-tenants from `lease.co_tenants`) |
| **Lease terms** | `lease_start`, `lease_end`, `monthly_rent` (formatted as `R X,XXX.XX`), `deposit`, `notice_period_days`, `water_included`, `electricity_prepaid`, `max_occupants`, `payment_reference` |

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

## Stage 2: Native Signing Submission

**Location:** `backend/apps/esigning/services.py:655`

`create_native_submission()` creates an `ESigningSubmission` with:
- `signing_backend = 'NATIVE'`
- `document_html` — the filled HTML snapshot (frozen at signing time)
- `document_hash` — SHA-256 of the HTML for integrity verification
- `signers` — list of signer records with locally-assigned IDs and field metadata

Each signer signs via the custom Vue signing UI (`/sign/<uuid>/`), which captures
signature/initials images as base64 data URLs and date fields as text.

## Stage 3: generate_signed_pdf()

**Location:** `backend/apps/esigning/services.py:978`

Takes a completed `ESigningSubmission` and produces final PDF bytes using Gotenberg (Chromium).

### Processing steps:
1. **Convert PaginationPlus wrappers** — TipTap's PaginationPlus uses `page-break-after:always`
   wrapper divs; these are converted to clean CSS page-break divs that Chromium handles natively
2. **Remove empty paragraph spacers** — collapses runs of `<p></p>` (TipTap page padding)
3. **Apply captured data** — replaces remaining merge-field spans with signer-entered values
   via `apply_captured_data(html, captured_data)`
4. **Embed signatures** — for each signer's `signed_fields`:
   - `signature` fields → `<img>` with base64 data URL, height 50px
   - `initials` fields → `<img>` with base64 data URL, height 14px (inline)
   - `date` fields → bold text span with date value
5. **Clean up unsigned fields** — replaces remaining signing field tags with placeholder
   underlines (e.g., `___/___/______` for dates)
6. **Clean up unfilled merge fields** — mustache-style content gets underline placeholder;
   already-filled content gets bold styling
7. **Append audit trail page** — new page with:
   - Document SHA-256 hash
   - Table: signer name, email, role, IP address, signed-at timestamp, user agent
   - Legal notice about electronic signatures
8. **Render with Gotenberg** — `gotenberg.html_to_pdf(html)` sends the HTML to the Gotenberg
   Docker service, which uses headless Chromium to render pixel-perfect PDF bytes
9. **Fallback to xhtml2pdf** — if Gotenberg is unavailable (service down, network error),
   falls back to `xhtml2pdf` (pisa) for basic PDF generation with degraded CSS support

### Gotenberg Rendering (Primary)

Gotenberg uses the same Chromium engine that powers the TipTap editor in the browser, so
the PDF output is pixel-perfect identical to what users see when editing lease templates.

Key advantages over xhtml2pdf:
- **Full CSS3 support** — flexbox, grid, advanced selectors all work
- **Native page breaks** — `page-break-before`, `page-break-after`, and the modern
  `break-before`/`break-after` CSS properties work exactly as in a browser
- **Font rendering** — standard web fonts render identically to the browser
- **Base64 images** — signature and initials data URLs render correctly
- **Print media** — `@page` rules with `preferCssPageSize: true` give precise control
  over page size and margins
- **Background colors** — `printBackground: true` ensures colored table headers and
  highlighted text render in the PDF

The Gotenberg client (`backend/apps/esigning/gotenberg.py`) sends the HTML as a
multipart form POST to `POST /forms/chromium/convert/html` with these defaults:
- A4 paper size (8.27 x 11.7 inches)
- 2cm margins (~0.79 inches)
- `preferCssPageSize: true` — CSS `@page` rules take precedence
- `printBackground: true` — include background colors
- 60-second timeout

### xhtml2pdf Fallback

xhtml2pdf is kept as a fallback for when Gotenberg is unavailable. It has significant
limitations compared to Chromium rendering:
- Limited CSS3 support (no flexbox, grid, or advanced selectors)
- Images must be base64 data URLs or accessible file paths (no remote URLs)
- Font support limited to standard web fonts (Arial, Times, Courier, etc.)
- Complex nested tables can break
- Layout may differ noticeably from the TipTap editor preview

### Document Integrity

The pipeline includes SHA-256 hashing for tamper detection:
- On submission creation: `document_hash = sha256(document_html)`
- Before completing each signer: verifies hash matches (via `select_for_update` for concurrency)
- Hash printed on audit trail page

## Troubleshooting

### Merge fields not being replaced
- Check that field names in the template match exactly what `build_lease_context()` returns
- The regex handles both attribute orderings (`data-type` before/after `data-field-name`)
- Mustache markers (`{{field}}`) are replaced as a final pass
- In native mode, unfilled fields are preserved as spans — this is intentional

### Page breaks not working in PDF
- Chromium natively supports `page-break-before`, `page-break-after`, and `break-before`/`break-after`
- TipTap PaginationPlus wrappers are converted to clean `page-break-after:always` divs
- If page breaks are wrong, check that the regex conversion is matching correctly
- Verify `preferCssPageSize` is `true` so CSS `@page` rules are respected

### Signatures not appearing in PDF
- Signature `imageData` must be a valid base64 data URL (`data:image/png;base64,...`)
- The regex matches `<signature-field name="X">` — field names must match exactly
- Check `signer['signed_fields']` has the correct `fieldName` and `fieldType`

### PDF layout issues
- Gotenberg renders with full Chromium — CSS flexbox and grid work fine
- If the PDF looks different from the editor, check `emulatedMediaType` (should be `print`)
- Ensure `printBackground: true` for background colors/images
- Font sizes should use `pt` units for consistent rendering
- Wide tables: set `width:100%` and use `word-break:break-all` for long text

### Gotenberg not responding
- Check Docker: `docker compose ps gotenberg`
- Check health: `curl http://localhost:3000/health`
- Check logs: `docker compose logs gotenberg`
- The pipeline will automatically fall back to xhtml2pdf — check Django logs for the warning
- Default API timeout is 60s — increase in `gotenberg.py` or `docker-compose.yml`

### PDF quality degraded (xhtml2pdf fallback active)
- If logs show "Gotenberg PDF generation failed, falling back to xhtml2pdf", the PDF
  will have degraded CSS rendering
- Fix the Gotenberg service to restore pixel-perfect output
- Common Gotenberg failures: container not running, timeout exceeded, port misconfiguration

### Adding a new merge field
1. Add the field to `build_lease_context()` in `services.py`
2. Add a corresponding `MergeField` node in the TipTap template editor
3. The field will be auto-replaced during `generate_lease_html()`
