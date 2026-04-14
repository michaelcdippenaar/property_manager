---
name: klikk-leases-format-template
description: >
  Format, restructure, or improve the HTML content of a lease template stored in
  the database. Triggers when the user asks to: format a lease template, clean up
  template HTML, restructure a template document, improve heading styles, add missing
  RHA sections, or fix formatting in a lease template. Also triggers for requests like
  "format template ID 3", "clean up the lease template", "make the template look
  professional", or "add standard SA sections to the template".
---

# Lease Template Document Formatter

You are formatting the HTML content of a lease template stored in the Tremly database.
The formatted HTML will be saved back via the API and will immediately appear in the
Tiptap editor when the user opens the template.

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

## Standard SA lease section structure
When restructuring a template, use this heading hierarchy:

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

## Workflow

### Step 1: Identify the template

Ask the user for the template ID if not provided, or list available templates:

```bash
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/v1/leases/templates/ | python3 -m json.tool
```

### Step 2: Fetch current content

```bash
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/v1/leases/templates/{id}/ | python3 -m json.tool
```

Read the `content_html` field. If empty, note that the template has no HTML content yet
(it may only have a DOCX file — you can still generate formatted HTML from scratch).

### Step 3: Apply formatting

Analyse the current HTML and the user's request. Then produce the improved HTML.

Common formatting tasks:
- **Restructure**: Apply the standard SA section hierarchy above
- **Add missing sections**: Insert any RHA-required sections not present (deposit terms, POPIA, dispute resolution)
- **Convert merge fields**: Replace plain `{{ field }}` text with proper `<span data-merge-field>` syntax
- **Heading cleanup**: Normalise all-caps paragraphs to `<h2>`, bold section labels to `<h3>`
- **Professional spacing**: Ensure related content groups under `<h3>` with `<p>` children
- **List formatting**: Convert comma-separated lists to `<ul><li>` items

### Step 4: Save the formatted HTML

```bash
curl -s -X PATCH \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content_html": "<h1>...</h1>..."}' \
  http://localhost:8000/api/v1/leases/templates/{id}/
```

Confirm success by checking the response includes the updated `content_html`.

### Step 5: Report back

Tell the user:
- What structural changes were made (sections added/renamed/reorganised)
- How many merge fields were converted to chip format
- Any RHA compliance gaps found (missing required clauses)
- That the changes are live — they can open the template editor at `/leases` to see the result

## Authentication

The API requires a JWT access token. The user needs to provide one, or you can
obtain it via:

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "...", "password": "..."}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])"
```

Store as `ADMIN_TOKEN` for subsequent requests.

## In-editor alternative

If the user is already in the template editor UI, they can simply type formatting
requests in the AI chat panel (left side). The AI assistant has a `update_document`
tool that applies changes directly to the Tiptap editor without needing this CLI skill.

Example chat prompts that trigger the tool:
- "Format this document with proper headings"
- "Add the missing POPIA and dispute resolution sections"
- "Convert all the merge fields to chip format"
- "Restructure this as a standard SA lease"
- "Make section 4 a proper heading and clean up the rental terms"
