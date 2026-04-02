# DocuSeal API Reference

## Authentication

All requests require: `X-Auth-Token: YOUR_API_KEY` header.

Base URLs: `https://api.docuseal.com` (US) / `https://api.docuseal.eu` (EU) / self-hosted.

---

## API Endpoints

### Templates

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/templates` | List templates |
| `GET` | `/templates/{id}` | Get template |
| `POST` | `/templates/html` | Create from HTML |
| `POST` | `/templates/pdf` | Create from PDF |
| `POST` | `/templates/docx` | Create from DOCX |
| `POST` | `/templates/{id}/clone` | Clone template |
| `POST` | `/templates/merge` | Merge templates |
| `PUT` | `/templates/{id}` | Update template |
| `PUT` | `/templates/{id}/documents` | Update documents |
| `DELETE` | `/templates/{id}` | Archive template |

### Submissions

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/submissions` | List submissions |
| `GET` | `/submissions/{id}` | Get submission |
| `GET` | `/submissions/{id}/documents` | Get documents |
| `POST` | `/submissions` | Create from template |
| `POST` | `/submissions/html` | Create from HTML (one-off) |
| `POST` | `/submissions/pdf` | Create from PDF (one-off) |
| `POST` | `/submissions/docx` | Create from DOCX (one-off) |
| `DELETE` | `/submissions/{id}` | Archive submission |

### Submitters

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/submitters` | List submitters |
| `GET` | `/submitters/{id}` | Get submitter |
| `PUT` | `/submitters/{id}` | Update/complete submitter |

---

## Creating Templates from HTML (Recommended)

**`POST /templates/html`**

```json
{
  "name": "Document Name",
  "documents": [{
    "name": "document-id",
    "html": "<html>...</html>",
    "html_header": "<html>header markup</html>",
    "html_footer": "<html>footer markup</html>",
    "size": "A4"
  }]
}
```

Header/footer special tags:
```html
<span class="pageNumber"></span>
<span class="totalPages"></span>
```

### HTML Field Tags (16 types)

DocuSeal auto-detects these custom HTML tags and converts them to interactive signing fields:

#### Signature & Identity

```html
<signature-field name="Signature" role="First Party" required="true"
  format="drawn_or_typed" style="width:200px;height:60px;display:inline-block;"> </signature-field>

<initials-field name="Initials" role="First Party" required="true"
  style="width:100px;height:40px;display:inline-block;"> </initials-field>

<stamp-field name="Company Stamp" role="First Party"
  style="width:150px;height:80px;display:inline-block;"> </stamp-field>

<image-field name="Photo ID" role="First Party"
  style="width:200px;height:150px;display:inline-block;"> </image-field>
```

Signature `format` options: `drawn`, `typed`, `drawn_or_typed`, `upload`

#### Text & Data

```html
<text-field name="Full Name" role="First Party" required="true"
  default="John Doe" font="Helvetica" font-size="12" align="left"
  style="width:200px;height:20px;display:inline-block;"> </text-field>

<date-field name="Signing Date" role="First Party" required="true"
  format="DD/MM/YYYY" min="2024-01-01" max="2025-12-31"
  style="width:120px;height:20px;display:inline-block;"> </date-field>

<phone-field name="Phone" role="First Party"
  style="width:150px;height:20px;display:inline-block;"> </phone-field>
```

#### Selection

```html
<checkbox-field name="Agree to Terms" role="First Party" required="true"> </checkbox-field>

<radio-field name="Choice" role="First Party" options="Option A,Option B,Option C"
  default="Option A"> </radio-field>

<select-field name="Country" role="First Party" options="USA,Canada,UK"
  required="true" style="width:150px;height:20px;display:inline-block;"> </select-field>

<multi-select-field name="Languages" role="First Party" options="English,French,Spanish"
  style="width:200px;height:20px;display:inline-block;"> </multi-select-field>
```

#### File & Payment

```html
<file-field name="Supporting Document" role="First Party"
  style="width:200px;height:40px;display:inline-block;"> </file-field>

<payment-field name="Payment" role="First Party" price="99.99" currency="usd"> </payment-field>

<verification-field name="Identity Check" role="First Party" method="aes"> </verification-field>
```

### Universal Field Attributes

| Attribute | Values | Notes |
|-----------|--------|-------|
| `name` | string | Field identifier (required) |
| `role` | string | Signer party designation |
| `required` | true/false | Default: true |
| `readonly` | true/false | Prevents editing |
| `default` | string | Pre-fill value |
| `hidden` | true/false | Conceals field |
| `mask` | true/false | Masks sensitive data |
| `title` | string | Display label |
| `description` | string | Helper text |
| `condition` | `FieldName:value` | Conditional display |
| `font` | Times, Helvetica, Courier | Typeface |
| `font-size` | number | Text size in px |
| `font-type` | bold, italic, bold_italic | Style variant |
| `color` | blue, red, black | Text color |
| `align` | left, center, right | Horizontal alignment |
| `valign` | top, center, bottom | Vertical alignment |
| `pattern` | regex | Input validation |
| `min` / `max` | number or date | Range constraints |
| `options` | comma-separated | For select/radio types |
| `format` | varies by type | Type-specific format |

**IMPORTANT: Field tags must NOT overlap text content.** Place them in their own block elements (e.g., `<div>` or `<p>`) with clear spacing.

---

## Creating Templates from PDF

**`POST /templates/pdf`**

```json
{
  "name": "Document Name",
  "documents": [{
    "name": "document.pdf",
    "file": "base64_encoded_pdf_bytes",
    "fields": [
      {
        "name": "Signature",
        "type": "signature",
        "role": "First Party",
        "required": true,
        "areas": [{"x": 0.05, "y": 0.25, "w": 0.35, "h": 0.06, "page": 1}]
      }
    ]
  }]
}
```

Areas use normalized 0-1 coordinates relative to the full page.

### Embedded Text Field Tags in PDF

PDFs can contain text markers that DocuSeal auto-detects:

**Syntax:** `{{FieldName;attribute=value;attribute=value}}`

Examples:
- `{{Full Name}}` -- simple text field
- `{{DOB;type=date;role=Customer;required=false}}`
- `{{Sign;type=signature;format=drawn}}`
- `{{Date;type=datenow}}` -- auto-filled signing date (readonly)
- `{{Option;type=select;options=Yes,No,Maybe}}`
- `{{type=checkbox}}`
- `{{Choice;type=radio;option=Option A}}`

---

## Creating Templates from DOCX

**`POST /templates/docx`**

Variable syntax (double square brackets):
- Simple: `[[variable_name]]`
- Conditional: `[[if:var]]...[[else]]...[[end:var]]`
- Loops: `[[for:items]]...[[item.name]]...[[end]]`
- HTML content: `[[variable_name]]` supports `<p>`, `<ul>`, `<ol>`, `<table>`, `<a>`

DOCX can also contain `{{...}}` field tags for signing fields.

---

## Creating Submissions

**`POST /submissions`**

```json
{
  "template_id": 1000001,
  "send_email": false,
  "order": "preserved",
  "message": {
    "subject": "Please sign {{template.name}}",
    "body": "Hi {{submitter.first_name}}, please sign: {{submitter.link}}"
  },
  "submitters": [
    {
      "email": "john@example.com",
      "name": "John Doe",
      "role": "First Party",
      "order": 0,
      "external_id": "customer_123",
      "fields": [
        { "name": "First name", "default_value": "John", "readonly": true }
      ]
    }
  ]
}
```

**Key parameters:**
- `template_id`: Required
- `send_email`: true (default) sends invitation emails
- `order`: `"preserved"` (sequential) or `"random"` (parallel)
- `submitters[].fields[]`: Pre-fill with `name`, `default_value`, `readonly`
- `submitters[].external_id`: Your app's identifier
- `submitters[].order`: Explicit signing order (lower goes first)

**Email template variables:**
`{{template.name}}`, `{{submitter.link}}`, `{{submitter.email}}`, `{{submitter.name}}`, `{{submitter.first_name}}`, `{{account.name}}`, `{{sender.name}}`

---

## Auto-Signing (Programmatic Completion)

**`PUT /submitters/{id}`**

```json
{
  "completed": true,
  "fields": [
    { "name": "Signature", "default_value": "data:image/png;base64,..." },
    { "name": "Date", "default_value": "2024-03-15" }
  ]
}
```

Signature fields accept base64 data URIs or public image URLs.

---

## Webhooks

### Event Types

| Event | Trigger |
|-------|---------|
| `form.started` | Signer opened form |
| `form.viewed` | Signer viewed document |
| `form.completed` | Signer completed signing |
| `form.declined` | Signer declined |
| `submission.created` | Submission created |
| `submission.completed` | All signers completed |
| `submission.archived` | Submission archived |
| `template.created` | Template created |
| `template.updated` | Template modified |

### Webhook Payload

```json
{
  "event_type": "form.completed",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "id": 123,
    "external_id": "customer_123",
    "email": "signer@example.com",
    "status": "completed",
    "completed_at": "...",
    "documents": [
      {
        "id": 456,
        "uuid": "abc-def-ghi",
        "url": "https://..../signed.pdf",
        "preview_image_url": "https://..../preview.png",
        "filename": "document.pdf"
      }
    ],
    "values": [
      { "field": "Full Name", "value": "John Doe" }
    ]
  }
}
```

---

## Embedding

### Signing Form (`<docuseal-form>`)

```html
<script src="https://cdn.docuseal.com/js/form.js"></script>
<docuseal-form data-src="https://docuseal.com/s/SUBMITTER_SLUG"></docuseal-form>
```

NPM: `@docuseal/react`, `@docuseal/vue`, `@docuseal/angular`

**Key props:** `src`, `email`, `name`, `role`, `external_id`, `values` (JSON pre-fill), `language`, `logo`, `background-color`, `custom-css`, `with-decline`, `completed-redirect-url`, `send-copy-email`, `preview`, `signature` (pre-fill), `remember-signature`, `only-required-fields`

**Events:** `init`, `load`, `complete`, `decline`

### Template Builder (`<docuseal-builder>`)

```html
<script src="https://cdn.docuseal.com/js/builder.js"></script>
<docuseal-builder data-token="JWT_TOKEN"></docuseal-builder>
```

Requires backend-generated JWT (HS256) signed with API key.

**JWT payload:** `user_email` (required), `integration_email`, `template_id`, `external_id`, `folder_name`, `document_urls`, `name`, `extract_fields`

**Events:** `load`, `upload`, `send`, `change`, `save`

---

## Tremly Integration Notes

Tremly uses **self-hosted DocuSeal** at `https://docuseal.klikk.co.za/api`.

Current approach:
1. Generate filled lease HTML with `generate_lease_html()` — replaces merge fields and embeds DocuSeal field tags
2. Upload via `POST /templates/html` — DocuSeal auto-detects all field tags and positions them
3. Create submission via `POST /submissions` with `send_email: false`
4. Tremly sends its own signing emails with links to `/sign/<uuid>/`
5. Custom Vue signing page (`PublicSignView.vue`) renders the PDF and captures signatures
6. Submission completed via `PUT /submitters/{id}` with signature data
