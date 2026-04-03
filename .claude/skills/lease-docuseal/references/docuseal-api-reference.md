# DocuSeal API Reference (for Tremly agents)

This reference covers the DocuSeal API endpoints used by Tremly, plus additional endpoints that agents may need for extending the integration.

## Authentication

All requests require the `X-Auth-Token` header:
```
X-Auth-Token: <your-api-key>
```

## Endpoints Used by Tremly

### POST /templates/pdf
Upload a PDF and define signing fields.

**Request:**
```json
{
  "name": "Document Name",
  "documents": [{
    "name": "file.pdf",
    "file": "<base64-encoded-pdf>",
    "fields": [
      {
        "name": "Signature (First Party)",
        "type": "signature",
        "role": "First Party",
        "required": true,
        "areas": [{"x": 0.05, "y": 0.82, "w": 0.35, "h": 0.06, "page": 1}]
      }
    ]
  }]
}
```

**Field types:** `signature`, `date`, `text`, `initials`, `checkbox`, `image`, `stamp`, `cells`, `file`

**Response:** Template object with `id`, `submitters[]` (each with `name` = role)

### POST /submissions
Create a signing submission from a template.

**Request:**
```json
{
  "template_id": 123,
  "send_email": true,
  "submitters": [
    {
      "name": "John Doe",
      "email": "john@example.com",
      "role": "First Party",
      "send_email": true,
      "order": 0
    }
  ]
}
```

**Key fields:**
- `order`: Controls sequential signing. Omit or give same value for parallel.
- `send_email` (top-level): Default for all submitters
- `send_email` (per-submitter): Override per signer
- `role`: Must match a `submitters[].name` from the template

**Response:** Array of submitter objects:
```json
[
  {
    "id": 456,
    "submission_id": 789,
    "name": "John Doe",
    "email": "john@example.com",
    "role": "First Party",
    "status": "sent",
    "slug": "abc123",
    "embed_src": "https://docuseal.com/s/abc123",
    "completed_at": null,
    "order": 0
  }
]
```

### POST /api/submitters/{id}/send_email
Resend the signing invitation email to a submitter.

No request body needed. Returns `{"ok": true}`.

## Additional DocuSeal Endpoints (not yet used by Tremly)

### GET /templates
List all templates.

### GET /templates/{id}
Get template details.

### DELETE /templates/{id}
Delete a template.

### GET /submissions
List submissions. Supports `?template_id=`, `?status=`, `?limit=`, `?after=` params.

### GET /submissions/{id}
Get submission details with all submitter statuses.

### DELETE /submissions/{id}
Delete/cancel a submission.

### GET /submitters/{id}
Get submitter details including current status.

### PUT /submitters/{id}
Update submitter details (name, email, phone, etc.).

### POST /templates/docx
Upload a DOCX template (alternative to PDF).

### POST /templates/html
Create template from HTML content.

### POST /templates/{id}/clone
Clone an existing template.

## Webhook Events

DocuSeal sends POST requests to your configured webhook URL.

### Event Payload Structure
```json
{
  "event_type": "form.completed",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "id": 456,
    "submission_id": 789,
    "email": "john@example.com",
    "name": "John Doe",
    "role": "First Party",
    "status": "completed",
    "completed_at": "2024-01-01T12:00:00Z",
    "submission": {
      "id": 789,
      "status": "completed",
      "submitters": [...]
    }
  }
}
```

### Event Types
| Event | Fired When |
|-------|-----------|
| `form.viewed` | A submitter opens the signing page |
| `form.started` | A submitter begins filling fields |
| `form.completed` | A submitter finishes and submits |
| `submission.completed` | All submitters have completed |
| `submission.created` | A new submission is created |
| `submission.archived` | A submission is archived |
| `submission.declined` | A submitter declines to sign |

### Webhook Verification

**HMAC SHA256:**
```
X-Docuseal-Signature: hmac_sha256(secret, request_body)
```

**Custom header:**
Configure a custom header name and static secret value in DocuSeal settings.

## Field Positioning Guide

Fields use fractional coordinates relative to the page:
- `x`: Horizontal position (0.0 = left edge, 1.0 = right edge)
- `y`: Vertical position (0.0 = top, 1.0 = bottom)
- `w`: Width as fraction of page width
- `h`: Height as fraction of page height
- `page`: 1-indexed page number

### Typical signature block layout
```
Signature: x=0.05, y=0.82, w=0.35, h=0.06
Date:      x=0.55, y=0.82, w=0.20, h=0.04
```

### Multi-signer spacing
Each additional signer offsets `y` by -0.10:
- Signer 1: y=0.82
- Signer 2: y=0.72
- Signer 3: y=0.62
- Signer 4: y=0.52

**Warning:** More than 4 signers may cause overlap issues.

## Rate Limits
- DocuSeal cloud: Check your plan limits
- Self-hosted: No rate limits, but large PDFs (>50MB) may timeout

## Error Codes
| Status | Meaning |
|--------|---------|
| 401 | Invalid or missing API key |
| 404 | Template/submission not found |
| 422 | Validation error (bad field positions, missing required fields) |
| 429 | Rate limited (cloud only) |
