# Parse Workflow — Steps 1–7

---

## Step 1: Read the Document

**For PDF files:**

Use the `Read` tool with the file path — Claude reads the PDF natively (vision-based), which correctly handles table-structured pages like the Klikk lease schedule.

```
Read the file at /path/to/lease.pdf
```

**Do NOT use pypdf or any text-extraction library.** pypdf garbles table cell order in structured PDFs, causing multi-tenant entries (Tenant Two, Three, Four) and table form fields to be missed or misread. Claude's native PDF reading is the only reliable approach for table-heavy SA lease templates.

**For DOCX files** — use python-docx:
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

---

## Step 2: Analyse Structure

Identify:
- **Section headings**: numbered sections like "1. Schedule", "2. Interpretations"
- **Sub-sections**: numbered items like 1.1, 1.2, 2.1.1
- **List items**: bulleted or lettered lists (a), (b), (c)
- **Tables**: schedule tables, party details, banking info
- **Signature blocks**: at the end of the document

Heading mapping:
- Document title and main heading → `<h1>`
- Major numbered sections (1., 2., 3.) → `<h2>`
- Sub-sections (1.1, 1.2) → `<h3>`
- Body text and clauses → `<p>`
- Bulleted/lettered lists → `<ul><li>` or `<ol><li>`
- Section dividers → `<hr>`

---

## Step 3: Identify Variables

See `references/field-mapping.md` for the full field category table and identification tips.

---

## Step 4: Generate HTML

Rules:
1. Main document title as `<h1>`
2. RHA subtitle as `<p>` immediately after `<h1>`
3. `<hr>` between major sections
4. Major numbered sections as `<h2>` (e.g., `<h2>1. PARTIES</h2>`)
5. Sub-sections as `<h3>` (e.g., `<h3>1.1 Landlord</h3>`)
6. All clause text as `<p>` elements
7. All variables wrapped in `<span data-merge-field="field_name">{{ field_name }}</span>`
8. Lists converted to `<ul><li>` or `<ol><li>` as appropriate
9. Bold/italic/underline preserved with `<strong>`, `<em>`, `<u>`

---

## Step 5: Build Fields Schema

Create the fields array with every merge field used. See `references/field-mapping.md` for the schema format.

---

## Step 6: Save to Database

```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "...", "password": "..."}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")
```

```bash
# Create template
TEMPLATE_ID=$(curl -s -X POST http://localhost:8000/api/v1/leases/templates/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Template Name", "version": "1.0", "province": "gauteng"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
```

```bash
# Save HTML + fields schema
python3 << 'PYEOF'
import json, subprocess

html = """..."""  # the generated HTML
fields = [...]    # the fields array

payload = json.dumps({"content_html": html, "fields_schema": fields})

with open("/tmp/template_payload.json", "w") as f:
    f.write(payload)
PYEOF

curl -s -X PATCH \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @/tmp/template_payload.json \
  http://localhost:8000/api/v1/leases/templates/$TEMPLATE_ID/

rm -f /tmp/template_payload.json
```

---

## Step 7: Report Results

Tell the user:
- Number of sections found and how they were mapped
- Number of merge fields identified (with full list of field refs and labels)
- Any sections restructured or renamed from the original
- Any RHA compliance gaps (missing POPIA, dispute resolution, deposit terms)
- The template ID (available in the editor at `/leases`)
- Suggest running the `klikk-leases-format-template` skill if further formatting refinements are needed
