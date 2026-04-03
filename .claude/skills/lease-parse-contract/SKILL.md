---
name: lease-parse-contract
description: >
  Parse a PDF or DOCX lease contract, extract its structure, identify all
  variable/placeholder fields, and create a properly formatted HTML template with
  merge fields in the Tremly system. Triggers when the user asks to: parse a lease,
  import a contract, convert a lease to a template, extract fields from a contract,
  create a template from a PDF, import a DOCX lease, or turn a signed lease into a
  reusable template. Also triggers for requests like "parse this lease PDF",
  "import contract.docx as a template", "extract merge fields from this lease",
  or "convert this rental agreement to a template".
---

# Lease Contract Parser

You are parsing a PDF or DOCX lease contract and converting it into a formatted HTML
template with merge fields for the Tremly property management system. The output will
be saved as a new lease template via the API.

## Allowed HTML tags

Only use these tags — the Tiptap editor only renders these:
- `<h1>`, `<h2>`, `<h3>` — headings
- `<p>` — paragraphs
- `<ul>`, `<ol>`, `<li>` — lists
- `<strong>`, `<em>`, `<u>` — inline formatting
- `<hr>` — horizontal divider
- `<span data-merge-field="field_name">{{ field_name }}</span>` — merge fields

Do NOT use: `<div>`, `<table>`, `<span>` (except merge fields), `<br>`, `<html>`, `<body>`, `<style>`.

## Merge field syntax

Every variable placeholder must use the merge-field span format:
```html
<span data-merge-field="tenant_name">{{ tenant_name }}</span>
```
Plain `{{ tenant_name }}` text in paragraphs will not render as a chip in the editor.

## Workflow

### Step 1: Read the document

Determine the file type and extract the text content.

**For PDF files** — use the Read tool directly:
```
Read the file at /path/to/lease.pdf
```
Read all pages to get the full document text.

**For DOCX files** — use python-docx to extract structured text:
```bash
python3 -c "
import subprocess, sys
subprocess.run([sys.executable, '-m', 'pip', 'install', 'python-docx'], capture_output=True)
from docx import Document
doc = Document('/path/to/file.docx')
for i, p in enumerate(doc.paragraphs):
    print(f'[{p.style.name}] {p.text}')
for table in doc.tables:
    print('--- TABLE ---')
    for row in table.rows:
        print(' | '.join(cell.text.strip() for cell in row.cells))
"
```

### Step 2: Analyse structure

Identify the document structure:
- **Section headings**: numbered sections like "1. Schedule", "2. Interpretations"
- **Sub-sections**: numbered items like 1.1, 1.2, 2.1.1
- **List items**: bulleted or lettered lists (a), (b), (c)
- **Tables**: schedule tables, party details, banking info
- **Signature blocks**: at the end of the document

Map heading styles:
- Document title and main heading: `<h1>`
- Major numbered sections (1., 2., 3.): `<h2>`
- Sub-sections (1.1, 1.2): `<h3>`
- Body text and clauses: `<p>`
- Bulleted/lettered lists: `<ul><li>` or `<ol><li>`
- Section dividers: `<hr>`

### Step 3: Identify variables and create merge fields

Look for these patterns and convert to merge fields:

- Blank lines or underscores after labels (e.g., "Name: ___________")
- Square bracket placeholders (e.g., "[Tenant Name]")
- Angle bracket placeholders (e.g., "<insert date>")
- Specific real data values that should be templated (names, addresses, amounts, dates)
- Table cells with labels paired with values or empty cells

**Common SA lease variable categories and field names:**

| Category | Fields |
|----------|--------|
| **Landlord** | `landlord_name`, `landlord_registration_no`, `landlord_vat_no`, `landlord_representative`, `landlord_title`, `landlord_contact`, `landlord_email`, `landlord_physical_address` |
| **Tenant 1** | `tenant1_name`, `tenant1_id_number`, `tenant1_contact`, `tenant1_email` |
| **Tenant 2** | `tenant2_name`, `tenant2_id_number`, `tenant2_contact`, `tenant2_email` |
| **Property** | `property_address`, `property_suburb`, `property_city`, `property_area_code`, `property_unit_number`, `property_description`, `property_max_occupants` |
| **Lease terms** | `lease_start_date`, `lease_end_date`, `lease_period`, `early_termination_penalty` |
| **Financial** | `monthly_rent`, `monthly_rent_words`, `deposit_amount`, `deposit_amount_words`, `escalation_percentage` |
| **Banking** | `bank_name`, `account_holder`, `account_no`, `branch_name`, `branch_code`, `account_type`, `payment_reference` |
| **Utilities** | `included_utilities`, `tenant_utilities` |
| **Signatures** | `landlord_signature_date`, `tenant1_signature_date`, `tenant2_signature_date`, `witness1_name`, `witness2_name` |

**Tips for variable identification:**
- If the document has real data filled in (like "Klikk (Pty) Ltd"), identify these as variables that should become merge fields
- If the document has blank spaces or "[Placeholder]" text, these are clearly variables
- Common patterns: "Name: ____", "Amount: R____", "[Date]", "................"
- Bank details are always variables
- Addresses, names, dates, amounts are always variables
- Legal boilerplate text is NOT a variable — keep it as static text

### Step 4: Generate HTML

Produce the formatted HTML applying these rules:

1. Main document title as `<h1>`
2. RHA subtitle as `<p>` immediately after `<h1>`
3. `<hr>` between major sections
4. Major numbered sections as `<h2>` (e.g., `<h2>1. PARTIES</h2>`)
5. Sub-sections as `<h3>` (e.g., `<h3>1.1 Landlord</h3>`)
6. All clause text as `<p>` elements
7. All variables wrapped in `<span data-merge-field="field_name">{{ field_name }}</span>`
8. Lists converted to `<ul><li>` or `<ol><li>` as appropriate
9. Bold/italic/underline preserved with `<strong>`, `<em>`, `<u>`

Follow the standard SA lease section structure where possible:
```
<h1>RESIDENTIAL LEASE AGREEMENT</h1>
<p>(In terms of the Rental Housing Act 50 of 1999, as amended)</p>
<hr>

<h2>1. PARTIES</h2>
<h3>1.1 Landlord</h3>  ...fields...
<h3>1.2 Tenant(s)</h3> ...fields...

<h2>2. PREMISES</h2>
<h2>3. LEASE PERIOD</h2>
<h2>4. RENTAL AND DEPOSIT</h2>
<h2>5. UTILITIES</h2>
<h2>6. OCCUPANCY</h2>
<h2>7. MAINTENANCE AND REPAIRS</h2>
<h2>8. INSPECTIONS</h2>
<h2>9. NOTICE AND TERMINATION</h2>
<h2>10. CONSUMER PROTECTION ACT</h2>
<h2>11. PROTECTION OF PERSONAL INFORMATION (POPIA)</h2>
<h2>12. DISPUTE RESOLUTION</h2>
<h2>13. SIGNATURES</h2>
```

### Step 5: Build fields schema

Create the fields array with every merge field used in the HTML:
```json
[
  {"ref": "landlord_name", "label": "Landlord Name", "type": "text"},
  {"ref": "tenant1_name", "label": "Tenant 1 Name", "type": "text"},
  {"ref": "monthly_rent", "label": "Monthly Rent", "type": "text"},
  {"ref": "lease_start_date", "label": "Lease Start Date", "type": "text"}
]
```

Ensure every `data-merge-field` attribute value in the HTML has a corresponding entry
in the fields array, and vice versa.

### Step 6: Save to database

Authenticate and create a new template:

```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "...", "password": "..."}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")
```

```bash
# Create the template
TEMPLATE_ID=$(curl -s -X POST http://localhost:8000/api/v1/leases/templates/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Template Name", "version": "1.0", "province": "gauteng"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
```

```bash
# Save the HTML content and fields schema using Python to handle JSON encoding
python3 << 'PYEOF'
import json, subprocess

html = """..."""  # the generated HTML (paste full output here)

fields = [...]  # the fields array

payload = json.dumps({
    "content_html": html,
    "fields_schema": fields
})

with open("/tmp/template_payload.json", "w") as f:
    f.write(payload)
PYEOF

curl -s -X PATCH \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @/tmp/template_payload.json \
  http://localhost:8000/api/v1/leases/templates/$TEMPLATE_ID/
```

Confirm success by checking the response includes the updated `content_html`.

Clean up the temp file:
```bash
rm -f /tmp/template_payload.json
```

### Step 7: Report results

Tell the user:
- Number of sections found and how they were mapped
- Number of merge fields identified (with a full list of field refs and labels)
- Any sections from the original document that were restructured or renamed
- Any RHA compliance gaps (missing required sections like POPIA, dispute resolution, deposit terms)
- The template ID and that it is now available in the editor at `/leases`
- Recommend running the `format-lease-document` skill if further formatting refinements are needed

## Authentication

The API requires a JWT access token. The user needs to provide one, or you can
obtain it via:

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "...", "password": "..."}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])"
```

Store as `TOKEN` for subsequent requests.

## Companion skill

This skill works alongside `format-lease-document` which handles reformatting and
restructuring of existing templates. Use `parse-lease-contract` for initial
import/parsing of PDF or DOCX files, and `format-lease-document` for subsequent
editing and formatting improvements.
